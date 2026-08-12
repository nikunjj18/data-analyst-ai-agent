import json
from google import genai
from app.config import config
from app.api_utils import call_with_retry

client = genai.Client(api_key=config.GEMINI_API_KEY)


def infer_domain_and_metrics(profile: dict) -> dict:
    """
    Given the REAL computed profile (not guesses), asks the AI to infer the business
    domain and select which columns are the key metrics/dimensions — grounded reasoning,
    not blind guessing from column names alone.
    """
    numeric_summary = "\n".join([
        f"- {c['name']}: mean={c['stats']['mean']}, skew={c['stats']['skew']}, outliers={c['stats']['outlier_pct']}%"
        for c in profile["columns"] if c["role"] == "numeric"
    ])
    categorical_summary = "\n".join([
        f"- {c['name']}: {c['stats']['unique_count']} unique values, top='{c['stats']['top_values'][0]['value']}' ({c['stats']['dominant_share_pct']}%)"
        for c in profile["columns"] if c["role"] == "categorical"
    ])
    date_summary = ", ".join(profile["date_columns"]) if profile["date_columns"] else "none"

    prompt = f"""You are a senior data analyst. Based on ACTUAL computed statistics (not guesses) about
this dataset, infer its business domain and identify the key metrics.

Dataset: {profile['row_count']} rows, {profile['column_count']} columns

Numeric columns (with real stats):
{numeric_summary}

Categorical columns (with real stats):
{categorical_summary}

Date columns: {date_summary}

Infer the business domain (e.g. sales, HR, marketing, finance, customer/support, operations, generic).
Then select which numeric column is the SINGLE most important primary metric for this domain
(e.g. revenue for sales, salary for HR, spend for marketing), and up to 2 secondary metrics.
Select up to 3 categorical columns that are the most meaningful dimensions to break metrics down by
(prefer low-cardinality, business-meaningful columns over IDs or noise).

Return ONLY valid JSON:
{{
  "domain": "sales",
  "domain_reasoning": "one sentence",
  "primary_metric": "<column name or null>",
  "secondary_metrics": ["<column name>", ...],
  "key_dimensions": ["<column name>", ...],
  "dashboard_title": "<a specific, professional title for this dashboard, e.g. 'Sales Performance Overview', not generic>"
}}
"""
    response = call_with_retry(lambda: client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=prompt
    ))
    text = response.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except Exception:
        return {
            "domain": "generic", "domain_reasoning": "",
            "primary_metric": profile["numeric_columns"][0] if profile["numeric_columns"] else None,
            "secondary_metrics": [], "key_dimensions": profile["categorical_columns"][:2],
            "dashboard_title": "Dataset Overview",
        }