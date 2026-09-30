import io
import time
import pytest
import pandas as pd
import numpy as np

from app.core.errors import AppError
from app.services.text_cleaner import TextCleanerService
from app.services.order_validator import OrderValidatorService
from app.services.file_parser import parse_uploaded_file


# ==============================================================================
# 1. Text Cleaner Vectorized Operations & Edge Cases
# ==============================================================================

def test_text_cleaner_vectorized_trim_unicode_nulls():
    """Trim collapses multiple inner spaces, strips outer spaces, and preserves Unicode & nulls."""
    s = pd.Series([
        "  Café   de   Paris  ",
        "  São   Paulo\t\tBrasil  ",
        None,
        np.nan,
        "   ",
        "clean text",
        "  🚀   Rocket   Man  ",
    ])
    res, affected_count = TextCleanerService.transform_text(s, operation="trim")

    assert res.iloc[0] == "Café de Paris"
    assert res.iloc[1] == "São Paulo Brasil"
    assert pd.isna(res.iloc[2])
    assert pd.isna(res.iloc[3])
    assert res.iloc[4] == ""
    assert res.iloc[5] == "clean text"
    assert res.iloc[6] == "🚀 Rocket Man"
    assert affected_count == 4  # rows 0, 1, 4, 6 were changed


def test_text_cleaner_vectorized_case_conversions():
    """Case conversions work on mixed case, Unicode, and preserve nulls."""
    s = pd.Series(["münchen HBF", "NEW YORK", "rio de janeiro", None])

    lower_res, lower_cnt = TextCleanerService.transform_text(s, operation="case", case_type="lower")
    assert lower_res.iloc[0] == "münchen hbf"
    assert lower_res.iloc[1] == "new york"
    assert pd.isna(lower_res.iloc[3])
    assert lower_cnt == 2

    upper_res, upper_cnt = TextCleanerService.transform_text(s, operation="case", case_type="upper")
    assert upper_res.iloc[0] == "MÜNCHEN HBF"
    assert upper_res.iloc[2] == "RIO DE JANEIRO"
    assert pd.isna(upper_res.iloc[3])
    assert upper_cnt == 2

    title_res, title_cnt = TextCleanerService.transform_text(s, operation="case", case_type="title")
    assert title_res.iloc[0] == "München Hbf"
    assert title_res.iloc[2] == "Rio De Janeiro"
    assert pd.isna(title_res.iloc[3])
    assert title_cnt == 3


def test_text_cleaner_vectorized_remove_special():
    """Remove special keeps only alphanumeric and whitespace, preserving nulls."""
    s = pd.Series(["Order #12345 @ $99.99!", "Clean text 123", None, "Special: (A+B)=C*2"])
    res, count = TextCleanerService.transform_text(s, operation="remove_special")

    assert res.iloc[0] == "Order 12345  9999"
    assert res.iloc[1] == "Clean text 123"
    assert pd.isna(res.iloc[2])
    assert res.iloc[3] == "Special ABC2"
    assert count == 2


def test_text_cleaner_vectorized_find_replace():
    """Find and replace works for both literal strings and regular expressions."""
    s = pd.Series(["Item-001", "Item-002", "Product-003", None])

    # Plain text replace
    res_plain, cnt_plain = TextCleanerService.transform_text(
        s, operation="find_replace", find_text="Item", replace_text="SKU", regex=False
    )
    assert res_plain.iloc[0] == "SKU-001"
    assert res_plain.iloc[1] == "SKU-002"
    assert res_plain.iloc[2] == "Product-003"
    assert pd.isna(res_plain.iloc[3])
    assert cnt_plain == 2

    # Regex replace
    res_rx, cnt_rx = TextCleanerService.transform_text(
        s, operation="find_replace", find_text=r"\d+", replace_text="XXX", regex=True
    )
    assert res_rx.iloc[0] == "Item-XXX"
    assert res_rx.iloc[1] == "Item-XXX"
    assert res_rx.iloc[2] == "Product-XXX"
    assert pd.isna(res_rx.iloc[3])
    assert cnt_rx == 3


def test_text_cleaner_empty_and_numeric_series():
    """Handles empty series and numeric series without crashing."""
    empty_s = pd.Series([], dtype=object)
    res_empty, cnt_empty = TextCleanerService.transform_text(empty_s, operation="trim")
    assert len(res_empty) == 0
    assert cnt_empty == 0

    num_s = pd.Series([123, 456, None, 789])
    res_num, cnt_num = TextCleanerService.transform_text(
        num_s, operation="find_replace", find_text="5", replace_text="9", regex=False
    )
    assert res_num.iloc[1] == "496.0"
    assert pd.isna(res_num.iloc[2])
    assert cnt_num == 1

    int_s = pd.Series([123, 456, None, 789], dtype="Int64")
    res_int, cnt_int = TextCleanerService.transform_text(
        int_s, operation="find_replace", find_text="5", replace_text="9", regex=False
    )
    assert res_int.iloc[1] == "496"
    assert pd.isna(res_int.iloc[2])
    assert cnt_int == 1


def test_text_cleaner_apply_standardize():
    """Standardize replaces variants with canonical value and tracks affected rows."""
    s = pd.Series(["NYC", "new york", "New York", "San Francisco", "SF", None])
    merges = [
        {"canonical": "New York", "variants": ["NYC", "new york"]},
        {"canonical": "San Francisco", "variants": ["SF"]},
    ]
    res, affected = TextCleanerService.apply_standardize(s, merges)

    assert res.iloc[0] == "New York"
    assert res.iloc[1] == "New York"
    assert res.iloc[2] == "New York"
    assert res.iloc[3] == "San Francisco"
    assert res.iloc[4] == "San Francisco"
    assert pd.isna(res.iloc[5])
    assert affected == 3  # NYC, new york, SF


# ==============================================================================
# 2. Order Validator Vectorized Diff Extraction & Performance
# ==============================================================================

def test_order_validator_diff_extraction_and_conflicts():
    """Validates that generate_unique_order_ids generates exact diff structures."""
    df = pd.DataFrame({
        "order_id": ["ORD-1", "ORD-1", "ORD-2", "ORD-3", "ORD-3", "ORD-4"],
        "order_date": ["2023-01-01", "2023-01-02", "2023-01-01", "2023-01-01", "2023-01-01", "2023-01-01"],
        "customer": ["Alice", "Bob", "Charlie", "David", "David", "Eve"],
        "product": ["Widget A", "Widget B", "Gadget C", "Item D", "Item E", "Item F"],
    })

    # In conflicts_only mode, only the conflicting ORD-1 across different dates/customers should change
    res_df, meta = OrderValidatorService.generate_unique_order_ids(df, mode="conflicts_only")

    assert meta["rows_affected"] == 2
    assert len(meta["diffs"]) == 2

    # Check diff structure
    diff0 = meta["diffs"][0]
    assert diff0["row_index"] == 0
    assert diff0["column"] == "order_id"
    assert diff0["old_value"] == "ORD-1"
    assert diff0["new_value"].startswith("ORD-")
    assert diff0["new_value"] != "ORD-1"

    diff1 = meta["diffs"][1]
    assert diff1["row_index"] == 1
    assert diff1["column"] == "order_id"
    assert diff1["old_value"] == "ORD-1"
    assert diff1["new_value"] != diff0["new_value"]

    # ORD-3 (valid order-line) and ORD-2, ORD-4 (unique) must remain unchanged
    assert res_df.at[2, "order_id"] == "ORD-2"
    assert res_df.at[3, "order_id"] == "ORD-3"
    assert res_df.at[4, "order_id"] == "ORD-3"
    assert res_df.at[5, "order_id"] == "ORD-4"


def test_order_validator_all_rows_mode():
    """Validates all_rows mode regenerates sequential IDs for all rows and extracts diffs."""
    df = pd.DataFrame({
        "order_id": ["A10", "B20", "C30"],
        "customer": ["Alice", "Bob", "Charlie"],
    })

    res_df, meta = OrderValidatorService.generate_unique_order_ids(
        df, mode="all_rows", prefix="ORD-", start_number=100
    )

    assert meta["rows_affected"] == 3
    assert len(meta["diffs"]) == 3
    assert res_df["order_id"].tolist() == ["ORD-100", "ORD-101", "ORD-102"]
    for i, diff in enumerate(meta["diffs"]):
        assert diff["row_index"] == i
        assert diff["new_value"] == f"ORD-10{i}"


def test_order_validator_diff_extraction_speed_large_dataset():
    """Diff extraction on large dataset (10,000+ rows) executes in milliseconds without row-by-row overhead."""
    n = 10000
    df = pd.DataFrame({
        "order_id": [f"ORD-{i:05d}" for i in range(n)],
        "customer": [f"Cust-{i % 200}" for i in range(n)],
        "order_date": ["2023-01-01"] * n,
    })

    t0 = time.perf_counter()
    res_df, meta = OrderValidatorService.generate_unique_order_ids(df, mode="conflicts_only")
    elapsed_sec = time.perf_counter() - t0

    # With 0 conflicts, no rows should be updated and diffs should be empty
    assert meta["rows_affected"] == 0
    assert len(meta["diffs"]) == 0
    # Must complete fast (well under 500ms)
    assert elapsed_sec < 0.5, f"Expected <0.5s on 10k rows, took {elapsed_sec:.3f}s"


# ==============================================================================
# 3. UTF-16 LE and BE CSV and TSV Support
# ==============================================================================

def test_utf16_le_csv_with_bom():
    """Parses UTF-16 LE encoded CSV with BOM b'\\xff\\xfe' and Unicode values."""
    csv_text = "order_id,customer,city,amount\nORD-1,René,São Paulo,150.50\nORD-2,München Hbf,München,200.00\n"
    file_bytes = b"\xff\xfe" + csv_text.encode("utf-16-le")

    df = parse_uploaded_file("orders_utf16le.csv", file_bytes)
    assert len(df) == 2
    assert list(df.columns) == ["order_id", "customer", "city", "amount"]
    assert df.iloc[0]["customer"] == "René"
    assert df.iloc[0]["city"] == "São Paulo"
    assert df.iloc[1]["city"] == "München"


def test_utf16_be_csv_with_bom():
    """Parses UTF-16 BE encoded CSV with BOM b'\\xfe\\xff'."""
    csv_text = "id,name,role\n1,Alice,Engineer\n2,Günther,Manager\n"
    file_bytes = b"\xfe\xff" + csv_text.encode("utf-16-be")

    df = parse_uploaded_file("users_utf16be.csv", file_bytes)
    assert len(df) == 2
    assert list(df.columns) == ["id", "name", "role"]
    assert df.iloc[1]["name"] == "Günther"


def test_utf16_tsv_with_bom():
    """Parses UTF-16 LE TSV file with tab delimiters automatically sniffed."""
    tsv_text = "product_id\tproduct_name\tcategory\tprice\nP100\tWidget A\tHardware\t19.99\nP200\tGadget B\tElectronics\t49.99\n"
    file_bytes = b"\xff\xfe" + tsv_text.encode("utf-16-le")

    df = parse_uploaded_file("catalog_utf16.tsv", file_bytes)
    assert len(df) == 2
    assert list(df.columns) == ["product_id", "product_name", "category", "price"]
    assert df.iloc[0]["product_id"] == "P100"
    assert df.iloc[1]["product_name"] == "Gadget B"


def test_utf16_quoted_fields_embedded_delimiters_and_newlines():
    """Parses UTF-16 CSV with quoted fields containing embedded commas, tabs, and newlines."""
    csv_text = (
        'id,description,notes\n'
        '1,"Item with, comma and \ttab","Note 1"\n'
        '2,"Multiline value:\nLine 2\nLine 3","Note 2"\n'
    )
    file_bytes = b"\xff\xfe" + csv_text.encode("utf-16-le")

    df = parse_uploaded_file("multiline_utf16.csv", file_bytes)
    assert len(df) == 2
    assert df.iloc[0]["description"] == "Item with, comma and \ttab"
    assert df.iloc[1]["description"] == "Multiline value:\nLine 2\nLine 3"
    assert df.iloc[1]["notes"] == "Note 2"


def test_utf16_empty_dataset_handling():
    """File with only UTF-16 BOM or whitespace raises EMPTY_DATASET instead of crash."""
    bom_only = b"\xff\xfe"
    with pytest.raises(AppError) as exc_info:
        parse_uploaded_file("empty_utf16.csv", bom_only)
    assert exc_info.value.code == "EMPTY_DATASET"

    bom_whitespace = b"\xff\xfe" + "   \n\r\n\t  ".encode("utf-16-le")
    with pytest.raises(AppError) as exc_info2:
        parse_uploaded_file("blank_utf16.csv", bom_whitespace)
    assert exc_info2.value.code == "EMPTY_DATASET"


def test_binary_file_with_null_bytes_rejected():
    """Binary files containing null bytes without UTF-16 BOM are rejected as INVALID_FILE_CONTENT."""
    raw_binary = b"\x00\x01\x02\x03\x04\x05\xaa\xbb\xcc\xdd"
    with pytest.raises(AppError) as exc_info:
        parse_uploaded_file("corrupt.csv", raw_binary)
    assert exc_info.value.code == "INVALID_FILE_CONTENT"


def test_utf8_and_utf8_sig_compatibility():
    """Ensures existing standard UTF-8 and UTF-8 BOM files continue to parse flawlessly."""
    # UTF-8 with BOM
    utf8_sig_text = "\ufeffid,name\n1,Alice\n2,Bob\n"
    df_sig = parse_uploaded_file("utf8_bom.csv", utf8_sig_text.encode("utf-8"))
    assert len(df_sig) == 2
    assert list(df_sig.columns) == ["id", "name"]

    # Plain UTF-8
    utf8_plain = "id,name\n1,Carlos\n2,Diana\n"
    df_plain = parse_uploaded_file("utf8_plain.csv", utf8_plain.encode("utf-8"))
    assert len(df_plain) == 2
    assert list(df_plain.columns) == ["id", "name"]
