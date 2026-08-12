import pandas as pd


def format_number(value: float) -> str:
    """Formats numbers the way a BI tool would: 1.25M, 25.4K, etc."""
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


def compute_period_comparison(df: pd.DataFrame, date_col: str, metric_col: str, agg: str = "sum"):
    """
    Splits data into the most recent complete period vs the one before it,
    and computes real percentage change. Returns None if there isn't enough
    time spread to make a comparison meaningful (avoids fake/misleading trends).
    """
    temp = df.copy()
    temp["_date"] = pd.to_datetime(temp[date_col], errors="coerce")
    temp = temp.dropna(subset=["_date", metric_col])
    if temp.empty:
        return None

    temp["_period"] = temp["_date"].dt.to_period("M")
    periods = sorted(temp["_period"].unique())

    if len(periods) < 2:
        return None  # not enough spread for a real comparison, don't fake one

    current_period, previous_period = periods[-1], periods[-2]
    current_data = temp[temp["_period"] == current_period][metric_col]
    previous_data = temp[temp["_period"] == previous_period][metric_col]

    if previous_data.empty or current_data.empty:
        return None

    current_val = getattr(current_data, agg)()
    previous_val = getattr(previous_data, agg)()

    if previous_val == 0:
        return None

    pct_change = round((current_val - previous_val) / abs(previous_val) * 100, 1)
    return {
        "current_value": round(float(current_val), 2),
        "previous_value": round(float(previous_val), 2),
        "pct_change": pct_change,
        "direction": "up" if pct_change > 0 else ("down" if pct_change < 0 else "flat"),
        "current_period": str(current_period),
        "previous_period": str(previous_period),
    }


def build_kpis(df: pd.DataFrame, profile: dict, domain_plan: dict) -> list:
    """Builds KPI cards using real aggregates, with real comparisons only when data supports them."""
    kpis = []
    date_col = profile["date_columns"][0] if profile["date_columns"] else None

    metrics_to_show = []
    if domain_plan.get("primary_metric"):
        metrics_to_show.append((domain_plan["primary_metric"], "sum", "Total"))
    for m in domain_plan.get("secondary_metrics", [])[:2]:
        metrics_to_show.append((m, "sum", "Total"))

    for col, agg, label_prefix in metrics_to_show:
        if col not in df.columns:
            continue

        total_value = float(pd.to_numeric(df[col], errors="coerce").sum())
        kpi = {
            "label": f"{label_prefix} {col.replace('_', ' ').title()}",
            "value": total_value,
            "formatted_value": format_number(total_value),
            "comparison": None,
        }

        if date_col:
            comparison = compute_period_comparison(df, date_col, col, agg)
            if comparison:
                kpi["comparison"] = comparison

        kpis.append(kpi)

    # Always include row count as a grounding KPI
    kpis.insert(0, {
        "label": "Total Records",
        "value": profile["row_count"],
        "formatted_value": format_number(profile["row_count"]),
        "comparison": None,
    })

    return kpis[:4]