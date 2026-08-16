import pandas as pd


def smart_to_datetime(series: pd.Series) -> pd.Series:
    """
    Correctly parses a column into dates, handling the common case of a plain
    'year' column stored as integers (e.g. 1990, 2015) — which pd.to_datetime()
    would otherwise misinterpret as nanosecond timestamps near 1970.
    """
    if pd.api.types.is_datetime64_any_dtype(series):
        return series

    numeric = pd.to_numeric(series, errors="coerce")
    non_null = numeric.dropna()

    if not non_null.empty:
        looks_like_years = ((non_null >= 1900) & (non_null <= 2100) & (non_null == non_null.astype(int))).mean() > 0.9
        if looks_like_years:
            return pd.to_datetime(numeric.astype("Int64").astype(str), format="%Y", errors="coerce")

    return pd.to_datetime(series, errors="coerce")