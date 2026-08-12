import pandas as pd


def compute_dataset_summary(df: pd.DataFrame) -> dict:
    """Computes quick, LLM-free stats for the Dashboard tab visualizations."""
    summary = {"columns": []}

    for col in df.columns:
        col_info = {"name": col, "dtype": str(df[col].dtype)}

        if pd.api.types.is_numeric_dtype(df[col]):
            col_info["type"] = "numeric"
            col_info["min"] = float(df[col].min()) if df[col].notna().any() else None
            col_info["max"] = float(df[col].max()) if df[col].notna().any() else None
            col_info["mean"] = round(float(df[col].mean()), 2) if df[col].notna().any() else None
            col_info["null_count"] = int(df[col].isnull().sum())
        else:
            col_info["type"] = "categorical"
            value_counts = df[col].value_counts().head(6)
            col_info["top_values"] = [{"label": str(k), "count": int(v)} for k, v in value_counts.items()]
            col_info["unique_count"] = int(df[col].nunique())
            col_info["null_count"] = int(df[col].isnull().sum())

        summary["columns"].append(col_info)

    summary["total_rows"] = len(df)
    summary["total_columns"] = len(df.columns)
    return summary