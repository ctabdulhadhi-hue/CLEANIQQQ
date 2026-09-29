"""
Centralized missing value detection and safe imputation service for CleanIQ.
Ensures correct identification of null, NaN, pd.NA, pd.NaT, empty strings,
whitespace-only strings, and configurable null markers.
Prevents misclassifying legitimate 0, False, or text strings (like 'NA') as missing.
"""

import math
from typing import Any, List, Optional, Tuple
import numpy as np
import pandas as pd

from app.core.errors import AppError


class MissingValueService:
    @staticmethod
    def is_val_missing(val: Any, custom_markers: Optional[List[str]] = None) -> bool:
        """
        Returns True if a single scalar value is considered missing.
        Legitimate values like 0, 0.0, False are NEVER missing.
        'NA' is NOT missing unless explicitly present in custom_markers.
        """
        if val is None:
            return True
        if isinstance(val, (bool, np.bool_)):
            return False
        if isinstance(val, (int, float, np.number)):
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                return True
            return False
        if pd.isna(val) or val is pd.NaT:
            return True
        if isinstance(val, str):
            trimmed = val.strip()
            if trimmed == "":
                return True
            if custom_markers and trimmed in custom_markers:
                return True
            return False
        return False

    @classmethod
    def get_missing_mask(
        cls,
        series: pd.Series,
        custom_markers: Optional[List[str]] = None,
    ) -> pd.Series:
        """
        Returns a boolean Series of identical length where True indicates a missing cell.
        """
        if len(series) == 0:
            return pd.Series(dtype=bool)

        # For purely boolean types, standard pd.isna is safe and fast
        if pd.api.types.is_bool_dtype(series):
            return series.isna()

        if pd.api.types.is_numeric_dtype(series):
            # Check for NaN and Inf
            mask = series.isna()
            if pd.api.types.is_float_dtype(series):
                mask = mask | np.isinf(series)
            return mask

        # For object, string, category, or mixed columns
        def check_val(v):
            return cls.is_val_missing(v, custom_markers)

        try:
            return series.map(check_val).astype(bool)
        except Exception:
            return series.apply(check_val).astype(bool)

    @classmethod
    def count_missing(
        cls,
        series: pd.Series,
        custom_markers: Optional[List[str]] = None,
    ) -> int:
        """Returns total count of missing cells in a series."""
        if len(series) == 0:
            return 0
        return int(cls.get_missing_mask(series, custom_markers).sum())

    @classmethod
    def safe_impute(
        cls,
        series: pd.Series,
        col_name: str,
        strategy: str,
        value: Optional[Any] = None,
        custom_markers: Optional[List[str]] = None,
    ) -> Tuple[pd.Series, int, int, Any]:
        """
        Safely imputes missing values in a pandas Series.
        Returns: (imputed_series, imputed_count, remaining_missing_count, fill_value_used)
        """
        mask = cls.get_missing_mask(series, custom_markers)
        orig_missing = int(mask.sum())
        if orig_missing == 0:
            return series.copy(), 0, 0, None

        result = series.copy()
        non_missing = result[~mask]
        fill_val = None

        if strategy == "mean":
            if not pd.api.types.is_numeric_dtype(series):
                raise AppError(
                    code="INVALID_METHOD",
                    message=f"Cannot use 'mean' on non-numeric column '{col_name}' (dtype: {series.dtype})",
                    status_code=400,
                )
            if len(non_missing) == 0:
                raise AppError(
                    code="NO_VALID_VALUES",
                    message=f"Cannot compute mean for column '{col_name}': all values are missing.",
                    status_code=400,
                )
            fill_val = float(pd.to_numeric(non_missing, errors="coerce").mean())
            if math.isnan(fill_val):
                raise AppError(
                    code="NO_VALID_VALUES",
                    message=f"Cannot compute mean for column '{col_name}': no valid numbers.",
                    status_code=400,
                )
            result.loc[mask] = fill_val

        elif strategy == "median":
            if not pd.api.types.is_numeric_dtype(series):
                raise AppError(
                    code="INVALID_METHOD",
                    message=f"Cannot use 'median' on non-numeric column '{col_name}' (dtype: {series.dtype})",
                    status_code=400,
                )
            if len(non_missing) == 0:
                raise AppError(
                    code="NO_VALID_VALUES",
                    message=f"Cannot compute median for column '{col_name}': all values are missing.",
                    status_code=400,
                )
            fill_val = float(pd.to_numeric(non_missing, errors="coerce").median())
            if math.isnan(fill_val):
                raise AppError(
                    code="NO_VALID_VALUES",
                    message=f"Cannot compute median for column '{col_name}': no valid numbers.",
                    status_code=400,
                )
            result.loc[mask] = fill_val

        elif strategy == "mode":
            if len(non_missing) == 0:
                raise AppError(
                    code="NO_VALID_VALUES",
                    message=f"Cannot compute mode for column '{col_name}': all values are missing.",
                    status_code=400,
                )
            modes = non_missing.mode()
            if len(modes) == 0:
                raise AppError(
                    code="NO_VALID_VALUES",
                    message=f"Cannot compute mode for column '{col_name}': no mode found.",
                    status_code=400,
                )
            # Deterministic tied mode resolution: sort candidates
            mode_list = modes.tolist()
            try:
                sorted_modes = sorted(mode_list)
            except TypeError:
                sorted_modes = sorted(mode_list, key=lambda x: str(x))
            fill_val = sorted_modes[0]
            result.loc[mask] = fill_val

        elif strategy in ("custom", "constant"):
            if value is None:
                raise AppError(
                    code="MISSING_VALUE",
                    message=f"Imputation strategy '{strategy}' requires a fill value.",
                    status_code=400,
                )
            fill_val = value
            # Type-compatibility checks
            if pd.api.types.is_numeric_dtype(series):
                try:
                    fill_val = float(fill_val)
                    if pd.api.types.is_integer_dtype(series) and fill_val.is_integer():
                        fill_val = int(fill_val)
                except (ValueError, TypeError):
                    raise AppError(
                        code="TYPE_MISMATCH",
                        message=f"Cannot cast fill value '{value}' to numeric for column '{col_name}'.",
                        status_code=400,
                    )
            elif pd.api.types.is_bool_dtype(series):
                if str(fill_val).lower() in ("true", "1", "yes"):
                    fill_val = True
                elif str(fill_val).lower() in ("false", "0", "no"):
                    fill_val = False
                else:
                    raise AppError(
                        code="TYPE_MISMATCH",
                        message=f"Cannot cast fill value '{value}' to boolean for column '{col_name}'.",
                        status_code=400,
                    )
            result.loc[mask] = fill_val

        elif strategy in ("ffill", "forward_fill"):
            result = result.ffill()
            fill_val = "forward-fill"

        elif strategy in ("bfill", "backward_fill"):
            result = result.bfill()
            fill_val = "backward-fill"

        elif strategy in ("none", "leave_unchanged"):
            return series.copy(), 0, orig_missing, None

        else:
            raise AppError(
                code="INVALID_METHOD",
                message=f"Unknown imputation strategy '{strategy}'. Supported: mean, median, mode, constant, custom, ffill, bfill, none",
                status_code=400,
            )

        new_mask = cls.get_missing_mask(result, custom_markers)
        remaining_missing = int(new_mask.sum())
        imputed_count = orig_missing - remaining_missing

        return result, imputed_count, remaining_missing, fill_val
