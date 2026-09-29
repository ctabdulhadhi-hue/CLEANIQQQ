import io
import math
import pytest
from fastapi.testclient import TestClient
import pandas as pd
import numpy as np

from app.main import app
from app.core.session_store import session_store
from app.services.missing_detector import MissingValueService
from app.services.cleaner import _detect_duplicate_mask, preview_operation
from app.services.type_detector import TypeDetectorService
from app.services.quality import QualityScoreService
from app.services.file_parser import parse_uploaded_file, make_unique_column_names, _check_zip_bomb
from app.routes.datasets import sanitize_for_spreadsheet
from app.core.errors import AppError

client = TestClient(app)


# ─── 1. Missing Value Detection & Preservation ──────────────────────────────


def test_missing_values_preserves_legitimate_zero_and_false():
    """Verify that 0, 0.0, and False are NOT classified as missing."""
    s = pd.Series([0, 0.0, False, True, "valid text", None, np.nan, ""])
    mask = MissingValueService.get_missing_mask(s)
    # 0, 0.0, False, True, "valid text" are NOT missing (indices 0, 1, 2, 3, 4)
    assert not mask.iloc[0]  # 0
    assert not mask.iloc[1]  # 0.0
    assert not mask.iloc[2]  # False
    assert not mask.iloc[3]  # True
    assert not mask.iloc[4]  # "valid text"
    # None, np.nan, "" ARE missing (indices 5, 6, 7)
    assert mask.iloc[5]
    assert mask.iloc[6]
    assert mask.iloc[7]
    assert MissingValueService.count_missing(s) == 3


def test_missing_values_preserves_na_string_unless_configured():
    """Verify string 'NA' (e.g. Namibia country code) is preserved unless explicitly configured."""
    s = pd.Series(["US", "CA", "NA", "GB", "  ", None])
    # Default: 'NA' is treated as valid text string
    mask_default = MissingValueService.get_missing_mask(s)
    assert not mask_default.iloc[2]  # 'NA' is NOT missing
    assert mask_default.iloc[4]      # '  ' is missing (whitespace)
    assert mask_default.iloc[5]      # None is missing
    assert MissingValueService.count_missing(s) == 2

    # Configured with custom_markers=['NA']:
    mask_custom = MissingValueService.get_missing_mask(s, custom_markers=["NA"])
    assert mask_custom.iloc[2]       # 'NA' IS missing
    assert MissingValueService.count_missing(s, custom_markers=["NA"]) == 3


def test_missing_values_all_types():
    """Verify detection on numeric, boolean, datetime, and nullable dtypes."""
    # Numeric float with NaN and Inf
    num_s = pd.Series([1.5, np.nan, 3.0, np.inf, 4.5])
    assert MissingValueService.count_missing(num_s) == 2

    # Nullable integer
    int_s = pd.Series([10, None, 20], dtype="Int64")
    assert MissingValueService.count_missing(int_s) == 1

    # Boolean series
    bool_s = pd.Series([True, False, None], dtype="boolean")
    assert MissingValueService.count_missing(bool_s) == 1


# ─── 2. Safe Imputation Strategies ──────────────────────────────────────────


def test_imputation_mean_median_mode_constant():
    # Numeric column: [10, 20, np.nan, 30] -> mean = 20.0
    num_col = pd.Series([10.0, 20.0, np.nan, 30.0])
    res_mean, count, rem, fill_val = MissingValueService.safe_impute(num_col, "val", "mean")
    assert count == 1
    assert rem == 0
    assert fill_val == 20.0
    assert res_mean.iloc[2] == 20.0

    # Median: [10, 20, np.nan, 90] -> median of [10, 20, 90] = 20.0
    num_med = pd.Series([10.0, 20.0, np.nan, 90.0])
    res_med, _, _, fill_val_med = MissingValueService.safe_impute(num_med, "val", "median")
    assert fill_val_med == 20.0
    assert res_med.iloc[2] == 20.0

    # Constant: [1, np.nan, 3] with value=99 -> 99
    res_const, _, _, fill_val_const = MissingValueService.safe_impute(num_col, "val", "constant", value=99)
    assert fill_val_const == 99
    assert res_const.iloc[2] == 99.0


def test_imputation_tied_modes_deterministic():
    """Tied mode values must be resolved deterministically (sorted)."""
    # Modes: 'B' and 'A' (each appears twice)
    tied_s = pd.Series(["B", "B", "A", "A", None])
    res1, _, _, fill1 = MissingValueService.safe_impute(tied_s, "cat", "mode")
    res2, _, _, fill2 = MissingValueService.safe_impute(tied_s, "cat", "mode")
    assert fill1 == "A"
    assert fill2 == "A"
    assert res1.iloc[4] == "A"


def test_imputation_prevent_non_numeric_mean_median():
    """Non-numeric columns must reject mean and median with AppError."""
    text_s = pd.Series(["apple", "banana", None])
    with pytest.raises(AppError) as exc_info:
        MissingValueService.safe_impute(text_s, "fruit", "mean")
    assert exc_info.value.code == "INVALID_METHOD"

    with pytest.raises(AppError) as exc_info:
        MissingValueService.safe_impute(text_s, "fruit", "median")
    assert exc_info.value.code == "INVALID_METHOD"


def test_imputation_all_missing_column():
    """Columns with no valid values must raise clear error without crashing."""
    all_nan = pd.Series([np.nan, np.nan, np.nan], dtype=float)
    with pytest.raises(AppError) as exc_info:
        MissingValueService.safe_impute(all_nan, "empty_col", "mean")
    assert exc_info.value.code == "NO_VALID_VALUES"


def test_imputation_forward_and_backward_fill():
    s = pd.Series([1.0, np.nan, 3.0])
    res_ffill, _, _, _ = MissingValueService.safe_impute(s, "col", "ffill")
    assert res_ffill.iloc[1] == 1.0

    res_bfill, _, _, _ = MissingValueService.safe_impute(s, "col", "bfill")
    assert res_bfill.iloc[1] == 3.0


# ─── 3. Duplicate Detection & Configurable Policies ─────────────────────────


def test_duplicate_detection_case_and_whitespace():
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "name": ["Alice", "alice", "Bob ", "Bob"],
        "dept": ["Sales", "sales", "HR", "hr"],
    })
    # Default exact match: 0 duplicates
    mask_exact = _detect_duplicate_mask(df, subset=["name"], keep="first", ignore_case=False, trim_whitespace=False)
    assert int(mask_exact.sum()) == 0

    # Case-insensitive duplicate detection: "Alice" and "alice" match!
    mask_ci = _detect_duplicate_mask(df, subset=["name"], keep="first", ignore_case=True, trim_whitespace=False)
    assert int(mask_ci.sum()) == 1
    assert mask_ci.iloc[1]  # row 1 ("alice") is duplicate of row 0 ("Alice")

    # Whitespace-insensitive duplicate detection on "Bob " and "Bob":
    mask_ws = _detect_duplicate_mask(df, subset=["name"], keep="first", ignore_case=False, trim_whitespace=True)
    assert int(mask_ws.sum()) == 1
    assert mask_ws.iloc[3]  # row 3 is duplicate of row 2

    # Both case and whitespace:
    mask_both = _detect_duplicate_mask(df, subset=["name"], keep="first", ignore_case=True, trim_whitespace=True)
    assert int(mask_both.sum()) == 2  # both alice and Bob are duplicate occurrences


def test_duplicate_detection_keep_last():
    df = pd.DataFrame({"key": ["A", "B", "A"]})
    mask_first = _detect_duplicate_mask(df, subset=["key"], keep="first")
    mask_last = _detect_duplicate_mask(df, subset=["key"], keep="last")

    # keep="first": row 2 is duplicate
    assert not mask_first.iloc[0]
    assert mask_first.iloc[2]

    # keep="last": row 0 is duplicate
    assert mask_last.iloc[0]
    assert not mask_last.iloc[2]


# ─── 4. File Upload & Validation ────────────────────────────────────────────


def test_unique_column_name_disambiguation():
    cols = ["price", "price", "  ", "name", "price"]
    deduped = make_unique_column_names(cols)
    assert deduped == ["price", "price_2", "column_3", "name", "price_3"]


def test_empty_dataset_quality_score():
    empty_df = pd.DataFrame()
    res = QualityScoreService.compute(empty_df)
    assert res["overall_score"] == 0.0
    assert res["summary"]["overall_score"] == 0.0


def test_clean_dataset_quality_score():
    clean_df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"],
        "score": [85, 90, 78, 92, 88],
    })
    res = QualityScoreService.compute(clean_df)
    assert res["overall_score"] >= 0.90
    assert res["summary"]["missing_values"] == 0
    assert res["summary"]["duplicate_rows"] == 0


# ─── 5. Type Inference & Conversion ─────────────────────────────────────────


def test_leading_zero_identifiers_not_suggested_as_integer():
    """Verify that postal codes/IDs like '01234' are NOT suggested as integers."""
    df = pd.DataFrame({"zip_code": ["01234", "05401", "07030", "00210"]})
    suggestions = TypeDetectorService.suggest_types(df)
    zip_sugg = [s for s in suggestions if s["column"] == "zip_code"]
    # Should not suggest integer because leading zeros would be destroyed
    assert len(zip_sugg) == 0


def test_type_conversion_handles_currency_and_accounting():
    df = pd.DataFrame({
        "price": ["$1,250.00", "€45.50", "£100", "₹500.25"],
        "profit": ["$500.00", "(200.00)", "$100.50", "(50.00)"],
    })
    conv_price, aff_p, _ = TypeDetectorService.convert_type(df["price"], "float")
    assert conv_price.iloc[0] == 1250.00
    assert conv_price.iloc[1] == 45.50
    assert conv_price.iloc[2] == 100.0
    assert conv_price.iloc[3] == 500.25

    conv_profit, _, _ = TypeDetectorService.convert_type(df["profit"], "float")
    assert conv_profit.iloc[0] == 500.00
    assert conv_profit.iloc[1] == -200.00  # Accounting format (200.00) -> -200.00
    assert conv_profit.iloc[3] == -50.00


# ─── 6. Spreadsheet Formula Injection Prevention ────────────────────────────


def test_formula_injection_sanitization():
    df = pd.DataFrame({
        "name": ["=cmd|' /C calc'!A0", "+1234", "-danger", "@SUM(A1:B2)", "Normal Text"],
        "num": [-15.5, 42.0, -100, 0, 5],
        "legit_neg_str": ["-15.5", "+42", "-100", "safe", "=calc"],
    })
    sanitized = sanitize_for_spreadsheet(df)
    # Dangerous formula triggers escaped with single quote:
    assert sanitized["name"].iloc[0] == "'=cmd|' /C calc'!A0"
    assert sanitized["name"].iloc[2] == "'-danger"
    assert sanitized["name"].iloc[3] == "'@SUM(A1:B2)"
    assert sanitized["name"].iloc[4] == "Normal Text"

    # Numeric column preserved intact:
    assert sanitized["num"].iloc[0] == -15.5
    assert sanitized["num"].iloc[2] == -100

    # String with valid numeric representation not altered:
    assert sanitized["legit_neg_str"].iloc[0] == "-15.5"
    assert sanitized["legit_neg_str"].iloc[4] == "'=calc"


# ─── 7. End-to-End API Ingestion, Cleaning, and Export ──────────────────────


def test_e2e_sample_data_workflow():
    # 1. Load sample dataset
    res_sample = client.post("/api/v1/datasets/sample")
    assert res_sample.status_code == 201
    data = res_sample.json()
    ds_id = data["dataset_id"]
    assert data["row_count"] > 0
    assert data["is_sample"] is True

    # 2. Get profile
    res_profile = client.get(f"/api/v1/datasets/{ds_id}/profile")
    assert res_profile.status_code == 200
    p_data = res_profile.json()
    assert p_data["row_count"] > 0
    assert len(p_data["columns"]) > 0

    # 3. Clean missing values on a column (e.g. 'salary')
    res_missing_prev = client.post(
        f"/api/v1/datasets/{ds_id}/clean/missing?preview=true",
        json={"column": "salary", "method": "median"},
    )
    assert res_missing_prev.status_code == 200
    prev_json = res_missing_prev.json()
    assert prev_json["operation_id"] is None
    assert prev_json["detected_dtype"] is not None

    res_missing_apply = client.post(
        f"/api/v1/datasets/{ds_id}/clean/missing?preview=false",
        json={"column": "salary", "method": "median"},
    )
    assert res_missing_apply.status_code == 200
    apply_json = res_missing_apply.json()
    assert apply_json["operation_id"] is not None

    # 4. Clean duplicates with configurable keep policy
    res_dup = client.post(
        f"/api/v1/datasets/{ds_id}/clean/duplicates?preview=false",
        json={"keep": "first", "ignore_case": True},
    )
    assert res_dup.status_code == 200
    dup_json = res_dup.json()
    assert dup_json["operation_id"] is not None

    # 5. Export dataset as CSV and verify UTF-8 BOM
    res_export = client.get(f"/api/v1/datasets/{ds_id}/export?format=csv")
    assert res_export.status_code == 200
    csv_bytes = res_export.content
    assert csv_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
    # Round-trip verify that exported CSV can be reopened
    reloaded_df = pd.read_csv(io.BytesIO(csv_bytes), encoding="utf-8-sig")
    assert len(reloaded_df) == len(session_store.get(ds_id))

    # 6. Export dataset as XLSX and verify
    res_export_xlsx = client.get(f"/api/v1/datasets/{ds_id}/export?format=xlsx")
    assert res_export_xlsx.status_code == 200
    reloaded_xlsx = pd.read_excel(io.BytesIO(res_export_xlsx.content))
    assert len(reloaded_xlsx) == len(session_store.get(ds_id))

    # 7. Undo operation and verify state restoration
    res_undo = client.post(f"/api/v1/datasets/{ds_id}/undo")
    assert res_undo.status_code == 200
    undo_data = res_undo.json()
    assert undo_data["can_redo"] is True
