import pandas as pd
import numpy as np


def detect_time_series_anomalies(df: pd.DataFrame, date_col: str, metric_col: str, agg: str = "sum") -> list:
    """
    Detects sudden spikes/drops in a metric over time using z-score on period-over-period
    changes. Only flags genuinely unusual points, not normal fluctuation.
    """
    temp = df.copy()
    temp["_date"] = pd.to_datetime(temp[date_col], errors="coerce")
    temp = temp.dropna(subset=["_date", metric_col])
    if temp.empty:
        return []

    temp["_period"] = temp["_date"].dt.to_period("M").astype(str)
    series = temp.groupby("_period")[metric_col].agg(agg)

    if len(series) < 4:
        return []  # not enough history to judge what's "unusual"

    pct_changes = series.pct_change().dropna()
    if pct_changes.std() == 0 or pct_changes.empty:
        return []

    z_scores = (pct_changes - pct_changes.mean()) / pct_changes.std()
    anomalies = []

    for period, z in z_scores.items():
        if abs(z) >= 2:  # genuinely unusual, not normal noise
            change_pct = round(pct_changes[period] * 100, 1)
            direction = "spike" if change_pct > 0 else "drop"
            anomalies.append({
                "type": "time_series",
                "period": period,
                "metric": metric_col,
                "change_pct": change_pct,
                "direction": direction,
                "message": f"{metric_col.replace('_', ' ').title()} had a {'sudden increase' if direction == 'spike' else 'sudden drop'} of {abs(change_pct)}% in {period}.",
            })

    return anomalies


def detect_category_outliers(df: pd.DataFrame, group_col: str, metric_col: str, agg: str = "sum") -> list:
    """Detects categories that are statistical outliers relative to their peers."""
    if group_col not in df.columns or metric_col not in df.columns:
        return []

    grouped = df.groupby(group_col)[metric_col].agg(agg)
    if len(grouped) < 4:
        return []

    q1, q3 = grouped.quantile(0.25), grouped.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return []

    lower_bound, upper_bound = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    anomalies = []

    for category, value in grouped.items():
        if value < lower_bound or value > upper_bound:
            direction = "unusually high" if value > upper_bound else "unusually low"
            anomalies.append({
                "type": "category_outlier",
                "category": str(category),
                "dimension": group_col,
                "metric": metric_col,
                "value": round(float(value), 2),
                "direction": direction,
                "message": f"{category} shows {direction} {metric_col.replace('_', ' ')} ({round(float(value), 2):,.0f}) compared to other {group_col.replace('_', ' ')} values.",
            })

    return anomalies


def detect_all_anomalies(df: pd.DataFrame, profile: dict, domain_plan: dict, max_anomalies: int = 4) -> list:
    """Runs all anomaly checks and returns the most significant ones, capped to avoid noise."""
    anomalies = []
    date_col = profile["date_columns"][0] if profile["date_columns"] else None
    primary_metric = domain_plan.get("primary_metric")

    if date_col and primary_metric:
        anomalies.extend(detect_time_series_anomalies(df, date_col, primary_metric))

    for dim in domain_plan.get("key_dimensions", [])[:2]:
        if primary_metric:
            anomalies.extend(detect_category_outliers(df, dim, primary_metric))

    # Sort by magnitude of change/deviation, most significant first
    def magnitude(a):
        if a["type"] == "time_series":
            return abs(a["change_pct"])
        return 1  # category outliers already filtered to genuine outliers

    anomalies.sort(key=magnitude, reverse=True)
    return anomalies[:max_anomalies]