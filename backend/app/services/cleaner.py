"""
Data cleaning service for CleanIQ.
Implements preview and apply logic for each supported cleaning operation.
Every operation can be previewed (generating a diff) before being applied.
"""

import math
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

from app.core.errors import AppError
from app.models.dataset import DiffRow
from app.services.missing_detector import MissingValueService



SUPPORTED_OPERATIONS = [
    "drop_duplicates",
    "fill_missing",
    "drop_missing_rows",
    "trim_whitespace",
    "standardize_case",
    "generate_unique_order_ids",
]

MAX_SAMPLE_DIFFS = 20


def _resolve_columns(df: pd.DataFrame, requested: List[str]) -> List[str]:
    """Resolve and validate requested columns against the DataFrame."""
    if not requested:
        return list(df.columns)
    invalid = [c for c in requested if c not in df.columns]
    if invalid:
        raise AppError(
            code="INVALID_COLUMNS",
            message=f"Column(s) not found in dataset: {', '.join(invalid)}",
            status_code=400,
        )
    return requested


def _text_columns(df: pd.DataFrame, columns: List[str]) -> List[str]:
    """Filter to only object/string dtype columns."""
    return [c for c in columns if pd.api.types.is_object_dtype(df[c]) or pd.api.types.is_string_dtype(df[c])]


def _numeric_columns(df: pd.DataFrame, columns: List[str]) -> List[str]:
    """Filter to only numeric dtype columns."""
    return [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]


def _safe_value(val: Any) -> Any:
    """Convert numpy/pandas values to JSON-safe Python primitives."""
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return None
    if pd.isna(val):
        return None
    if isinstance(val, np.generic):
        return val.item()
    if isinstance(val, (pd.Timestamp,)):
        return val.isoformat()
    return val


def _generate_diffs(
    df_before: pd.DataFrame,
    df_after: pd.DataFrame,
    columns: List[str],
    max_diffs: int = MAX_SAMPLE_DIFFS,
) -> List[DiffRow]:
    """
    Generate sample diff rows showing before/after changes.
    Compares cell-by-cell for the specified columns.
    """
    diffs: List[DiffRow] = []

    # If row counts differ (rows were dropped), show which rows were removed
    if len(df_after) < len(df_before):
        # Identify removed rows by checking which indices from df_before are absent in df_after
        if set(df_after.index).issubset(set(df_before.index)):
            removed_indices = [idx for idx in df_before.index if idx not in df_after.index]
        else:
            # Fallback if df_after was already reset_index
            removed_indices = list(df_before.index[len(df_after):])

        for idx in removed_indices:
            row_pos = int(df_before.index.get_loc(idx))
            for col in columns[:3]:  # Show first 3 columns per removed row
                diffs.append(DiffRow(
                    row_index=row_pos,
                    column=col,
                    before=_safe_value(df_before.at[idx, col]) if idx in df_before.index else None,
                    after=None,
                ))
                if len(diffs) >= max_diffs:
                    return diffs
        return diffs

    # Same number of rows — compare cell-by-cell
    min_len = min(len(df_before), len(df_after))
    for col in columns:
        if col not in df_before.columns or col not in df_after.columns:
            continue
        before_series = df_before[col].iloc[:min_len]
        after_series = df_after[col].iloc[:min_len]

        # Find cells that changed
        try:
            changed_mask = before_series.fillna("__NULL__").astype(str) != after_series.fillna("__NULL__").astype(str)
        except Exception:
            changed_mask = before_series.astype(str) != after_series.astype(str)

        changed_indices = changed_mask[changed_mask].index.tolist()

        for idx in changed_indices:
            diffs.append(DiffRow(
                row_index=int(idx),
                column=col,
                before=_safe_value(before_series.iloc[idx] if idx < len(before_series) else None),
                after=_safe_value(after_series.iloc[idx] if idx < len(after_series) else None),
            ))
            if len(diffs) >= max_diffs:
                return diffs

    return diffs


# ─── Operation Implementations ───────────────────────────────────────────────


def _detect_duplicate_mask(
    df: pd.DataFrame,
    subset: Optional[List[str]],
    keep: str = "first",
    ignore_case: bool = False,
    trim_whitespace: bool = False,
) -> pd.Series:
    """Computes duplicate mask with optional case-insensitivity and whitespace normalization."""
    cols = subset if subset else list(df.columns)
    valid_keep = keep if keep in ("first", "last", False) else "first"

    if not ignore_case and not trim_whitespace:
        try:
            return df.duplicated(subset=cols, keep=valid_keep)
        except TypeError:
            return df[cols].astype(str).duplicated(keep=valid_keep)

    comp_df = pd.DataFrame(index=df.index)
    for c in cols:
        s = df[c]
        if pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s):
            str_s = s.astype(str)
            if trim_whitespace:
                str_s = str_s.str.strip()
            if ignore_case:
                str_s = str_s.str.lower()
            comp_df[c] = str_s
        else:
            comp_df[c] = s
    return comp_df.duplicated(keep=valid_keep)


def _preview_drop_duplicates(
    df: pd.DataFrame, columns: List[str], params: Dict[str, Any]
) -> Tuple[pd.DataFrame, List[str], str]:
    cols = columns if columns else list(df.columns)
    keep = params.get("keep", "first")
    ignore_case = bool(params.get("ignore_case", False))
    trim_whitespace = bool(params.get("trim_whitespace", False))

    dup_mask = _detect_duplicate_mask(
        df,
        subset=cols,
        keep=keep,
        ignore_case=ignore_case,
        trim_whitespace=trim_whitespace,
    )
    result = df[~dup_mask].copy()
    dropped = int(dup_mask.sum())
    summary = f"Found {dropped} duplicate row(s) to remove (keeping {keep})"
    if ignore_case or trim_whitespace:
        summary += f" [case-insensitive: {ignore_case}, trim-whitespace: {trim_whitespace}]"
    affected_cols = list(df.columns) if not columns else columns
    return result, affected_cols, summary


def _preview_fill_missing(
    df: pd.DataFrame, columns: List[str], params: Dict[str, Any]
) -> Tuple[pd.DataFrame, List[str], str]:
    strategy = params.get("strategy", params.get("method", "mean"))
    fill_value = params.get("value", None)
    custom_markers = params.get("null_markers", None)
    result = df.copy()
    affected_cols = []
    total_filled = 0

    for col in columns:
        col_missing = MissingValueService.count_missing(result[col], custom_markers=custom_markers)
        if col_missing == 0:
            continue

        imputed_series, count, _, _ = MissingValueService.safe_impute(
            result[col],
            col_name=col,
            strategy=strategy,
            value=fill_value,
            custom_markers=custom_markers,
        )
        result[col] = imputed_series
        affected_cols.append(col)
        total_filled += count

    summary = f"Filled {total_filled} missing cell(s) using '{strategy}' strategy across {len(affected_cols)} column(s)"
    return result, affected_cols, summary


def _preview_drop_missing_rows(
    df: pd.DataFrame, columns: List[str], params: Dict[str, Any]
) -> Tuple[pd.DataFrame, List[str], str]:
    how = params.get("how", "any")  # 'any' or 'all'
    custom_markers = params.get("null_markers", None)
    cols = columns if columns else list(df.columns)

    if not cols or len(df) == 0:
        return df.copy(), list(df.columns), "No rows to drop"

    masks = [MissingValueService.get_missing_mask(df[c], custom_markers=custom_markers) for c in cols]
    combined_mask = pd.concat(masks, axis=1)

    if how == "all":
        row_has_missing = combined_mask.all(axis=1)
    else:
        row_has_missing = combined_mask.any(axis=1)

    result = df[~row_has_missing].copy()
    dropped = int(row_has_missing.sum())
    summary = f"Dropping {dropped} row(s) with {'any' if how == 'any' else 'all'} missing values across {len(cols)} column(s)"
    return result, cols, summary



def _preview_trim_whitespace(
    df: pd.DataFrame, columns: List[str], params: Dict[str, Any]
) -> Tuple[pd.DataFrame, List[str], str]:
    text_cols = _text_columns(df, columns)
    if not text_cols:
        raise AppError(
            code="NO_TEXT_COLUMNS",
            message="No text/object columns found in the selected columns for whitespace trimming.",
            status_code=400,
        )
    result = df.copy()
    affected_count = 0
    for col in text_cols:
        trimmed = result[col].astype(str).str.strip()
        original = result[col].astype(str)
        affected_count += int((trimmed != original).sum())
        result[col] = df[col].where(df[col].isna(), trimmed)

    summary = f"Trimmed whitespace in {affected_count} cell(s) across {len(text_cols)} text column(s)"
    return result, text_cols, summary


def _preview_standardize_case(
    df: pd.DataFrame, columns: List[str], params: Dict[str, Any]
) -> Tuple[pd.DataFrame, List[str], str]:
    case_type = params.get("case", "lower")
    text_cols = _text_columns(df, columns)
    if not text_cols:
        raise AppError(
            code="NO_TEXT_COLUMNS",
            message="No text/object columns found in the selected columns for case standardization.",
            status_code=400,
        )
    result = df.copy()
    affected_count = 0
    for col in text_cols:
        if case_type == "lower":
            transformed = result[col].astype(str).str.lower()
        elif case_type == "upper":
            transformed = result[col].astype(str).str.upper()
        elif case_type == "title":
            transformed = result[col].astype(str).str.title()
        else:
            transformed = result[col].astype(str).str.lower()

        original = result[col].astype(str)
        affected_count += int((transformed != original).sum())
        result[col] = df[col].where(df[col].isna(), transformed)

    summary = f"Standardized {affected_count} cell(s) to {case_type}case across {len(text_cols)} column(s)"
    return result, text_cols, summary


def _preview_generate_unique_order_ids(
    df: pd.DataFrame, columns: List[str], params: Dict[str, Any]
) -> Tuple[pd.DataFrame, List[str], str]:
    from app.services.order_validator import OrderValidatorService

    order_id_col = params.get("column") or (columns[0] if columns else None)
    mode = params.get("mode", "conflicts_only")
    prefix = params.get("prefix")
    start_num = int(params.get("start_number", 1))

    cleaned_df, info = OrderValidatorService.generate_unique_order_ids(
        df=df,
        order_id_col=order_id_col,
        mode=mode,
        prefix=prefix,
        start_number=start_num,
    )
    col_used = info["column"]
    summary = info["logs"][0] if info["logs"] else f"Generated unique Order IDs for {info['rows_affected']} row(s)"
    return cleaned_df, [col_used], summary


# ─── Public API ───────────────────────────────────────────────────────────────


OPERATION_HANDLERS = {
    "drop_duplicates": _preview_drop_duplicates,
    "fill_missing": _preview_fill_missing,
    "drop_missing_rows": _preview_drop_missing_rows,
    "trim_whitespace": _preview_trim_whitespace,
    "standardize_case": _preview_standardize_case,
    "generate_unique_order_ids": _preview_generate_unique_order_ids,
}


def preview_operation(
    df: pd.DataFrame,
    dataset_id: str,
    operation: str,
    columns: List[str],
    params: Dict[str, Any],
) -> dict:
    """
    Preview a cleaning operation without modifying the original DataFrame.
    Returns a dict with preview stats and sample diffs.
    """
    if operation not in OPERATION_HANDLERS:
        raise AppError(
            code="UNSUPPORTED_OPERATION",
            message=f"Operation '{operation}' is not supported. Supported: {', '.join(SUPPORTED_OPERATIONS)}",
            status_code=400,
        )

    resolved_columns = _resolve_columns(df, columns)
    handler = OPERATION_HANDLERS[operation]
    result_df, affected_cols, summary = handler(df, resolved_columns, params)

    rows_before = len(df)
    rows_after = len(result_df)

    # Compute affected row count
    if rows_before != rows_after:
        affected_row_count = abs(rows_before - rows_after)
    else:
        # Count rows where at least one cell changed
        affected_row_count = 0
        min_len = min(rows_before, rows_after)
        for col in affected_cols:
            if col in df.columns and col in result_df.columns:
                try:
                    mask = df[col].iloc[:min_len].fillna("__NULL__").astype(str) != result_df[col].iloc[:min_len].fillna("__NULL__").astype(str)
                    affected_row_count += int(mask.sum())
                except Exception:
                    pass

    sample_diffs = _generate_diffs(df, result_df, affected_cols)

    return {
        "dataset_id": dataset_id,
        "operation": operation,
        "affected_row_count": affected_row_count,
        "total_rows_before": rows_before,
        "total_rows_after": rows_after,
        "columns_affected": affected_cols,
        "sample_diffs": sample_diffs,
        "summary": summary,
        "_result_df": result_df,  # Internal: used by apply if called immediately
    }


def apply_operation(
    df: pd.DataFrame,
    operation: str,
    columns: List[str],
    params: Dict[str, Any],
) -> Tuple[pd.DataFrame, List[str], int, str]:
    """
    Apply a cleaning operation and return the new DataFrame.
    Returns: (result_df, affected_cols, affected_row_count, summary)
    """
    if operation not in OPERATION_HANDLERS:
        raise AppError(
            code="UNSUPPORTED_OPERATION",
            message=f"Operation '{operation}' is not supported.",
            status_code=400,
        )

    resolved_columns = _resolve_columns(df, columns)
    handler = OPERATION_HANDLERS[operation]
    result_df, affected_cols, summary = handler(df, resolved_columns, params)

    rows_before = len(df)
    rows_after = len(result_df)
    if rows_before != rows_after:
        affected_row_count = abs(rows_before - rows_after)
    else:
        affected_row_count = 0
        min_len = min(rows_before, rows_after)
        for col in affected_cols:
            if col in df.columns and col in result_df.columns:
                try:
                    mask = df[col].iloc[:min_len].fillna("__NULL__").astype(str) != result_df[col].iloc[:min_len].fillna("__NULL__").astype(str)
                    affected_row_count += int(mask.sum())
                except Exception:
                    pass

    # Reset index for consistency
    result_df = result_df.reset_index(drop=True)

    return result_df, affected_cols, affected_row_count, summary
