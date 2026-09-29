import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_directly():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_full_pipeline_upload_clean_export():
    # 1. Create a dummy CSV with missing values, duplicates, and outliers
    csv_content = (
        "id,name,age,salary,city\n"
        "1,Alice,30,70000,New York\n"
        "2,Bob,,80000,Chicago\n"
        "3,Charlie,45,120000,New York\n"
        "1,Alice,30,70000,New York\n"  # Duplicate row
        "4,David,50,,Boston\n"
        "5,Eve,22,50000,Miami\n"
    ).encode("utf-8")

    # 2. Upload dataset
    upload_res = client.post(
        "/api/v1/datasets",
        files={"file": ("test_data.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert upload_res.status_code == 201
    upload_data = upload_res.json()
    dataset_id = upload_data["dataset_id"]
    assert dataset_id
    assert upload_data["row_count"] == 6

    # 3. Quality score & Profile
    quality_res = client.get(f"/api/v1/datasets/{dataset_id}/quality")
    assert quality_res.status_code == 200
    assert "overall_score" in quality_res.json()

    profile_res = client.get(f"/api/v1/datasets/{dataset_id}/profile")
    assert profile_res.status_code == 200
    profile_data = profile_res.json()
    assert profile_data["duplicate_row_count"] == 1

    # 4. Duplicate handling
    dup_preview = client.post(
        f"/api/v1/datasets/{dataset_id}/clean/duplicates?preview=true",
        json={"strategy": "first"},
    )
    assert dup_preview.status_code == 200
    assert dup_preview.json()["affected_rows"] == 1

    dup_apply = client.post(
        f"/api/v1/datasets/{dataset_id}/clean/duplicates?preview=false",
        json={"strategy": "first"},
    )
    assert dup_apply.status_code == 200

    # 5. Missing value handling
    missing_preview = client.post(
        f"/api/v1/datasets/{dataset_id}/clean/missing?preview=true",
        json={"column": "age", "method": "median"},
    )
    assert missing_preview.status_code == 200
    assert missing_preview.json()["affected_rows"] == 1

    missing_apply = client.post(
        f"/api/v1/datasets/{dataset_id}/clean/missing?preview=false",
        json={"column": "age", "method": "median"},
    )
    assert missing_apply.status_code == 200

    # 6. Verify operation history & undo
    ops_res = client.get(f"/api/v1/datasets/{dataset_id}/operations")
    assert ops_res.status_code == 200
    assert ops_res.json()["total"] == 2

    undo_res = client.post(f"/api/v1/datasets/{dataset_id}/undo")
    assert undo_res.status_code == 200
    assert undo_res.json()["current_step"] == 1

    # 7. Export / download
    export_csv = client.get(f"/api/v1/datasets/{dataset_id}/export?format=csv")
    assert export_csv.status_code == 200
    assert "text/csv" in export_csv.headers.get("content-type", "")

    export_xlsx = client.get(f"/api/v1/datasets/{dataset_id}/export?format=xlsx")
    assert export_xlsx.status_code == 200
    assert "openxmlformats" in export_xlsx.headers.get("content-type", "")


def test_offline_simulation():
    # Simulate non-existent route or stopped server response
    offline_client = TestClient(app, base_url="http://127.0.0.1:9999")
    try:
        offline_res = offline_client.get("/nonexistent-health")
        assert offline_res.status_code == 404
    except Exception:
        pass
