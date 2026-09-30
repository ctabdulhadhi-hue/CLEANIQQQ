import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from app.core.errors import AppError
from app.core.session_store import DatasetSession, OperationRecord
from app.services.cleaner import preview_operation
from app.services.outliers import OutlierDetectorService
from app.services.quality import QualityScoreService
from app.services.missing_detector import MissingValueService
from app.services.type_detector import TypeDetectorService
from app.services.report import ReportGeneratorService


# ─── 1. Cleaner: Removed-Row Preview Diffs ───────────────────────────────────


def test_preview_drop_duplicates_generates_sample_diffs():
    """Verify that dropping duplicate rows correctly identifies and returns removed row diffs."""
    df = pd.DataFrame({
        "id": [1, 2, 3, 2, 4],
        "name": ["Alice", "Bob", "Charlie", "Bob", "Dave"],
        "score": [90, 80, 85, 80, 95],
    })

    preview = preview_operation(
        df=df,
        dataset_id="test_ds",
        operation="drop_duplicates",
        columns=["name", "score"],
        params={"keep": "first"},
    )

    assert preview["affected_row_count"] == 1
    assert preview["total_rows_before"] == 5
    assert preview["total_rows_after"] == 4
    # The duplicate row (index 3) must be in sample_diffs
    assert len(preview["sample_diffs"]) > 0
    diff_cols = [d.column for d in preview["sample_diffs"]]
    assert "name" in diff_cols or "score" in diff_cols
    # Verify that before contains the removed data and after is None
    for d in preview["sample_diffs"]:
        assert d.row_index == 3
        assert d.after is None


def test_preview_drop_missing_rows_generates_sample_diffs():
    """Verify that dropping rows with missing values returns accurate diffs."""
    df = pd.DataFrame({
        "col_a": [10, np.nan, 30, 40],
        "col_b": ["apple", "banana", None, "date"],
    })

    preview = preview_operation(
        df=df,
        dataset_id="test_ds",
        operation="drop_missing_rows",
        columns=["col_a"],
        params={"how": "any"},
    )

    assert preview["affected_row_count"] == 1
    assert preview["total_rows_before"] == 4
    assert preview["total_rows_after"] == 3
    assert len(preview["sample_diffs"]) > 0
    # Row index 1 had missing col_a
    assert any(d.row_index == 1 for d in preview["sample_diffs"])


# ─── 2. Outliers: Preserve Non-Numeric Text ─────────────────────────────────


def test_outlier_removal_preserves_non_numeric_values():
    """Ensure outlier removal deletes only statistical outliers, not non-numeric text rows."""
    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5, 6, 7],
        "val": [10, 12, 11, "unparseable_string", 10, 1000, 11],
    })

    result_df, affected, summary = OutlierDetectorService.handle_outliers(
        df=df,
        column="val",
        method="iqr",
        action="remove",
        multiplier=1.5,
    )

    # 1000 is an outlier; "unparseable_string" is text and must NOT be silently deleted
    assert affected == 1
    assert len(result_df) == 6
    assert "unparseable_string" in result_df["val"].values
    assert 1000 not in result_df["val"].values


def test_outlier_capping_preserves_non_numeric_values():
    """Ensure outlier capping caps only outliers and leaves non-numeric text untouched."""
    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5, 6, 7],
        "val": [10, 12, 11, "unparseable_string", 10, 1000, 11],
    })

    result_df, affected, summary = OutlierDetectorService.handle_outliers(
        df=df,
        column="val",
        method="iqr",
        action="cap",
        multiplier=1.5,
    )

    assert affected == 1
    assert len(result_df) == 7
    # "unparseable_string" must remain intact
    assert result_df.at[3, "val"] == "unparseable_string"
    # 1000 must be capped below 100
    assert float(result_df.at[5, "val"]) < 100


# ─── 3. Quality: Timezone-Aware Timestamps ───────────────────────────────────


def test_quality_scoring_with_timezone_aware_timestamps():
    """Verify that timezone-aware ISO-8601 strings do not crash quality scoring."""
    df = pd.DataFrame({
        "customer_id": [101, 102, 103],
        "created_at": [
            "2024-01-15T10:30:00Z",
            "2024-02-20T14:45:00+02:00",
            "2024-03-10T08:00:00-05:00",
        ],
        "amount": [150.0, 200.0, 350.0],
    })

    # Should compute without raising TypeError
    quality = QualityScoreService.compute(df)
    assert quality["overall_score"] > 0
    sub_dict = {s["name"]: s["score"] for s in quality["sub_scores"]}
    assert sub_dict["completeness"] == 1.0
    assert sub_dict["validity"] == 1.0


# ─── 4. Missing Imputation: Integer & Nullable Types ─────────────────────────


def test_impute_mean_non_integer_float_on_nullable_int():
    """Ensure mean imputation of a non-integer float (e.g. 17.5) does not raise TypeError on Int64."""
    # [10, 25, NA] -> sum=35, count=2, mean=17.5
    s = pd.Series([10, 25, pd.NA], dtype="Int64")
    res, count, rem, fill_val = MissingValueService.safe_impute(s, "col", "mean")

    assert count == 1
    assert rem == 0
    assert fill_val == 17.5
    assert res.iloc[2] == 17.5
    assert pd.api.types.is_float_dtype(res)


def test_impute_median_non_integer_float_on_int_series():
    """Ensure median imputation of a non-integer float (e.g. 1.5) works on integer series."""
    # [1, 2, None] -> median=1.5
    s = pd.Series([1, 2, None], dtype=object)
    s_num = pd.to_numeric(s, errors="coerce")
    res, count, rem, fill_val = MissingValueService.safe_impute(s_num, "col", "median")

    assert count == 1
    assert fill_val == 1.5
    assert res.iloc[2] == 1.5


def test_impute_custom_float_on_integer_series():
    """Ensure entering a float constant (e.g. 3.14) into an integer column converts safely."""
    s = pd.Series([10, 20, np.nan], dtype=float)
    res, count, rem, fill_val = MissingValueService.safe_impute(s, "col", "constant", value="3.14")

    assert count == 1
    assert fill_val == 3.14
    assert res.iloc[2] == 3.14


# ─── 5. Type Conversion: errors_strategy ─────────────────────────────────────


def test_convert_type_errors_strategy_coerce():
    """errors_strategy='coerce' sets unparseable values to null (default)."""
    s = pd.Series(["10", "20", "invalid_number", "40"])
    converted, affected, summary = TypeDetectorService.convert_type(
        series=s,
        target_type="integer",
        errors_strategy="coerce",
    )
    assert pd.isna(converted.iloc[2])
    assert converted.iloc[0] == 10
    assert "unparseable value(s) set to null" in summary


def test_convert_type_errors_strategy_raise():
    """errors_strategy='raise' raises AppError if any value cannot be converted."""
    s = pd.Series(["10", "20", "not_a_number", "40"])
    with pytest.raises(AppError) as exc_info:
        TypeDetectorService.convert_type(
            series=s,
            target_type="integer",
            errors_strategy="raise",
        )
    assert exc_info.value.code == "TYPE_CONVERSION_ERROR"
    assert "cannot be safely parsed" in exc_info.value.message


def test_convert_type_errors_strategy_ignore():
    """errors_strategy='ignore' returns original series unchanged if conversion produces invalid values."""
    s = pd.Series(["10", "20", "not_a_number", "40"])
    converted, affected, summary = TypeDetectorService.convert_type(
        series=s,
        target_type="integer",
        errors_strategy="ignore",
    )
    assert affected == 0
    assert converted.equals(s)
    assert "Conversion ignored" in summary


# ─── 6. Report: Active Operations Only (Excluding Undone) ────────────────────


def test_report_metrics_exclude_undone_operations():
    """Ensure data quality audit reports count only active steps up to current_step."""
    df_init = pd.DataFrame({"col_a": [10, 20, 30], "col_b": ["A", "B", "C"]})
    session = DatasetSession("test_report_session", df_init)

    # Step 1: apply op 1
    rec1 = OperationRecord(
        operation="text_trim",
        params={"column": "col_b"},
        columns_affected=["col_b"],
        affected_row_count=1,
        rows_before=3,
        rows_after=3,
    )
    session.push_operation(rec1)

    # Step 2: apply op 2
    rec2 = OperationRecord(
        operation="clean_missing",
        params={"column": "col_a", "method": "drop"},
        columns_affected=["col_a"],
        affected_row_count=1,
        rows_before=3,
        rows_after=2,
    )
    session.push_operation(rec2)
    session.df = session.df.iloc[:2].copy()

    assert session.current_step == 2
    assert len(session.history) == 2

    # Verify report with 2 active ops
    report2 = ReportGeneratorService._compute_report_metrics(session)
    assert report2["total_operations"] == 2
    assert len(report2["applied_ops"]) == 2

    # Now UNDO 1 operation
    session.undo()
    assert session.current_step == 1
    assert len(session.history) == 2  # history contains 2, but current_step is 1

    # Verify report now excludes the undone operation
    report1 = ReportGeneratorService._compute_report_metrics(session)
    assert report1["total_operations"] == 1
    assert len(report1["applied_ops"]) == 1
    assert report1["applied_ops"][0]["operation"] == "text_trim"
