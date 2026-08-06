import pandas as pd
from google import genai
from app.config import config

client = genai.Client(api_key=config.GEMINI_API_KEY)


def load_data(csv_path: str) -> pd.DataFrame:
    return pd.read_csv(csv_path)


def build_prompt(question: str, df: pd.DataFrame, quality_report=None) -> str:
    columns_info = "\n".join([f"- {col} ({df[col].dtype})" for col in df.columns])
    sample_rows = df.head(3).to_string()
    quality_text = quality_report.to_prompt_text() if quality_report else "Not checked."

    prompt = f"""You are a data analyst. You have a Pandas DataFrame called `df` with these columns:

{columns_info}

Data quality issues found in this dataset:
{quality_text}

Sample rows:
{sample_rows}

Write Python Pandas code to answer this question:
"{question}"

Rules:
- Only use the variable name `df`.
-`pd` (pandas) is already available — never write `import pandas` or any import statement.
- Handle missing values (NaN) defensively — use .dropna() on relevant columns before aggregating.
- Never assume a column is 100% clean, even if it looks numeric.
- Store the final answer in a variable called `result`.
- Return ONLY executable Python code, no explanations, no markdown fences.
"""
    return prompt


def generate_code(question: str, df: pd.DataFrame, quality_report=None) -> str:
    prompt = build_prompt(question, df, quality_report)
    response = client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=prompt
    )
    code = response.text.strip()
    code = code.replace("```python", "").replace("```", "").strip()
    return code