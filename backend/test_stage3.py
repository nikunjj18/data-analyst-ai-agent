# backend/test_stage3_forced.py
import pandas as pd
from app.anomaly_detector import detect_category_outliers

df = pd.read_csv("../data/sample_sales.csv")

# Force an artificial outlier: make one region's revenue absurdly high
df.loc[df["region"] == "North", "revenue"] = df.loc[df["region"] == "North", "revenue"] * 20

anomalies = detect_category_outliers(df, "region", "revenue")
import json
print(json.dumps(anomalies, indent=2))