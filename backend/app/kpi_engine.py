import pandas as pd
from app.date_utils import smart_to_datetime


def format_number(value: float) -> str:
    if value is None:
        return "N/A"
    abs_val = abs(value)
    if abs_val >= 1_000_000:
        return f"{value/1_000_000:.2f}M"
    if abs_val >= 1_000:
        return f"{value/1_000:.1f}K"
    if abs_val == int(abs_val):
        return f"{int(value):,}"
    return f"{value:,.2f}"


def _aggregate_value(series: pd.Series, agg: str):
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return 0.0
    if agg == "sum":
        return float(clean.sum())
    if agg == "mean":
        return float(clean.mean())
    if agg == "count":
        return float(clean.count())
    if agg == "max":
        return float(clean.max())
    if agg == "min":
        return float(clean.min())
    return float(clean.sum())


def _default_label(col: str, agg: str) -> str:
    pretty = col.replace("_", " ").title()
    prefix = {"sum": "Total", "mean": "Average", "count": "Count of", "max": "Max", "min": "Min"}.get(agg, "Total")
    return f"{prefix} {pretty}"


def compute_period_comparison(df: pd.DataFrame, date_col: str, metric_col: str, agg: str = "sum"):
    temp = df.copy()
    temp["_date"] = smart_to_datetime(temp[date_col])
    temp = temp.dropna(subset=["_date", metric_col])
    if temp.empty:
        return None

    temp["_period"] = temp["_date"].dt.to_period("M")
    periods = sorted(temp["_period"].unique())

    if len(periods) < 2:
        return None

    current_period, previous_period = periods[-1], periods[-2]
    current_data = temp[temp["_period"] == current_period][metric_col]
    previous_data = temp[temp["_period"] == previous_period][metric_col]

    if previous_data.empty or current_data.empty:
        return None

    current_val = _aggregate_value(current_data, agg)
    previous_val = _aggregate_value(previous_data, agg)

    if previous_val == 0:
        return None

    pct_change = round((current_val - previous_val) / abs(previous_val) * 100, 1)
    return {
        "current_value": round(current_val, 2), "previous_value": round(previous_val, 2),
        "pct_change": pct_change, "direction": "up" if pct_change > 0 else ("down" if pct_change < 0 else "flat"),
        "current_period": str(current_period), "previous_period": str(previous_period),
    }


def build_kpis(df: pd.DataFrame, profile: dict, domain_plan: dict) -> list:
    kpis = []
    date_col = profile["date_columns"][0] if profile["date_columns"] else None

    metrics_to_show = []
    primary = domain_plan.get("primary_metric")
    if primary:
        agg = domain_plan.get("primary_metric_agg", "sum")
        label = domain_plan.get("primary_metric_label") or _default_label(primary, agg)
        metrics_to_show.append((primary, agg, label))

    for m in domain_plan.get("secondary_metrics", [])[:2]:
        if isinstance(m, dict):
            col, agg, label = m.get("column"), m.get("agg", "sum"), m.get("label")
        else:
            col, agg, label = m, "sum", None
        if not col:
            continue
        label = label or _default_label(col, agg)
        metrics_to_show.append((col, agg, label))

    for col, agg, label in metrics_to_show:
        if col not in df.columns:
            continue
        value = _aggregate_value(df[col], agg)
        kpi = {"label": label, "value": value, "formatted_value": format_number(value), "comparison": None}
        if date_col:
            comparison = compute_period_comparison(df, date_col, col, agg)
            if comparison:
                kpi["comparison"] = comparison
        kpis.append(kpi)

    kpis.insert(0, {
        "label": "Total Records", "value": profile["row_count"],
        "formatted_value": format_number(profile["row_count"]), "comparison": None,
    })

    return kpis[:4]