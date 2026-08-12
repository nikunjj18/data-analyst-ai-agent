import pandas as pd
import numpy as np
import json
from google import genai
from app.config import config
from app.api_utils import call_with_retry

client = genai.Client(api_key=config.GEMINI_API_KEY)

VALID_TYPES = {"kpi", "line", "bar", "pie", "table", "correlation", "histogram", "scatter"}
VALID_AGGS = {"sum", "mean", "count", "max", "min"}


def ai_design_dashboard(df: pd.DataFrame) -> dict:
    """Lets the AI fully design the dashboard, pushed toward genuine variety per dataset."""
    columns_info = "\n".join([f"- {col} ({df[col].dtype}, {df[col].nunique()} unique values)" for col in df.columns])
    sample = df.head(5).to_string()
    numeric_count = len(df.select_dtypes(include="number").columns)
    cat_count = len(df.select_dtypes(exclude="number").columns)

    prompt = f"""You are a senior BI dashboard designer. Design a dashboard for THIS specific dataset.

Columns:
{columns_info}

Sample rows:
{sample}

This dataset has {numeric_count} numeric columns and {cat_count} categorical columns.

IMPORTANT: Do not default to a generic "sales dashboard" template. Actually look at what's unusual
or interesting about THIS data's shape and design around it. Two different datasets should get
genuinely different dashboards, not the same KPI+line+bar+pie combo reskinned.

Available widget types, use whichever genuinely fit, not all of them:
- "kpi": single headline number
- "line": trend over a real date/sequence column
- "bar": comparison across categories
- "pie": composition, only if a categorical column has 2-8 distinct values
- "table": ranked list, good for many categories or top-N rankings
- "correlation": heatmap of numeric relationships, only if 3+ numeric columns
- "histogram": distribution shape of a single numeric column, use when a numeric column's spread
  itself is interesting (e.g. price distribution, age distribution)
- "scatter": relationship between two numeric columns, use when two numeric columns might be related

Rules:
- Design 20 to 60 widgets, exactly as many as this dataset's actual structure supports. Sparse data gets fewer widgets, rich data gets more.
- Vary widget types meaningfully, don't repeat the same type more than twice unless the data has that many genuinely distinct groupings worth showing separately.
- For "kpi","line","bar","table": specify metric_column (numeric) and aggregation (sum/mean/count/max/min).
- For "bar","pie","table" also specify group_by.
- For "line" specify x_column and metric_column.
- For "histogram" specify metric_column only.
- For "scatter" specify x_column and metric_column (both numeric).
- For "correlation" no extra fields.
- Assign "size": "small" (kpis), "medium", or "large" (trend/scatter/correlation deserve more space).
- Only reference columns that exist in the list above.

Return ONLY valid JSON:
{{
  "widgets": [ {{"id": "w1", "type": "...", "title": "...", "size": "...", ...fields...}} ],
  "reasoning": "one sentence explaining the specific design logic for THIS dataset's shape"
}}
"""
    response = call_with_retry(lambda: client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=prompt,
        config={"temperature": 1.1}
    ))
    text = response.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        plan = json.loads(text)
        plan["widgets"] = [w for w in plan.get("widgets", []) if w.get("type") in VALID_TYPES]
        return plan
    except Exception:
        return {"widgets": [], "reasoning": "Could not generate a dashboard plan."}


def _aggregate(series: pd.Series, agg: str):
    series = pd.to_numeric(series, errors="coerce").dropna()
    if series.empty:
        return 0
    if agg == "sum":
        return float(series.sum())
    if agg == "mean":
        return float(series.mean())
    if agg == "count":
        return int(series.count())
    if agg == "max":
        return float(series.max())
    if agg == "min":
        return float(series.min())
    return float(series.sum())


def execute_widget(df: pd.DataFrame, widget: dict):
    """Executes one AI-designed widget spec against the real dataframe using safe pandas ops."""
    wtype = widget.get("type")
    agg = widget.get("aggregation", "sum") if widget.get("aggregation") in VALID_AGGS else "sum"

    try:
        if wtype == "kpi":
            col = widget.get("metric_column")
            if col not in df.columns:
                return None
            return {"value": round(_aggregate(df[col], agg), 2)}

        if wtype == "line":
            x_col, metric = widget.get("x_column"), widget.get("metric_column")
            if x_col not in df.columns or metric not in df.columns:
                return None
            temp = df.copy()
            temp["_x"] = pd.to_datetime(temp[x_col], errors="coerce")
            temp = temp.dropna(subset=["_x"])
            if temp.empty:
                return None
            temp["_period"] = temp["_x"].dt.to_period("M").astype(str)
            grouped = temp.groupby("_period")[metric].agg(agg if agg != "count" else "count").reset_index()
            grouped.columns = ["period", "value"]
            return {"data": grouped.to_dict("records")}

        if wtype in ("bar", "pie", "table"):
            group_col, metric = widget.get("group_by"), widget.get("metric_column")
            if group_col not in df.columns:
                return None
            if metric and metric in df.columns:
                grouped = df.groupby(group_col)[metric].agg(agg if agg != "count" else "count")
            else:
                grouped = df[group_col].value_counts()
            grouped = grouped.sort_values(ascending=False)
            limit = widget.get("limit", 8 if wtype != "pie" else 6)
            grouped = grouped.head(limit)
            total = grouped.sum()
            data = [
                {"name": str(k), "value": round(float(v), 2), "pct": round(float(v) / total * 100, 1) if total else 0}
                for k, v in grouped.items()
            ]
            return {"data": data}

        if wtype == "correlation":
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            if len(numeric_cols) < 2:
                return None
            corr = df[numeric_cols].corr().round(2)
            return {"columns": numeric_cols, "matrix": corr.values.tolist()}

        if wtype == "histogram":
            col = widget.get("metric_column")
            if col not in df.columns:
                return None
            values = pd.to_numeric(df[col], errors="coerce").dropna()
            if values.empty:
                return None
            counts, bin_edges = np.histogram(values, bins=10)
            data = [{"name": f"{bin_edges[i]:.0f}-{bin_edges[i+1]:.0f}", "value": int(counts[i])} for i in range(len(counts))]
            return {"data": data}

        if wtype == "scatter":
            x_col, y_col = widget.get("x_column"), widget.get("metric_column")
            if x_col not in df.columns or y_col not in df.columns:
                return None
            temp = df[[x_col, y_col]].copy()
            temp[x_col] = pd.to_numeric(temp[x_col], errors="coerce")
            temp[y_col] = pd.to_numeric(temp[y_col], errors="coerce")
            temp = temp.dropna().head(300)
            return {"data": [{"x": round(float(r[x_col]), 2), "y": round(float(r[y_col]), 2)} for _, r in temp.iterrows()]}

    except Exception:
        return None

    return None


def compute_dashboard_insights(df: pd.DataFrame) -> dict:
    plan = ai_design_dashboard(df)
    widgets_out = []

    for widget in plan.get("widgets", []):
        result = execute_widget(df, widget)
        if result is None:
            continue
        widgets_out.append({**widget, **result})

    return {"widgets": widgets_out, "reasoning": plan.get("reasoning", "")}