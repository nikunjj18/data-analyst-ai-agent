import json
from google import genai
from app.config import config
from app.api_utils import call_with_retry

client = genai.Client(api_key=config.GEMINI_API_KEY)


def infer_domain_and_metrics(profile: dict) -> dict:
    """
    Given the REAL computed profile, asks the AI to infer the business domain,
    select key metrics, AND decide the correct aggregation for each metric based
    on what it semantically represents (e.g. revenue -> sum, price/rating/age -> average,
    a rate/percentage column -> average, a count of transactions -> sum or count).
    """
    numeric_summary = "\n".join([
        f"- {c['name']}: mean={c['stats']['mean']}, min={c['stats']['min']}, max={c['stats']['max']}, "
        f"skew={c['stats']['skew']}, is_likely_percentage={c['stats'].get('is_likely_percentage')}, "
        f"is_likely_rate_0_100={c['stats'].get('is_likely_rate_0_100')}"
        for c in profile["columns"] if c["role"] == "numeric"
    ])
    categorical_summary = "\n".join([
        f"- {c['name']}: {c['stats']['unique_count']} unique values, top='{c['stats']['top_values'][0]['value']}' ({c['stats']['dominant_share_pct']}%)"
        for c in profile["columns"] if c["role"] == "categorical"
    ])
    date_summary = ", ".join(profile["date_columns"]) if profile["date_columns"] else "none"

    prompt = f"""You are a senior data analyst. Based on ACTUAL computed statistics about this dataset,
infer its business domain and identify the key metrics — AND decide the semantically correct
aggregation for each metric.

Dataset: {profile['row_count']} rows, {profile['column_count']} columns

Numeric columns (with real stats):
{numeric_summary}

Categorical columns (with real stats):
{categorical_summary}

Date columns: {date_summary}

Infer the business domain (sales, HR, marketing, finance, customer/support, operations, generic).

For each metric you select, decide the CORRECT aggregation based on what the column means:
- "sum" for additive quantities: revenue, sales, quantity, cost, spend, count of items, total X
- "mean" for rates, prices, scores, ratings, ages, percentages, durations, or anything where
  adding across rows would be meaningless (e.g. averaging unit_price, discount_pct, satisfaction_score, age)
- "count" for counting occurrences/records rather than summing a value
- "max" or "min" only if the column represents a ceiling/floor that's more meaningful than sum/mean

A column being "likely a percentage" or "likely a rate 0-100" is a strong signal it should use "mean", never "sum".

Select the single most important primary metric, and up to 2 secondary metrics. Select up to 3
categorical columns as the most meaningful dimensions (prefer low-cardinality, business-meaningful
columns over IDs or noise).

Return ONLY valid JSON:
{{
  "domain": "sales",
  "domain_reasoning": "one sentence",
  "primary_metric": "<column name or null>",
  "primary_metric_agg": "<sum|mean|count|max|min>",
  "primary_metric_label": "<e.g. 'Total Revenue' or 'Average Rating' — matches the aggregation, not always 'Total'>",
  "secondary_metrics": [
    {{"column": "<name>", "agg": "<sum|mean|count|max|min>", "label": "<matching label>"}}
  ],
  "key_dimensions": ["<column name>", ...],
  "dashboard_title": "<specific, professional title for this dashboard>"
}}
"""
    response = call_with_retry(lambda: client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=prompt
    ))
    text = response.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(text)
        # Basic safety defaults if the model omits fields
        result.setdefault("primary_metric_agg", "sum")
        result.setdefault("primary_metric_label", None)
        result.setdefault("secondary_metrics", [])
        return result
    except Exception:
        fallback_metric = profile["numeric_columns"][0] if profile["numeric_columns"] else None
        return {
            "domain": "generic", "domain_reasoning": "",
            "primary_metric": fallback_metric, "primary_metric_agg": "sum", "primary_metric_label": None,
            "secondary_metrics": [], "key_dimensions": profile["categorical_columns"][:2],
            "dashboard_title": "Dataset Overview",
        }