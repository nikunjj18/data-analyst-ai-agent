import pandas as pd
from app.data_profiler import profile_dataset
from app.domain_inference import infer_domain_and_metrics
from app.kpi_engine import build_kpis
from app.anomaly_detector import detect_all_anomalies
from app.viz_selector import ai_select_visualizations
from app.dashboard_insights import execute_widget


def validate_widgets(executed: list) -> list:
    seen_signatures = set()
    final = []
    for w in executed:
        if w is None:
            continue
        signature = (w.get("type"), w.get("metric_column"), w.get("group_by"), w.get("x_column"))
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        final.append(w)
    return final[:8]


def build_fallback_widgets(df: pd.DataFrame, profile: dict) -> list:
    widgets = []
    wid = 1

    for col in profile.get("numeric_columns", [])[:3]:
        stats = next((c.get("stats") for c in profile["columns"] if c["name"] == col), None)
        if not stats or stats.get("count", 0) == 0:
            continue
        widgets.append({
            "id": f"fb{wid}", "type": "kpi", "title": f"Total {col.replace('_', ' ').title()}",
            "size": "small", "value": round(stats["mean"] * stats["count"], 2),
        })
        wid += 1

    for col in profile.get("categorical_columns", [])[:3]:
        stats = next((c.get("stats") for c in profile["columns"] if c["name"] == col), None)
        if not stats or stats.get("count", 0) == 0:
            continue
        top_values = stats.get("top_values", [])
        if not top_values:
            continue
        total = sum(v["count"] for v in top_values)
        widgets.append({
            "id": f"fb{wid}", "type": "bar" if not stats.get("is_low_cardinality") else "pie",
            "title": f"Distribution by {col.replace('_', ' ').title()}",
            "size": "medium", "group_by": col,
            "data": [{"name": v["value"], "value": v["count"], "pct": round(v["count"] / total * 100, 1) if total else 0} for v in top_values],
        })
        wid += 1

    if not widgets:
        widgets.append({
            "id": "fb0", "type": "kpi", "title": "Total Records",
            "size": "small", "value": profile.get("row_count", len(df)),
        })

    return widgets


def _safe_profile(df: pd.DataFrame) -> dict:
    try:
        return profile_dataset(df)
    except Exception:
        return {
            "row_count": len(df), "column_count": len(df.columns), "columns": [],
            "numeric_columns": [], "categorical_columns": [], "date_columns": [], "id_columns": [],
            "duplicate_row_count": 0,
        }


def _safe_domain(profile: dict) -> dict:
    try:
        return infer_domain_and_metrics(profile)
    except Exception:
        return {
            "domain": "generic", "domain_reasoning": "", "primary_metric": None,
            "secondary_metrics": [], "key_dimensions": [], "dashboard_title": "Dataset Overview",
        }


def compute_full_dashboard(df: pd.DataFrame) -> dict:
    """
    Full grounded pipeline, hardened so no single failure can produce an empty dashboard.
    Every stage is wrapped so a failure degrades gracefully instead of crashing the whole thing.
    """
    if df is None or df.empty:
        return {
            "dashboard_title": "Dataset Overview", "domain": "generic", "domain_reasoning": "",
            "kpis": [{"label": "Total Records", "value": 0, "formatted_value": "0", "comparison": None}],
            "anomalies": [], "widgets": [], "multi_table": False, "error": "Table is empty.",
        }

    profile = _safe_profile(df)
    domain_plan = _safe_domain(profile)

    try:
        kpis = build_kpis(df, profile, domain_plan)
    except Exception:
        kpis = []

    try:
        anomalies = detect_all_anomalies(df, profile, domain_plan)
    except Exception:
        anomalies = []

    executed_widgets = []
    try:
        viz_plan = ai_select_visualizations(profile, domain_plan, anomalies)
        for widget in viz_plan.get("widgets", []):
            result = execute_widget(df, widget)
            if result is not None:
                executed_widgets.append({**widget, **result})
    except Exception:
        executed_widgets = []

    validated_widgets = validate_widgets(executed_widgets)

    used_fallback = False
    if not validated_widgets:
        try:
            validated_widgets = build_fallback_widgets(df, profile)
        except Exception:
            validated_widgets = [{
                "id": "fb_last_resort", "type": "kpi", "title": "Total Records",
                "size": "small", "value": len(df),
            }]
        used_fallback = True

    if not kpis:
        kpis = [{
            "label": "Total Records", "value": profile.get("row_count", len(df)),
            "formatted_value": f"{profile.get('row_count', len(df)):,}", "comparison": None,
        }]

    return {
        "dashboard_title": domain_plan.get("dashboard_title", "Dataset Overview"),
        "domain": domain_plan.get("domain"),
        "domain_reasoning": domain_plan.get("domain_reasoning", "") if not used_fallback else "",
        "kpis": kpis,
        "anomalies": anomalies,
        "widgets": validated_widgets,
        "multi_table": False,
    }