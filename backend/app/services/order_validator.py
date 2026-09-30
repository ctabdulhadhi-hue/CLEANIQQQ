import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np


class OrderValidatorService:
    """
    Intelligent Order ID and Transaction Integrity Validation Service.
    
    Distinguishes between:
    - Order-level data (1 row per order)
    - Order-line data (multiple rows per order, e.g. multi-item orders)
    
    Detects genuine conflicts:
    When the same Order ID appears across different dates, customers, cities,
    or other transaction-level invariant attributes.
    """

    ID_COLUMN_PATTERNS = [
        r"^order[-_ ]?id$",
        r"^order[-_ ]?no$",
        r"^order[-_ ]?number$",
        r"^orderid$",
        r"^ord[-_ ]?id$",
        r"^invoice[-_ ]?id$",
        r"^invoice[-_ ]?no$",
        r"^transaction[-_ ]?id$",
        r"^txn[-_ ]?id$",
    ]

    DATE_PATTERNS = [
        r"date", r"time", r"created_at", r"order_date", r"timestamp", r"day"
    ]

    CUSTOMER_PATTERNS = [
        r"customer", r"client", r"buyer", r"user", r"city", r"email", r"channel", r"store"
    ]

    PRODUCT_PATTERNS = [
        r"product", r"item", r"sku", r"description", r"category", r"title"
    ]

    @classmethod
    def find_order_id_column(cls, df: pd.DataFrame) -> Optional[str]:
        """Identifies the most likely Order ID column in the DataFrame."""
        cols = list(df.columns)
        
        # 1. Exact regex match
        for col in cols:
            col_lower = str(col).strip().lower()
            for pattern in cls.ID_COLUMN_PATTERNS:
                if re.match(pattern, col_lower):
                    return col

        # 2. Contains order and id
        for col in cols:
            col_lower = str(col).strip().lower()
            if "order" in col_lower and "id" in col_lower:
                return col

        # 3. Fallback to any column ending in _id or id where values look like ORD-xxx or ID-xxx
        for col in cols:
            col_lower = str(col).strip().lower()
            if col_lower.endswith("_id") or col_lower == "id":
                sample_vals = df[col].dropna().astype(str).head(10)
                if any(re.match(r"^[A-Za-z]+[-_0-9]+", s) for s in sample_vals):
                    return col

        return None

    @classmethod
    def _find_matching_columns(cls, df: pd.DataFrame, patterns: List[str]) -> List[str]:
        """Finds all columns matching any of the regex patterns."""
        matches = []
        for col in df.columns:
            col_lower = str(col).strip().lower()
            if any(re.search(pat, col_lower) for pat in patterns):
                matches.append(col)
        return matches

    @classmethod
    def analyze_order_ids(cls, df: pd.DataFrame, order_id_col: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes the DataFrame for duplicate and conflicting Order IDs.
        Determines whether data is order-level or order-line.
        """
        total_rows = len(df)
        if total_rows == 0:
            return {
                "order_id_column": None,
                "total_rows": 0,
                "unique_order_ids": 0,
                "duplicate_order_ids_count": 0,
                "conflicting_order_ids_count": 0,
                "rows_affected": 0,
                "has_conflict": False,
                "detected_structure": "order_level",
                "warning_message": "Dataset is empty.",
                "conflict_table": [],
            }

        target_col = order_id_col or cls.find_order_id_column(df)
        if not target_col or target_col not in df.columns:
            return {
                "order_id_column": None,
                "total_rows": total_rows,
                "unique_order_ids": 0,
                "duplicate_order_ids_count": 0,
                "conflicting_order_ids_count": 0,
                "rows_affected": 0,
                "has_conflict": False,
                "detected_structure": "order_level",
                "warning_message": "No Order ID column detected in this dataset.",
                "conflict_table": [],
            }

        series = df[target_col]
        # Drop or treat nulls
        non_null_series = series.dropna().astype(str).str.strip()
        unique_order_ids = int(non_null_series.nunique())
        
        # Counts per ID
        value_counts = non_null_series.value_counts()
        duplicate_ids_series = value_counts[value_counts > 1]
        duplicate_order_ids_count = int(len(duplicate_ids_series))

        # Detect transaction-level grouping columns
        date_cols = [c for c in cls._find_matching_columns(df, cls.DATE_PATTERNS) if c != target_col]
        customer_cols = [c for c in cls._find_matching_columns(df, cls.CUSTOMER_PATTERNS) if c != target_col]
        product_cols = [c for c in cls._find_matching_columns(df, cls.PRODUCT_PATTERNS) if c != target_col]

        # Analyze each duplicate ID
        conflict_table: List[Dict[str, Any]] = []
        conflicting_ids_count = 0
        rows_affected = 0
        valid_order_line_count = 0

        # Full column normalized for grouping
        clean_col_series = df[target_col].fillna("").astype(str).str.strip()

        # Pre-group only rows with duplicate IDs to avoid O(N*M) repeated dataframe scanning
        if not duplicate_ids_series.empty:
            dup_keys_set = set(duplicate_ids_series.index.astype(str))
            dup_mask = clean_col_series.isin(dup_keys_set)
            grouped = df[dup_mask].groupby(clean_col_series[dup_mask], sort=False)
        else:
            grouped = None

        # We inspect each duplicate ID
        for order_id_val, count in duplicate_ids_series.items():
            str_key = str(order_id_val)
            if grouped is not None and str_key in grouped.groups:
                subset = grouped.get_group(str_key)
            else:
                subset = df[clean_col_series == str_key]
            occurrences = int(count)

            # Check distinct dates
            diff_dates = False
            distinct_dates: List[str] = []
            for d_col in date_cols:
                d_vals = subset[d_col].dropna().astype(str).str.strip().unique().tolist()
                if len(d_vals) > 1:
                    diff_dates = True
                    distinct_dates.extend(d_vals[:5])
                    break
                elif len(d_vals) == 1 and not distinct_dates:
                    distinct_dates.append(d_vals[0])

            # Check distinct customers/cities
            diff_customers = False
            distinct_customers: List[str] = []
            for c_col in customer_cols:
                c_vals = subset[c_col].dropna().astype(str).str.strip().unique().tolist()
                if len(c_vals) > 1:
                    diff_customers = True
                    distinct_customers.extend(c_vals[:5])
                    break
                elif len(c_vals) == 1 and not distinct_customers:
                    distinct_customers.append(c_vals[0])

            # Check distinct products
            diff_products = False
            distinct_products: List[str] = []
            for p_col in product_cols:
                p_vals = subset[p_col].dropna().astype(str).str.strip().unique().tolist()
                if len(p_vals) > 1:
                    diff_products = True
                    distinct_products.extend(p_vals[:5])
                    break
                elif len(p_vals) == 1 and not distinct_products:
                    distinct_products.append(p_vals[0])

            # A conflict is present when the SAME order_id is associated with:
            # - Multiple transaction dates, OR
            # - Multiple customers / cities / sales channels
            # If dates and customers are identical, but products differ, it is valid order-line items!
            is_conflict = diff_dates or diff_customers

            if is_conflict:
                status = "Conflict"
                conflicting_ids_count += 1
                rows_affected += occurrences
            else:
                status = "Valid Order-Line"
                valid_order_line_count += 1

            conflict_table.append({
                "order_id": str(order_id_val),
                "occurrences": occurrences,
                "different_dates": "Yes" if diff_dates else "No",
                "dates": distinct_dates[:3],
                "different_customers": "Yes" if diff_customers else "No",
                "customers": distinct_customers[:3],
                "different_products": "Yes" if diff_products else "No",
                "products": distinct_products[:3],
                "status": status,
            })

        # Determine overall dataset structure
        # If there are duplicate IDs and most are valid order-line items with NO conflicts:
        # structure is 'order_line'. If conflicts exist or IDs are unique:
        if conflicting_ids_count > 0:
            detected_structure = "order_level_with_conflicts"
            warning_message = "Potential Order ID conflict detected: the same Order ID is associated with multiple transactions."
            has_conflict = True
        elif valid_order_line_count > 0:
            detected_structure = "order_line"
            warning_message = "Order-line structure detected: repeated Order IDs share the same transaction date and customer."
            has_conflict = False
        else:
            detected_structure = "order_level"
            warning_message = "All Order IDs are unique."
            has_conflict = False

        # Sort conflict table so conflicts appear first, then by occurrences descending
        conflict_table.sort(key=lambda x: (0 if x["status"] == "Conflict" else 1, -x["occurrences"]))

        return {
            "order_id_column": target_col,
            "total_rows": total_rows,
            "unique_order_ids": unique_order_ids,
            "duplicate_order_ids": duplicate_order_ids_count,
            "duplicate_order_ids_count": duplicate_order_ids_count,
            "conflicting_order_ids": conflicting_ids_count,
            "conflicting_order_ids_count": conflicting_ids_count,
            "rows_affected": rows_affected,
            "has_conflict": has_conflict,
            "dataset_structure": detected_structure,
            "detected_structure": detected_structure,
            "warning_message": warning_message,
            "conflict_table": conflict_table,
            "problematic_ids": conflict_table,
            "date_columns_checked": date_cols,
            "customer_columns_checked": customer_cols,
            "product_columns_checked": product_cols,
        }

    @classmethod
    def generate_unique_order_ids(
        cls,
        df: pd.DataFrame,
        order_id_col: Optional[str] = None,
        mode: str = "conflicts_only",  # 'conflicts_only' or 'all_rows'
        prefix: Optional[str] = None,
        start_number: int = 1,
        scope: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Safely generates new unique Order IDs preserving format (e.g. ORD-001).
        
        Guarantees:
        - Unique
        - Sequential where appropriate
        - Consistent prefix & zero-padding
        - Free from null values
        - Free from accidental duplicates
        - Detailed cleaning log
        """
        if scope:
            mode = scope
        result_df = df.copy()
        target_col = order_id_col or cls.find_order_id_column(df)
        if not target_col or target_col not in result_df.columns:
            raise ValueError("No valid Order ID column found to regenerate.")

        # Detect existing format pattern (e.g. ORD-001 -> prefix 'ORD-', padding 3)
        sample_vals = result_df[target_col].dropna().astype(str).tolist()
        detected_prefix = "ORD-"
        padding = 3

        for val in sample_vals:
            m = re.match(r"^([A-Za-z]+[-_]?)([0-9]+)$", str(val).strip())
            if m:
                detected_prefix = m.group(1)
                padding = max(padding, len(m.group(2)))
                break

        use_prefix = prefix or detected_prefix
        # Determine max padding based on row count
        required_digits = len(str(len(result_df) + start_number))
        padding = max(padding, required_digits)

        # Analysis of conflicts
        analysis = cls.analyze_order_ids(result_df, target_col)
        conflicting_ids = {item["order_id"] for item in analysis["conflict_table"] if item["status"] == "Conflict"}

        rows_updated = 0
        log_messages = []

        if mode == "all_rows":
            # Renumber every row sequentially
            new_ids = [
                f"{use_prefix}{str(i).zfill(padding)}"
                for i in range(start_number, start_number + len(result_df))
            ]
            result_df[target_col] = new_ids
            rows_updated = len(result_df)
            log_messages.append(
                f"Generated {rows_updated} new unique Order IDs sequentially from {new_ids[0]} to {new_ids[-1]}."
            )
        else:
            # conflicts_only mode:
            # We keep genuine unique IDs and valid order-line IDs intact.
            # For each conflicting Order ID, each distinct transaction (date + customer) gets a new unique ID!
            # If multiple rows share the same date + customer under that conflicting ID, they receive the SAME new ID!
            
            # Find the highest existing sequence number so new IDs do not collide
            existing_numbers = []
            for val in sample_vals:
                num_match = re.search(r"(\d+)", str(val))
                if num_match:
                    try:
                        existing_numbers.append(int(num_match.group(1)))
                    except ValueError:
                        pass
            
            curr_counter = max(existing_numbers, default=0) + 1
            if curr_counter < start_number:
                curr_counter = start_number

            # Group conflicting rows by (order_id, date, customer)
            date_cols = analysis.get("date_columns_checked", [])
            customer_cols = analysis.get("customer_columns_checked", [])
            
            # Mapping from (order_id, date_val, cust_val) -> new_id
            assigned_map: Dict[Tuple, str] = {}
            new_series = result_df[target_col].copy()

            # Pre-filter to only iterate over conflicting or null rows
            if conflicting_ids:
                conflict_mask = (
                    result_df[target_col].isna()
                    | result_df[target_col].astype(str).str.strip().isin(conflicting_ids)
                )
            else:
                conflict_mask = result_df[target_col].isna()

            for idx in result_df.index[conflict_mask]:
                val = result_df.at[idx, target_col]
                s_val = str(val).strip() if pd.notna(val) else ""
                d_val = str(result_df.at[idx, date_cols[0]]).strip() if date_cols else ""
                c_val = str(result_df.at[idx, customer_cols[0]]).strip() if customer_cols else ""

                key = (s_val, d_val, c_val, idx if not (d_val or c_val) else "")
                # If this transaction has not yet received a new unique ID:
                if key not in assigned_map:
                    new_id = f"{use_prefix}{str(curr_counter).zfill(padding)}"
                    assigned_map[key] = new_id
                    curr_counter += 1

                new_series.at[idx] = assigned_map[key]
                rows_updated += 1

            result_df[target_col] = new_series
            log_messages.append(
                f"Resolved Order ID conflicts: generated new unique Order IDs for {rows_updated} conflicting rows across {len(conflicting_ids)} ambiguous IDs."
            )

        # Vectorized diff extraction: avoids expensive O(N) df.iloc indexing
        old_vals = df[target_col].astype(str).to_numpy()
        new_vals = result_df[target_col].astype(str).to_numpy()
        changed_mask = old_vals != new_vals
        changed_positions = np.flatnonzero(changed_mask)
        diffs = [
            {
                "row_index": int(pos),
                "column": target_col,
                "old_value": str(old_vals[pos]),
                "new_value": str(new_vals[pos]),
            }
            for pos in changed_positions
        ]

        return result_df, {
            "rows_affected": rows_updated,
            "column": target_col,
            "mode": mode,
            "prefix": use_prefix,
            "logs": log_messages,
            "diffs": diffs,
        }
