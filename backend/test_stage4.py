import pandas as pd
from app.dashboard_engine import compute_full_dashboard
import json

df = pd.read_csv("../data/sample_sales.csv")
result = compute_full_dashboard(df)
print(json.dumps(result, indent=2, default=str))