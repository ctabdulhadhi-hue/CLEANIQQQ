import io
import csv
import logging
import zipfile
from typing import Tuple, List, Optional
import pandas as pd

from app.core.errors import AppError

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024  # 200 MB uncompressed limit for zip bombs
MAX_COMPRESSION_RATIO = 100  # Max ratio of uncompressed to compressed size

ZIP_MAGIC_BYTES = b"PK\x03\x04"
OLE_MAGIC_BYTES = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

# Safe default NA values that do NOT include 'NA' (preserving Namibia or valid codes)
# while recognizing empty strings, NULL, None, NaN, and standard spreadsheet blanks.
SAFE_CSV_NA_VALUES = [
    "",
    "#N/A",
    "#N/A N/A",
    "#NA",
    "-1.#IND",
    "-1.#QNAN",
    "-NaN",
    "-nan",
    "1.#IND",
    "1.#QNAN",
    "<NA>",
    "N/A",
    "NULL",
    "NaN",
    "None",
    "n/a",
    "nan",
    "null",
]


def make_unique_column_names(columns: list) -> List[str]:
    """
    Cleans up column names:
    - Trims whitespace
    - Replaces empty/null names with 'column_{i+1}'
    - Disambiguates duplicate column names (e.g. ['col', 'col'] -> ['col', 'col_2'])
    - Preserves original order and valid names
    """
    seen: dict[str, int] = {}
    new_cols: List[str] = []
    for i, col in enumerate(columns):
        if pd.notna(col) and str(col).strip() != "":
            clean_name = str(col).strip()
        else:
            clean_name = f"column_{i+1}"

        if clean_name not in seen:
            seen[clean_name] = 1
            new_cols.append(clean_name)
        else:
            seen[clean_name] += 1
            new_cols.append(f"{clean_name}_{seen[clean_name]}")
    return new_cols


def _check_zip_bomb(file_bytes: bytes, filename: str) -> None:
    """Inspects ZIP archive to protect against decompression bombs."""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            total_uncompressed = sum(info.file_size for info in zf.infolist())
            compressed_size = len(file_bytes)
            if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                raise AppError(
                    code="DECOMPRESSION_BOMB",
                    message=(
                        f"Excel file '{filename}' exceeds uncompressed safety limits "
                        f"({total_uncompressed / (1024 * 1024):.1f}MB uncompressed, max 200MB allowed)."
                    ),
                    status_code=400,
                )
            if compressed_size > 0 and (total_uncompressed / compressed_size) > MAX_COMPRESSION_RATIO:
                raise AppError(
                    code="DECOMPRESSION_BOMB",
                    message=(
                        f"Excel file '{filename}' has an abnormal compression ratio "
                        f"({(total_uncompressed / compressed_size):.1f}:1), potential zip bomb rejected."
                    ),
                    status_code=400,
                )
    except AppError:
        raise
    except zipfile.BadZipFile:
        pass  # Will be caught by openpyxl parsing below
    except Exception as e:
        logger.warning(f"Error checking zip bomb for '{filename}': {e}")


def parse_uploaded_file(filename: str, file_bytes: bytes) -> pd.DataFrame:
    """
    Parses an uploaded file into a pandas DataFrame.
    Validates file content rather than blindly relying on file extensions:
    - Inspects magic bytes for Excel formats (.xlsx, .xls)
    - Protects against decompression bombs
    - Tries CSV / TSV with automatic delimiter and encoding detection
    - Rejects invalid, corrupted, or oversized files with clear AppError
    - Preserves column order and disambiguates duplicate column names
    """
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise AppError(
            code="FILE_TOO_LARGE",
            message=f"File exceeds maximum allowed size of 50MB (received {len(file_bytes) / (1024 * 1024):.2f}MB)",
            status_code=413,
        )

    if not file_bytes:
        raise AppError(
            code="EMPTY_FILE",
            message="Uploaded file is empty (0 bytes).",
            status_code=400,
        )

    lower_name = (filename or "").lower()
    df: pd.DataFrame | None = None
    parse_errors: list[str] = []

    # Check for Excel ZIP magic bytes (.xlsx)
    is_zip = file_bytes.startswith(ZIP_MAGIC_BYTES)
    is_ole = file_bytes.startswith(OLE_MAGIC_BYTES)

    # Strategy 1: Openpyxl for modern Excel (.xlsx)
    if is_zip or lower_name.endswith((".xlsx", ".xlsm")):
        _check_zip_bomb(file_bytes, filename)
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
        except AppError:
            raise
        except Exception as e:
            parse_errors.append(f"openpyxl: {str(e)}")

    # Strategy 2: xlrd for legacy Excel (.xls)
    if df is None and (is_ole or lower_name.endswith(".xls")):
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), engine="xlrd")
        except Exception as e:
            parse_errors.append(f"xlrd: {str(e)}")

    # Strategy 3: CSV/TSV parsing with encoding & separator fallbacks
    if df is None:
        # If the file contains null bytes, it is a binary file (not text/CSV)
        if b"\x00" in file_bytes:
            raise AppError(
                code="INVALID_FILE_CONTENT",
                message=f"Failed to parse '{filename}': file contains binary data and is not a valid CSV or Excel document.",
                status_code=400,
            )

        encodings = ["utf-8-sig", "utf-8", "latin1", "cp1252", "iso-8859-1"]
        for enc in encodings:
            try:
                decoded = file_bytes.decode(enc)
                sample = decoded[:4096]

                # Sniff delimiter if possible
                sep = ","
                if "\t" in sample and sample.count("\t") > sample.count(","):
                    sep = "\t"
                elif ";" in sample and sample.count(";") > sample.count(","):
                    sep = ";"
                elif "|" in sample and sample.count("|") > sample.count(","):
                    sep = "|"
                else:
                    try:
                        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
                        sep = dialect.delimiter
                    except Exception:
                        sep = ","

                # Use keep_default_na=False with SAFE_CSV_NA_VALUES to preserve 'NA'
                df = pd.read_csv(
                    io.StringIO(decoded),
                    sep=sep,
                    keep_default_na=False,
                    na_values=SAFE_CSV_NA_VALUES,
                    on_bad_lines="skip",
                )
                break
            except Exception as e:
                parse_errors.append(f"csv ({enc}): {str(e)}")
                continue

    # Strategy 4: Fallback generic pd.read_excel if extension suggested excel
    if df is None and lower_name.endswith((".xlsx", ".xls")):
        try:
            df = pd.read_excel(io.BytesIO(file_bytes))
        except Exception as e:
            parse_errors.append(f"excel-generic: {str(e)}")

    if df is None:
        logger.warning(f"Failed parsing file '{filename}'. Errors: {parse_errors}")
        raise AppError(
            code="INVALID_FILE_CONTENT",
            message=(
                f"Failed to parse '{filename}': file is corrupted or not a valid CSV or Excel document."
            ),
            status_code=400,
        )

    # Validate that dataframe is not empty
    if df.empty and len(df.columns) == 0:
        raise AppError(
            code="EMPTY_DATASET",
            message=f"Uploaded file '{filename}' contains no readable data rows or columns.",
            status_code=400,
        )

    # Clean up column headers (ensure string, trim whitespace, deduplicate)
    df.columns = make_unique_column_names(list(df.columns))

    return df
