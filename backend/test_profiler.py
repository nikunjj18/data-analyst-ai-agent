import pandas as pd
from app.data_profiler import profile_dataset
import json

df = pd.read_csv("../data/sample_sales.csv")
profile = profile_dataset(df)
print(json.dumps(profile, indent=2, default=str))