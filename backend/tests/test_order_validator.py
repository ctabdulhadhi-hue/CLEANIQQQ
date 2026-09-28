import pytest
import pandas as pd
from app.services.order_validator import OrderValidatorService
from app.services.quality import QualityScoreService
from app.core.session_store import session_store, DatasetSession
from app.services.cleaner import preview_operation, apply_operation

def test_order_id_unique_detection():
    df = pd.DataFrame({
        "order_id": ["ORD-001", "ORD-002", "ORD-003"],
        "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "product_name": ["Desk", "Chair", "Lamp"],
        "price": [100, 50, 20],
        "quantity": [1, 2, 1],
        "total_amount": [100, 100, 20]
    })
    analysis = OrderValidatorService.analyze_order_ids(df, "order_id")
    assert analysis["total_rows"] == 3
    assert analysis["unique_order_ids"] == 3
    assert analysis["duplicate_order_ids"] == 0
    assert analysis["conflicting_order_ids"] == 0
    assert analysis["has_conflict"] is False
    assert analysis["dataset_structure"] == "order_level"

def test_order_id_valid_order_line():
    # Same date & customer/city, different products
    df = pd.DataFrame({
        "order_id": ["ORD-001", "ORD-001", "ORD-002"],
        "date": ["2024-01-01", "2024-01-01", "2024-01-02"],
        "product_name": ["Desk", "Chair", "Lamp"],
        "customer_city": ["Bangalore", "Bangalore", "Chennai"],
        "price": [100, 50, 20],
        "quantity": [1, 1, 1],
        "total_amount": [100, 50, 20]
    })
    analysis = OrderValidatorService.analyze_order_ids(df, "order_id")
    assert analysis["total_rows"] == 3
    assert analysis["unique_order_ids"] == 2
    assert analysis["duplicate_order_ids"] == 1
    assert analysis["conflicting_order_ids"] == 0
    assert analysis["has_conflict"] is False
    assert analysis["dataset_structure"] == "order_line"
    assert len(analysis["problematic_ids"]) == 1
    assert analysis["problematic_ids"][0]["status"] == "Valid Order-Line"

def test_order_id_conflict_detection():
    # Same ID ORD-001 across different dates
    df = pd.DataFrame({
        "order_id": ["ORD-001", "ORD-001", "ORD-002"],
        "date": ["2024-01-01", "2024-02-15", "2024-01-02"],
        "product_name": ["Desk", "Chair", "Lamp"],
        "customer_city": ["Bangalore", "Mumbai", "Chennai"],
        "price": [100, 50, 20],
        "quantity": [1, 1, 1],
        "total_amount": [100, 50, 20]
    })
    analysis = OrderValidatorService.analyze_order_ids(df, "order_id")
    assert analysis["has_conflict"] is True
    assert analysis["conflicting_order_ids"] == 1
    assert analysis["rows_affected"] == 2
    prob = analysis["problematic_ids"][0]
    assert prob["order_id"] == "ORD-001"
    assert prob["status"] == "Conflict"
    assert prob["different_dates"] == "Yes"

def test_generate_unique_order_ids_conflicts_only():
    df = pd.DataFrame({
        "order_id": ["ORD-001", "ORD-001", "ORD-002"],
        "date": ["2024-01-01", "2024-02-15", "2024-01-02"],
        "product_name": ["Desk", "Chair", "Lamp"],
        "price": [100, 50, 20],
        "quantity": [1, 1, 1],
        "total_amount": [100, 50, 20]
    })
    cleaned_df, diffs = OrderValidatorService.generate_unique_order_ids(df, "order_id", scope="conflicts_only")
    assert len(diffs) > 0
    # ORD-002 was not conflicted, should remain
    assert "ORD-002" in cleaned_df["order_id"].values
    # No duplicate IDs should remain
    assert cleaned_df["order_id"].nunique() == 3

def test_quality_summary_16_checks():
    df = pd.DataFrame({
        "order_id": ["ORD-001", "ORD-001", "ORD-002", None],
        "date": ["2024-01-01", "2099-01-01", "not-a-date", "2024-01-02"],
        "product_name": ["  Desk ", "Chair", "Lamp", "Desk"],
        "price": [100, -10, 0, 50],
        "quantity": [1, -2, 0, 1],
        "total_amount": [100, 20, 0, 999]  # 999 != 50*1
    })
    quality = QualityScoreService.compute(df)
    summary = quality.get("summary")
    assert summary is not None
    assert summary["missing_values"] > 0
    assert summary["order_id_conflicts"] >= 0
    assert summary["invalid_values"] > 0
    assert len(summary["metrics"]) == 8
    assert len(summary["issues"]) > 0
    assert summary["overall_score"] > 0
