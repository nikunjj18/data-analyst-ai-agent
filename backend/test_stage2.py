import pandas as pd
from app.data_profiler import profile_dataset
from app.domain_inference import infer_domain_and_metrics
from app.kpi_engine import build_kpis
import json

df = pd.read_csv("../data/sample_sales.csv")
profile = profile_dataset(df)

domain_plan = infer_domain_and_metrics(profile)
print("=== DOMAIN PLAN ===")
print(json.dumps(domain_plan, indent=2))

kpis = build_kpis(df, profile, domain_plan)
print("\n=== KPIS ===")
print(json.dumps(kpis, indent=2))