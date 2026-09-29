import math
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from app.services.profiler import classify_column_type
from app.services.text_cleaner import TextCleanerService
from app.services.type_detector import TypeDetectorService
from app.services.outliers import OutlierDetectorService
from app.services.order_validator import OrderValidatorService
from app.services.missing_detector import MissingValueService


class QualityScoreService:
    """
    Computes a weighted data quality score with four sub-dimensions:
      score = 0.40*completeness + 0.25*consistency + 0.20*validity + 0.15*uniqueness

    Each sub-score ranges from 0.0 to 1.0.
    Also produces a comprehensive Data Quality Summary containing metrics,
    issues breakdown, and order ID transaction integrity analysis.
    """

    WEIGHTS = {
        "completeness": 0.40,
        "consistency": 0.25,
        "validity": 0.20,
        "uniqueness": 0.15,
    }

    @classmethod
    def compute(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Computes overall quality score, four sub-scores, Data Quality Summary,
        and Order ID conflict analysis for the given DataFrame.
        """
        row_count = len(df)
        col_count = len(df.columns)
        total_cells = row_count * col_count

        issues_list: List[Dict[str, Any]] = []

        # ── 1. Completeness Check (Missing Values) ───────────────────────
        if total_cells == 0:
            completeness = 0.0
            completeness_detail = "Empty dataset (0 records)"
            missing_cells = 0
        else:
            missing_by_col = {col: MissingValueService.count_missing(df[col]) for col in df.columns}
            missing_cells = int(sum(missing_by_col.values()))
            completeness = 1.0 - (missing_cells / total_cells)
            completeness = max(0.0, completeness)
            completeness_detail = f"{missing_cells} missing cell(s) out of {total_cells} total"

            if missing_cells > 0:
                cols_with_missing = [str(c) for c in df.columns if missing_by_col[c] > 0]
                issues_list.append({
                    "category": "Missing Values",
                    "severity": "warning" if (missing_cells / total_cells) < 0.1 else "error",
                    "description": f"{missing_cells} missing or null value(s) detected across {len(cols_with_missing)} column(s)",
                    "count": missing_cells,
                    "columns": cols_with_missing[:5],
                })

        # ── 2. Order ID & Transaction Integrity Check ────────────────────
        order_analysis = OrderValidatorService.analyze_order_ids(df)
        dup_order_ids_count = order_analysis.get("duplicate_order_ids_count", 0)
        conflicting_ids_count = order_analysis.get("conflicting_order_ids_count", 0)
        conflicting_rows = order_analysis.get("rows_affected", 0)

        if conflicting_ids_count > 0:
            issues_list.append({
                "category": "Order ID Conflicts",
                "severity": "error",
                "description": f"Potential Order ID conflict: {conflicting_ids_count} Order ID(s) associated with multiple separate transaction dates or customer locations ({conflicting_rows} rows affected).",
                "count": conflicting_ids_count,
                "columns": [order_analysis["order_id_column"]] if order_analysis.get("order_id_column") else [],
            })
        elif dup_order_ids_count > 0 and order_analysis.get("detected_structure") == "order_line":
            issues_list.append({
                "category": "Duplicate Order IDs",
                "severity": "clean",
                "description": f"{dup_order_ids_count} repeated Order ID(s) detected with matching dates/customers (valid order-line item structure).",
                "count": dup_order_ids_count,
                "columns": [order_analysis["order_id_column"]] if order_analysis.get("order_id_column") else [],
            })

        # ── 3. Uniqueness Check (Duplicate Rows) ─────────────────────────
        if row_count == 0:
            uniqueness = 0.0
            uniqueness_detail = "Empty dataset (0 rows)"
            dup_count = 0
        else:
            try:
                dup_count = int(df.duplicated().sum())
            except TypeError:
                dup_count = int(df.astype(str).duplicated().sum())
            
            # Incorporate conflicting IDs into uniqueness deduction
            effective_uniqueness_faults = dup_count + (conflicting_rows // 2 if conflicting_rows > 0 else 0)
            uniqueness = 1.0 - (min(row_count, effective_uniqueness_faults) / row_count)
            uniqueness = max(0.0, uniqueness)
            uniqueness_detail = f"{dup_count} duplicate row(s) and {conflicting_ids_count} conflicting Order ID(s)"

            if dup_count > 0:
                issues_list.append({
                    "category": "Duplicate Rows",
                    "severity": "warning",
                    "description": f"{dup_count} exact duplicate row(s) identified in dataset.",
                    "count": dup_count,
                    "columns": list(df.columns)[:5],
                })

        # ── 4. Whitespace & Text Inconsistency Checks ────────────────────
        whitespace_issues_count = 0
        whitespace_cols = []
        for col in df.columns:
            if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
                str_s = df[col].dropna().astype(str)
                # Count values where strip() != value
                ws_count = int((str_s != str_s.str.strip()).sum())
                if ws_count > 0:
                    whitespace_issues_count += ws_count
                    whitespace_cols.append(str(col))

        if whitespace_issues_count > 0:
            issues_list.append({
                "category": "Leading/Trailing Whitespace",
                "severity": "warning",
                "description": f"{whitespace_issues_count} cell(s) contain untrimmed leading or trailing whitespace.",
                "count": whitespace_issues_count,
                "columns": whitespace_cols[:5],
            })

        # Categorical typo clusters
        cat_columns = [col for col in df.columns if classify_column_type(df[col]) == "categorical"]
        total_cat_cells = 0
        inconsistent_cat_count = 0

        for col in cat_columns:
            non_null_count = int(df[col].notna().sum())
            total_cat_cells += non_null_count
            try:
                clusters = TextCleanerService.cluster_near_duplicates(
                    df[col], similarity_threshold=0.85, max_clusters=50
                )
                for cluster in clusters:
                    inconsistent_cat_count += cluster["total_affected"]
            except Exception:
                pass

        if inconsistent_cat_count > 0:
            issues_list.append({
                "category": "Inconsistent Categories",
                "severity": "warning",
                "description": f"{inconsistent_cat_count} values have near-duplicate spelling variants or casing discrepancies.",
                "count": inconsistent_cat_count,
                "columns": cat_columns[:5],
            })

        # ── 5. Numeric & Business Logic Integrity (Quantities, Prices, Calculations)
        invalid_values_count = 0

        # Look for quantity columns
        qty_cols = [c for c in df.columns if re.search(r"quant|qty|units|item_count", str(c), re.IGNORECASE)]
        negative_qty_count = 0
        zero_qty_count = 0
        for col in qty_cols:
            num_s = pd.to_numeric(df[col], errors="coerce").dropna()
            neg_q = int((num_s < 0).sum())
            zero_q = int((num_s == 0).sum())
            if neg_q > 0:
                negative_qty_count += neg_q
                invalid_values_count += neg_q
                issues_list.append({
                    "category": "Negative Quantities",
                    "severity": "error",
                    "description": f"Found {neg_q} row(s) with negative quantity in '{col}'.",
                    "count": neg_q,
                    "columns": [str(col)],
                })
            if zero_q > 0:
                zero_qty_count += zero_q
                issues_list.append({
                    "category": "Zero Quantities",
                    "severity": "warning",
                    "description": f"Found {zero_q} row(s) with zero quantity in '{col}'.",
                    "count": zero_q,
                    "columns": [str(col)],
                })

        # Look for price/amount columns
        price_cols = [c for c in df.columns if re.search(r"^price$|unit_price|cost|rate", str(c), re.IGNORECASE)]
        negative_price_count = 0
        zero_price_count = 0
        for col in price_cols:
            num_s = pd.to_numeric(df[col], errors="coerce").dropna()
            neg_p = int((num_s < 0).sum())
            zero_p = int((num_s == 0).sum())
            if neg_p > 0:
                negative_price_count += neg_p
                invalid_values_count += neg_p
                issues_list.append({
                    "category": "Negative Prices",
                    "severity": "error",
                    "description": f"Found {neg_p} row(s) with negative price in '{col}'.",
                    "count": neg_p,
                    "columns": [str(col)],
                })
            if zero_p > 0:
                zero_price_count += zero_p
                issues_list.append({
                    "category": "Zero Prices",
                    "severity": "warning",
                    "description": f"Found {zero_p} row(s) with zero price in '{col}'.",
                    "count": zero_p,
                    "columns": [str(col)],
                })

        # Incorrect calculated fields (price * quantity != total_amount)
        calc_cols = [c for c in df.columns if re.search(r"total|total_amount|gross|net_amount", str(c), re.IGNORECASE)]
        if price_cols and qty_cols and calc_cols:
            p_col, q_col, t_col = price_cols[0], qty_cols[0], calc_cols[0]
            try:
                p_vals = pd.to_numeric(df[p_col], errors="coerce")
                q_vals = pd.to_numeric(df[q_col], errors="coerce")
                t_vals = pd.to_numeric(df[t_col], errors="coerce")
                valid_mask = p_vals.notna() & q_vals.notna() & t_vals.notna()
                if valid_mask.sum() > 0:
                    diff = np.abs((p_vals[valid_mask] * q_vals[valid_mask]) - t_vals[valid_mask])
                    mismatch_count = int((diff > 1.0).sum())
                    if mismatch_count > 0:
                        invalid_values_count += mismatch_count
                        issues_list.append({
                            "category": "Calculation Mismatch",
                            "severity": "error",
                            "description": f"Discrepancy in {mismatch_count} row(s): {p_col} * {q_col} does not equal {t_col}.",
                            "count": mismatch_count,
                            "columns": [p_col, q_col, t_col],
                        })
            except Exception:
                pass

        # ── 6. Date Validity (Invalid dates, Future dates) ───────────────
        date_cols = [c for c in df.columns if classify_column_type(df[c]) == "date" or re.search(r"date|time", str(c), re.IGNORECASE)]
        now_dt = datetime.now()
        for d_col in date_cols:
            try:
                parsed_dates = pd.to_datetime(df[d_col], errors="coerce")
                # Check for unparseable dates
                unparseable_count = int(df[d_col].notna().sum() - parsed_dates.notna().sum())
                if unparseable_count > 0:
                    invalid_values_count += unparseable_count
                    issues_list.append({
                        "category": "Invalid Date Formats",
                        "severity": "error",
                        "description": f"{unparseable_count} value(s) in '{d_col}' could not be parsed into a valid calendar date.",
                        "count": unparseable_count,
                        "columns": [str(d_col)],
                    })
                # Check for future dates (e.g. beyond current year + 1)
                future_dates_count = int((parsed_dates > (now_dt + pd.Timedelta(days=365))).sum())
                if future_dates_count > 0:
                    invalid_values_count += future_dates_count
                    issues_list.append({
                        "category": "Future Dates",
                        "severity": "warning",
                        "description": f"{future_dates_count} date(s) in '{d_col}' are set far in the future.",
                        "count": future_dates_count,
                        "columns": [str(d_col)],
                    })
            except Exception:
                pass

        # ── 7. Numerical Outliers (IQR) ──────────────────────────────────
        outlier_total = 0
        for col in df.columns:
            if classify_column_type(df[col]) == "numerical":
                try:
                    res = OutlierDetectorService.detect(df[col], method="iqr", multiplier=2.5)
                    if res["outlier_count"] > 0:
                        outlier_total += res["outlier_count"]
                except Exception:
                    pass

        if outlier_total > 0:
            issues_list.append({
                "category": "Statistical Outliers",
                "severity": "warning",
                "description": f"{outlier_total} extreme statistical outlier value(s) detected (>2.5x IQR).",
                "count": outlier_total,
                "columns": [],
            })

        # ── Calculate Consistency Score ──────────────────────────────────
        total_inconsistent = inconsistent_cat_count + whitespace_issues_count
        if total_cells == 0:
            consistency = 0.0
            consistency_detail = "Empty dataset (0 records)"
        else:
            consistency = 1.0 - (total_inconsistent / total_cells)
            consistency = max(0.0, consistency)
            consistency_detail = f"{total_inconsistent} consistency issue(s) detected"

        # ── Calculate Validity Score ─────────────────────────────────────
        if total_cells == 0:
            validity = 0.0
            validity_detail = "Empty dataset (0 records)"
        else:
            validity = 1.0 - (invalid_values_count / total_cells)
            validity = max(0.0, validity)
            validity_detail = f"{invalid_values_count} invalid value(s) detected"

        # ── Overall Score ────────────────────────────────────────────────
        if total_cells == 0:
            overall = 0.0
        else:
            overall = (
                cls.WEIGHTS["completeness"] * completeness
                + cls.WEIGHTS["consistency"] * consistency
                + cls.WEIGHTS["validity"] * validity
                + cls.WEIGHTS["uniqueness"] * uniqueness
            )
            overall = round(max(0.0, min(1.0, overall)), 4)

        sub_scores = [
            {
                "name": "completeness",
                "score": round(completeness, 4),
                "weight": cls.WEIGHTS["completeness"],
                "detail": completeness_detail,
            },
            {
                "name": "consistency",
                "score": round(consistency, 4),
                "weight": cls.WEIGHTS["consistency"],
                "detail": consistency_detail,
            },
            {
                "name": "validity",
                "score": round(validity, 4),
                "weight": cls.WEIGHTS["validity"],
                "detail": validity_detail,
            },
            {
                "name": "uniqueness",
                "score": round(uniqueness, 4),
                "weight": cls.WEIGHTS["uniqueness"],
                "detail": uniqueness_detail,
            },
        ]

        # ── Data Quality Summary Construction ────────────────────────────
        total_cleaning_issues = len(issues_list)
        has_errors = any(i["severity"] == "error" for i in issues_list)
        has_warnings = any(i["severity"] == "warning" for i in issues_list)
        overall_status = "error" if has_errors else ("warning" if has_warnings else "clean")

        metrics_items = [
            {
                "name": "Total Rows",
                "count": row_count,
                "status": "clean",
                "detail": f"{row_count} total records",
            },
            {
                "name": "Total Columns",
                "count": col_count,
                "status": "clean",
                "detail": f"{col_count} columns profiled",
            },
            {
                "name": "Missing Values",
                "count": missing_cells,
                "status": "clean" if missing_cells == 0 else ("warning" if missing_cells < 15 else "error"),
                "detail": f"{missing_cells} missing cell(s)",
            },
            {
                "name": "Duplicate Rows",
                "count": dup_count,
                "status": "clean" if dup_count == 0 else "warning",
                "detail": f"{dup_count} exact duplicate row(s)",
            },
            {
                "name": "Duplicate Order IDs",
                "count": dup_order_ids_count,
                "status": "clean" if dup_order_ids_count == 0 else ("error" if conflicting_ids_count > 0 else "warning"),
                "detail": f"{dup_order_ids_count} repeated Order ID(s)",
            },
            {
                "name": "Order ID Conflicts",
                "count": conflicting_ids_count,
                "status": "clean" if conflicting_ids_count == 0 else "error",
                "detail": f"{conflicting_ids_count} conflict(s) across different transactions",
            },
            {
                "name": "Invalid Values",
                "count": invalid_values_count,
                "status": "clean" if invalid_values_count == 0 else "error",
                "detail": f"{invalid_values_count} invalid or contradictory value(s)",
            },
            {
                "name": "Cleaning Issues",
                "count": total_cleaning_issues,
                "status": "clean" if total_cleaning_issues == 0 else ("warning" if total_cleaning_issues < 5 else "error"),
                "detail": f"{total_cleaning_issues} quality dimension issue(s) identified",
            },
        ]

        summary = {
            "overall_score": overall,
            "overall_quality_score": overall,
            "total_rows": row_count,
            "total_columns": col_count,
            "missing_values": missing_cells,
            "duplicate_rows": dup_count,
            "duplicate_order_ids": dup_order_ids_count,
            "order_id_conflicts": conflicting_ids_count,
            "invalid_values": invalid_values_count,
            "cleaning_issues": total_cleaning_issues,
            "overall_status": overall_status,
            "metrics": metrics_items,
            "issues": issues_list,
        }

        return {
            "overall_score": overall,
            "sub_scores": sub_scores,
            "summary": summary,
            "order_id_analysis": order_analysis,
        }
