import pandas as pd
import numpy as np
from app.date_utils import smart_to_datetime

VALID_TYPES = {"kpi", "line", "bar", "pie", "table", "correlation", "histogram", "scatter"}
VALID_AGGS = {"sum", "mean", "count", "max", "min"}


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
            temp["_x"] = smart_to_datetime(temp[x_col])
            temp = temp.dropna(subset=["_x"])
            if temp.empty:
                return None
            span_days = (temp["_x"].max() - temp["_x"].min()).days
            freq = "Y" if span_days > 900 else "M"
            temp["_period"] = temp["_x"].dt.to_period(freq).astype(str)
            grouped = temp.groupby("_period")[metric].agg(agg if agg != "count" else "count").reset_index()
            grouped.columns = ["period", "value"]
            grouped = grouped.sort_values("period")
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