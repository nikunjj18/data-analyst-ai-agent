import json
from google import genai
from app.config import config
from app.api_utils import call_with_retry

client = genai.Client(api_key=config.GEMINI_API_KEY)

VALID_TYPES = {"line", "bar", "pie", "table", "correlation", "histogram", "scatter"}


def ai_select_visualizations(profile: dict, domain_plan: dict, anomalies: list) -> dict:
    """
    Selects visualizations grounded in REAL facts: the computed profile, the inferred
    domain/metrics, and any detected anomalies — not guessing from raw sample rows.
    """
    numeric_cols = profile["numeric_columns"]
    categorical_cols = profile["categorical_columns"]
    date_cols = profile["date_columns"]

    anomaly_text = "\n".join([a["message"] for a in anomalies]) if anomalies else "None detected."

    prompt = f"""You are a senior BI dashboard designer. Design visualizations for this dataset,
using ONLY the facts below, don't guess beyond them.

Domain: {domain_plan['domain']} — {domain_plan.get('domain_reasoning', '')}
Primary metric: {domain_plan.get('primary_metric')}
Secondary metrics: {domain_plan.get('secondary_metrics')}
Key dimensions: {domain_plan.get('key_dimensions')}

Available numeric columns: {numeric_cols}
Available categorical columns: {categorical_cols}
Available date columns: {date_cols}

Detected anomalies (real, computed — reference these if relevant):
{anomaly_text}

Design 4 to 8 visualizations (quality over quantity — every chart must answer a real question).
Available types: "line" (trend over time), "bar" (category comparison), "pie" (composition,
only for dimensions with <=8 unique values), "table" (ranked list), "correlation" (numeric
relationships, only if 3+ numeric columns), "histogram" (distribution shape), "scatter"
(relationship between two numeric columns).

Rules:
- Only reference columns from the lists above.
- Don't repeat the same type more than twice unless genuinely justified.
- If an anomaly references a specific dimension/metric, prioritize a chart that surfaces it.
- Each widget needs: id, type, title (specific, not generic), size ("small"/"medium"/"large"),
  and the right fields: metric_column + aggregation (sum/mean/count/max/min) for line/bar/table/histogram,
  group_by for bar/pie/table, x_column for line/scatter.
- Ask yourself: "what question does this chart answer?" — skip it if unclear.

Return ONLY valid JSON:
{{
  "widgets": [ {{"id": "w1", "type": "...", "title": "...", "size": "...", ...fields}} ]
}}
"""
    response = call_with_retry(lambda: client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=prompt,
        config={"temperature": 0.9}
    ))
    text = response.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        plan = json.loads(text)
        plan["widgets"] = [w for w in plan.get("widgets", []) if w.get("type") in VALID_TYPES]
        return plan
    except Exception:
        return {"widgets": []}