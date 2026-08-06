import pandas as pd
from google import genai
from app.config import config
from app.api_utils import call_with_retry
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
    response = call_with_retry(lambda: client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=prompt
    ))
    code = response.text.strip()
    code = code.replace("```python", "").replace("```", "").strip()
    return code
def generate_code_with_retry(question: str, df: pd.DataFrame, quality_report=None, max_attempts: int = 3):
    """
    Generates code, executes it, and if it fails, feeds the error back to
    the model to self-correct. Retries up to max_attempts times.
    Returns (result, final_code, attempt_history).
    """
    from app.executor import safe_execute, ExecutionError

    prompt = build_prompt(question, df, quality_report)
    attempt_history = []

    for attempt in range(1, max_attempts + 1):
        response = call_with_retry(lambda: client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=prompt
    ))
        code = response.text.strip().replace("```python", "").replace("```", "").strip()

        try:
            result = safe_execute(code, df)
            attempt_history.append({"attempt": attempt, "code": code, "status": "success"})
            return result, code, attempt_history
        except ExecutionError as e:
            attempt_history.append({"attempt": attempt, "code": code, "status": "failed", "error": str(e)})

            if attempt == max_attempts:
                raise ExecutionError(
                    f"Failed after {max_attempts} attempts. Last error: {e}"
                )

            # Feed the error back so the model can fix itself
            prompt = f"""{prompt}

Your previous attempt produced this code:
{code}

It failed with this error:
{e}

Fix the code so it runs correctly. Return ONLY the corrected executable Python code, no explanations, no markdown fences.
"""

    raise ExecutionError("Unexpected: retry loop exited without result.")