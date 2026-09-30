import io
import pandas as pd
import pytest
from app.services.file_parser import parse_uploaded_file, SAFE_CSV_NA_VALUES
from app.services.order_validator import OrderValidatorService
from app.services.text_cleaner import TextCleanerService


def test_csv_delimiters_and_streaming_bytesio():
    """Verify that comma, tab, semicolon, and pipe delimited CSVs parse correctly."""
    # Comma
    csv_comma = b"col_a,col_b\n1,apple\n2,banana\n"
    df_comma = parse_uploaded_file("test.csv", csv_comma)
    assert len(df_comma) == 2
    assert list(df_comma.columns) == ["col_a", "col_b"]
    assert df_comma["col_b"].iloc[0] == "apple"

    # Tab
    csv_tab = b"col_a\tcol_b\n1\tapple\n2\tbanana\n"
    df_tab = parse_uploaded_file("test.tsv", csv_tab)
    assert len(df_tab) == 2
    assert list(df_tab.columns) == ["col_a", "col_b"]

    # Semicolon
    csv_semi = b"col_a;col_b\n1;apple\n2;banana\n"
    df_semi = parse_uploaded_file("test.csv", csv_semi)
    assert len(df_semi) == 2
    assert list(df_semi.columns) == ["col_a", "col_b"]

    # Pipe
    csv_pipe = b"col_a|col_b\n1|apple\n2|banana\n"
    df_pipe = parse_uploaded_file("test.csv", csv_pipe)
    assert len(df_pipe) == 2
    assert list(df_pipe.columns) == ["col_a", "col_b"]


def test_csv_encodings_support():
    """Verify utf-8, latin1, and utf-8-sig encodings."""
    # Latin-1 with accented characters
    text_latin1 = "name,city\nRené,Montréal\nJosé,São Paulo\n"
    bytes_latin1 = text_latin1.encode("latin1")
    df_latin1 = parse_uploaded_file("latin1.csv", bytes_latin1)
    assert len(df_latin1) == 2
    assert "René" in df_latin1["name"].values

    # UTF-8 with BOM
    text_bom = "id,value\n100,Test\n"
    bytes_bom = text_bom.encode("utf-8-sig")
    df_bom = parse_uploaded_file("bom.csv", bytes_bom)
    assert len(df_bom) == 1
    assert "id" in df_bom.columns


def test_csv_preserves_legitimate_na_country_code():
    """Verify that 'NA' (e.g. ISO code for Namibia) is preserved and not converted to null."""
    csv_content = b"country,code\nNamibia,NA\nUnited States,US\n"
    df = parse_uploaded_file("countries.csv", csv_content)
    assert df["code"].iloc[0] == "NA"
    assert pd.notna(df["code"].iloc[0])


def test_order_validator_grouped_performance_and_accuracy():
    """Verify order ID analysis correctly identifies conflicts and order-lines with grouping optimization."""
    # Create dataset with multiple repeated IDs
    data = {
        "order_id": ["ORD-101", "ORD-101", "ORD-102", "ORD-102", "ORD-103"],
        "date": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-03-01", "2024-01-03"],
        "customer": ["Alice", "Alice", "Bob", "Charlie", "Dave"],
        "product": ["Keyboard", "Mouse", "Screen", "Screen", "Cable"],
    }
    df = pd.DataFrame(data)
    analysis = OrderValidatorService.analyze_order_ids(df, "order_id")

    assert analysis["total_rows"] == 5
    assert analysis["unique_order_ids"] == 3
    assert analysis["duplicate_order_ids"] == 2
    # ORD-101 is valid order line (same date & customer)
    # ORD-102 is a conflict (different dates & customers)
    assert analysis["conflicting_order_ids"] == 1
    assert analysis["has_conflict"] is True


def test_text_cleaner_near_duplicates_heuristics():
    """Verify fuzzy clustering accurately identifies variants with heuristics."""
    series = pd.Series([
        "Sales Dept",
        "sales dept",
        "SALES DEPT",
        "  Sales Dept  ",
        "Engineering",
        "engineering",
        "Human Resources",
    ])
    clusters = TextCleanerService.cluster_near_duplicates(series, similarity_threshold=0.85)
    assert len(clusters) >= 2
    cluster_canonicals = [c["canonical"].strip().lower() for c in clusters]
    assert "sales dept" in cluster_canonicals
    assert "engineering" in cluster_canonicals
