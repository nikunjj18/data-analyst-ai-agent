import pandas as pd
from google import genai
from app.config import config

client = genai.Client(api_key=config.GEMINI_API_KEY)


def load_data(csv_path: str) -> pd.DataFrame:
    return pd.read_csv(csv_path)


def build_prompt(question: str, df: pd.DataFrame) -> str:
    columns_info = "\n".join([f"- {col} ({df[col].dtype})" for col in df.columns])
    sample_rows = df.head(3).to_string()

    prompt = f"""You are a data analyst. You have a Pandas DataFrame called `df` with these columns:

{columns_info}

Here are a few sample rows:
{sample_rows}

Write Python Pandas code to answer this question:
"{question}"

Rules:
- Only use the variable name `df` to refer to the dataframe.
- Store the final answer in a variable called `result`.
- Return ONLY executable Python code, no explanations, no markdown formatting, no ```python fences.
"""
    return prompt


def generate_code(question: str, df: pd.DataFrame) -> str:
    prompt = build_prompt(question, df)
    response = client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=prompt
    )
    code = response.text.strip()
    # Safety: strip markdown fences if the model adds them anyway
    code = code.replace("```python", "").replace("```", "").strip()
    return code