import pandas as pd
import numpy as np
from app.date_utils import smart_to_datetime


def _is_likely_id_column(col_name: str, series: pd.Series) -> bool:
    name_lower = col_name.lower()
    id_hints = ["id", "_id", "uuid", "key", "code"]
    name_match = any(name_lower == h or name_lower.endswith(h) for h in id_hints)

    is_float = pd.api.types.is_float_dtype(series)
    if is_float:
        return name_match

    high_cardinality = series.nunique() / max(len(series), 1) > 0.95
    return name_match or high_cardinality


def _is_likely_date_column(col_name: str, series: pd.Series) -> bool:
    name_lower = col_name.lower()
    date_hints = ["date", "time", "day", "month", "year", "created", "updated", "timestamp"]
    if any(h in name_lower for h in date_hints):
        try:
            parsed = smart_to_datetime(series.dropna().head(50))
            return parsed.notna().mean() > 0.7
        except Exception:
            return False
    return False


def profile_numeric_column(series: pd.Series) -> dict:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return {"count": 0}

    q1, q3 = clean.quantile(0.25), clean.quantile(0.75)
    iqr = q3 - q1
    outlier_mask = (clean < q1 - 1.5 * iqr) | (clean > q3 + 1.5 * iqr)

    return {
        "count": int(clean.count()),
        "min": float(clean.min()),
        "max": float(clean.max()),
        "mean": round(float(clean.mean()), 2),
        "median": float(clean.median()),
        "std": round(float(clean.std()), 2) if clean.count() > 1 else 0,
        "skew": round(float(clean.skew()), 2) if clean.count() > 2 else 0,
        "outlier_count": int(outlier_mask.sum()),
        "outlier_pct": round(float(outlier_mask.mean() * 100), 1),
        "is_mostly_zero_or_binary": bool(clean.nunique() <= 2),
        "is_likely_percentage": bool(0 <= clean.min() and clean.max() <= 1.0001),
        "is_likely_rate_0_100": bool(0 <= clean.min() and clean.max() <= 100 and clean.nunique() > 2),
    }


def profile_categorical_column(series: pd.Series) -> dict:
    clean = series.dropna().astype(str)
    if clean.empty:
        return {"count": 0}

    value_counts = clean.value_counts()
    top = value_counts.head(5)

    return {
        "count": int(clean.count()),
        "unique_count": int(clean.nunique()),
        "cardinality_ratio": round(clean.nunique() / max(len(clean), 1), 3),
        "top_values": [{"value": str(k), "count": int(v)} for k, v in top.items()],
        "dominant_share_pct": round(float(top.iloc[0] / len(clean) * 100), 1) if len(top) else 0,
        "is_low_cardinality": bool(clean.nunique() <= 12),
        "is_boolean_like": bool(clean.nunique() == 2),
    }


def profile_dataset(df: pd.DataFrame) -> dict:
    profile = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": [],
        "numeric_columns": [],
        "categorical_columns": [],
        "date_columns": [],
        "id_columns": [],
        "duplicate_row_count": int(df.duplicated().sum()),
    }

    for col in df.columns:
        series = df[col]
        null_count = int(series.isnull().sum())
        null_pct = round(null_count / max(len(df), 1) * 100, 1)

        col_entry = {"name": col, "dtype": str(series.dtype), "null_count": null_count, "null_pct": null_pct}

        is_id = _is_likely_id_column(col, series)
        is_date = _is_likely_date_column(col, series)
        is_numeric = pd.api.types.is_numeric_dtype(series) and not is_id and not is_date

        if is_date:
            col_entry["role"] = "date"
            profile["date_columns"].append(col)
        elif is_id:
            col_entry["role"] = "identifier"
            profile["id_columns"].append(col)
        elif is_numeric:
            col_entry["role"] = "numeric"
            col_entry["stats"] = profile_numeric_column(series)
            profile["numeric_columns"].append(col)
        else:
            col_entry["role"] = "categorical"
            col_entry["stats"] = profile_categorical_column(series)
            profile["categorical_columns"].append(col)

        profile["columns"].append(col_entry)

    return profile