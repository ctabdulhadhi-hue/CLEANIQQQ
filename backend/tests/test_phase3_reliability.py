import io
import pandas as pd
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.session_store import session_store
from app.routes.datasets import sanitize_for_spreadsheet

client = TestClient(app)


# ==============================================================================
# 1. Health Contract Alignment & Session Counting
# ==============================================================================

def test_health_contract_schema_and_types():
    """Validates that /health and /api/health return status, app, version, active_sessions."""
    for path in ["/health", "/api/health", "/"]:
        res = client.get(path)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["app"] == "CleanIQ API"
        assert data["version"] == "1.0.0"
        assert isinstance(data["active_sessions"], int)
        assert data["active_sessions"] >= 0


def test_health_active_session_lifecycle():
    """Active session count dynamically tracks sessions added and deleted from session_store."""
    res_before = client.get("/health").json()
    count_before = res_before["active_sessions"]

    test_id = "test_phase3_lifecycle_session"
    session_store.set(test_id, pd.DataFrame({"col": [10, 20, 30]}))

    try:
        res_during = client.get("/health").json()
        assert res_during["active_sessions"] == count_before + 1
    finally:
        session_store.delete(test_id)
        res_after = client.get("/health").json()
        assert res_after["active_sessions"] == count_before


# ==============================================================================
# 2. Spreadsheet Formula Injection (CWE-1236) Protection
# ==============================================================================

def test_formula_injection_leading_whitespace_and_triggers():
    """Sanitizes formula triggers =, +, -, @, \\t, \\r with and without leading whitespace."""
    df = pd.DataFrame({
        "direct_formula": ["=cmd|' /C calc'!A0", "+SUM(1,2)", "-danger", "@SUM(A1:B2)", "=1+2"],
        "whitespace_formula": [
            "  =cmd|' /C calc'!A0",
            "\t+alert(1)",
            "   -execute",
            "\r\n@malicious",
            " \t=1+1",
        ],
        "legit_numbers": ["-15.5", " -42.0 ", "+100", " +25.5 ", "-0.001"],
        "normal_text": ["Normal Text", "john.doe@example.com", "Item - Variant A", "123 Main St", "Safe Value"],
        "nulls": [None, np.nan, "None", None, np.nan],
    })

    sanitized = sanitize_for_spreadsheet(df)

    # 1. Direct formula triggers are escaped
    assert sanitized["direct_formula"].iloc[0] == "'=cmd|' /C calc'!A0"
    assert sanitized["direct_formula"].iloc[1] == "'+SUM(1,2)"
    assert sanitized["direct_formula"].iloc[2] == "'-danger"
    assert sanitized["direct_formula"].iloc[3] == "'@SUM(A1:B2)"
    assert sanitized["direct_formula"].iloc[4] == "'=1+2"

    # 2. Leading whitespace formula triggers are escaped
    assert sanitized["whitespace_formula"].iloc[0] == "'  =cmd|' /C calc'!A0"
    assert sanitized["whitespace_formula"].iloc[1] == "'\t+alert(1)"
    assert sanitized["whitespace_formula"].iloc[2] == "'   -execute"
    assert sanitized["whitespace_formula"].iloc[3] == "'\r\n@malicious"
    assert sanitized["whitespace_formula"].iloc[4] == "' \t=1+1"

    # 3. Legitimate numbers (even with + or - and spaces) are untouched
    assert sanitized["legit_numbers"].iloc[0] == "-15.5"
    assert sanitized["legit_numbers"].iloc[1] == " -42.0 "
    assert sanitized["legit_numbers"].iloc[2] == "+100"
    assert sanitized["legit_numbers"].iloc[3] == " +25.5 "
    assert sanitized["legit_numbers"].iloc[4] == "-0.001"

    # 4. Ordinary text is untouched
    assert sanitized["normal_text"].iloc[0] == "Normal Text"
    assert sanitized["normal_text"].iloc[1] == "john.doe@example.com"
    assert sanitized["normal_text"].iloc[2] == "Item - Variant A"

    # 5. Nulls remain null
    assert pd.isna(sanitized["nulls"].iloc[0])
    assert pd.isna(sanitized["nulls"].iloc[1])


def test_formula_injection_categorical_and_numeric_columns():
    """Sanitizes categorical columns while preserving numeric columns intact."""
    df = pd.DataFrame({
        "cat_col": pd.Series(["=SUM(1)", "  @DDE", "safe_category", "-50.0"], dtype="category"),
        "int_col": [10, -20, 30, -40],
        "float_col": [1.5, -2.5, 3.5, -4.5],
    })

    sanitized = sanitize_for_spreadsheet(df)

    # Categorical formulas are escaped
    assert sanitized["cat_col"].iloc[0] == "'=SUM(1)"
    assert sanitized["cat_col"].iloc[1] == "'  @DDE"
    assert sanitized["cat_col"].iloc[2] == "safe_category"
    assert sanitized["cat_col"].iloc[3] == "-50.0"  # legitimate number preserved

    # Numeric columns remain unchanged numeric types
    assert sanitized["int_col"].tolist() == [10, -20, 30, -40]
    assert sanitized["float_col"].tolist() == [1.5, -2.5, 3.5, -4.5]


def test_formula_injection_column_headers():
    """Sanitizes formula injection triggers in column headers."""
    df = pd.DataFrame({
        "=cmd|calc": [1, 2],
        "  @DDE_header": [3, 4],
        "safe_header": [5, 6],
    })

    sanitized = sanitize_for_spreadsheet(df)
    cols = list(sanitized.columns)

    assert cols[0] == "'=cmd|calc"
    assert cols[1] == "'  @DDE_header"
    assert cols[2] == "safe_header"


def test_export_endpoints_apply_formula_sanitization():
    """Export endpoints for CSV and XLSX apply spreadsheet sanitization on output."""
    csv_input = "name,formula_col\nAlice,=cmd|' /C calc'!A0\nBob,  @SUM(10)\nCharlie,-42.5\n"
    res_upload = client.post(
        "/api/v1/datasets",
        files={"file": ("test_export_security.csv", io.BytesIO(csv_input.encode("utf-8")), "text/csv")},
    )
    assert res_upload.status_code == 201
    dataset_id = res_upload.json()["dataset_id"]

    try:
        # CSV Export
        res_csv = client.get(f"/api/v1/datasets/{dataset_id}/export?format=csv")
        assert res_csv.status_code == 200
        csv_text = res_csv.content.decode("utf-8-sig")
        assert "'=cmd|" in csv_text
        assert "'  @SUM(10)" in csv_text
        # Legitimate number -42.5 is not prefixed with '
        assert ",-42.5" in csv_text

        # Excel Export
        res_xlsx = client.get(f"/api/v1/datasets/{dataset_id}/export?format=xlsx")
        assert res_xlsx.status_code == 200
        df_excel = pd.read_excel(io.BytesIO(res_xlsx.content))
        assert df_excel["formula_col"].iloc[0] == "'=cmd|' /C calc'!A0"
        assert df_excel["formula_col"].iloc[1] == "'  @SUM(10)"
    finally:
        session_store.delete(dataset_id)
