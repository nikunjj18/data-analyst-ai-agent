import pandas as pd
from google import genai
from app.config import config
from app.api_utils import call_with_retry
from app.executor import safe_execute_with_timeout
from app.logger import log_event, log_error
from langsmith import traceable
from app.api_utils import log_token_usage_to_trace

client = genai.Client(api_key=config.GEMINI_API_KEY)



def load_data(csv_path: str) -> pd.DataFrame:
    return pd.read_csv(csv_path)


def build_prompt(question: str, df: pd.DataFrame, quality_report=None, memory=None) -> str:
    columns_info = "\n".join([f"- {col} ({df[col].dtype})" for col in df.columns])
    sample_rows = df.head(3).to_string()
    quality_text = quality_report.to_prompt_text() if quality_report else "Not checked."

    numeric_ranges = []
    for col in df.select_dtypes(include="number").columns:
        col_min, col_max = df[col].min(), df[col].max()
        numeric_ranges.append(f"- {col}: range {col_min} to {col_max}")
    ranges_text = "\n".join(numeric_ranges) if numeric_ranges else "No numeric columns."

    memory_text = memory.to_prompt_text() if memory else "No previous questions in this conversation."

    prompt = f"""You are a data analyst. You have a Pandas DataFrame called `df` with these columns:

{columns_info}

Numeric column value ranges (use this to infer scale, e.g. whether a percentage column is 0-1 or 0-100):
{ranges_text}

Data quality issues found in this dataset:
{quality_text}

Previous questions and answers in this conversation (use for context on follow-up questions like "now show that by region"):
{memory_text}

Sample rows:
{sample_rows}

Write Python Pandas code to answer this question:
"{question}"

Rules:
- Only use the variable name `df`.
- `pd` (pandas) is already available — never write `import pandas` or any import statement.
- Handle missing values (NaN) defensively — use .dropna() on relevant columns before aggregating.
- Never assume a column is 100% clean, even if it looks numeric.
- For percentage-like columns, check the value range above before dividing.
- If this question refers to a previous question (e.g. "now by region", "what about last month"), use the conversation history above to understand what it's building on.
- Store the final answer in a variable called `result`.
- Return ONLY executable Python code, no explanations, no markdown fences.
"""
    return prompt


def generate_code(question: str, df: pd.DataFrame, quality_report=None, memory=None) -> str:
    prompt = build_prompt(question, df, quality_report, memory)
    response = call_with_retry(lambda: client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt
    ))
    code = response.text.strip()
    code = code.replace("```python", "").replace("```", "").strip()
    return code

@traceable(name="generate_code_with_retry")
def generate_code_with_retry(question: str, df: pd.DataFrame, quality_report=None, memory=None, max_attempts: int = 3):
    from app.executor import safe_execute_with_timeout, ExecutionError

    log_event("question_received", question=question, pipeline="pandas")

    prompt = build_prompt(question, df, quality_report, memory)
    attempt_history = []

    for attempt in range(1, max_attempts + 1):
        response = call_with_retry(lambda: client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt
        ))
        log_token_usage_to_trace(response)
        code = response.text.strip().replace("```python", "").replace("```", "").strip()
        log_event("code_generated", question=question, attempt=attempt, code=code)

        try:
            result = safe_execute_with_timeout(code, df, timeout_seconds=10.0)
            attempt_history.append({"attempt": attempt, "code": code, "status": "success"})
            log_event("execution_success", question=question, attempt=attempt)
            return result, code, attempt_history
        except ExecutionError as e:
            attempt_history.append({"attempt": attempt, "code": code, "status": "failed", "error": str(e)})
            log_error("execution_failed", e, question=question, attempt=attempt, code=code)

            if attempt == max_attempts:
                log_error("all_attempts_exhausted", e, question=question)
                raise ExecutionError(f"Failed after {max_attempts} attempts. Last error: {e}")

            prompt = f"""{prompt}

Your previous attempt produced this code:
{code}

It failed with this error:
{e}

Fix the code so it runs correctly. Return ONLY the corrected executable Python code, no explanations, no markdown fences.
"""

    raise ExecutionError("Unexpected: retry loop exited without result.")

def ask_question_safely(question: str, df, quality_report=None, memory=None):
    from app.errors import AnalysisError
    from app.logger import log_error, log_event

    if not is_data_question(question, df):
        log_event("non_data_question", question=question)
        response_text = handle_non_data_question(question)
        return response_text, None, []

    try:
        result, code, history = generate_code_with_retry(question, df, quality_report, memory)
        return result, code, history
    except ExecutionError as e:
        raise AnalysisError(
            user_message="I wasn't able to answer that question. Try rephrasing it, or ask something more specific about your data.",
            internal_detail=str(e)
        )
    except Exception as e:
        log_error("unexpected_error", e, question=question)
        raise AnalysisError(
            user_message="Something went wrong while processing your question. Please try again.",
            internal_detail=f"{type(e).__name__}: {e}"
        )

def is_data_question(question: str, df: pd.DataFrame = None) -> bool:
    """Quick check: is this actually answerable from the dataset, or just conversation?"""
    columns_context = ""
    if df is not None:
        columns_context = f"\nThe dataset has these columns: {list(df.columns)}"

    prompt = f"""Is the following question something that could be answered by analyzing a dataset
(e.g. asking for a calculation, aggregation, filter, trend, or comparison involving the data)?
{columns_context}

Question: "{question}"

If the question mentions or relates to any of the columns listed above, even briefly or informally, answer YES.
Answer with only one word: YES or NO.
"""
    response = call_with_retry(lambda: client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt
    ))
    answer = response.text.strip().upper()
    return answer.startswith("YES")


def handle_non_data_question(question: str) -> str:
    """Responds conversationally to non-data questions instead of forcing code generation."""
    prompt = f"""You are a helpful data analyst assistant. The user asked something that isn't
a data analysis question: "{question}"

Respond briefly and naturally (1-2 sentences). If it's a greeting, greet them back and mention
you're here to help analyze their data. If it's something you genuinely can't know (like today's
date, or general knowledge), say so honestly and redirect them toward asking about their dataset.
"""
    response = call_with_retry(lambda: client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt
    ))
    return response.text.strip()

@traceable(name="generate_explanation")
def generate_explanation(question: str, result, code: str) -> str:
    """Generates a short natural-language explanation of why the result is what it is."""
    prompt = f"""A data analyst asked: "{question}"

The answer computed was: {str(result)[:400]}

The code used to compute it:
{code}

In 1-2 short sentences, explain what's driving this result in plain language — what pattern,
concentration, or factor in the data explains it. Be specific and analytical, not generic.
Do not repeat the question or the number itself, just explain the "why."
"""
    response = call_with_retry(lambda: client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt
    ))
    return response.text.strip()

def generate_dataset_insights(df: pd.DataFrame, quality_report=None) -> str:
    """Generates an executive-summary style narrative about the dataset for the export report."""
    columns_info = "\n".join([f"- {col} ({df[col].dtype})" for col in df.columns])
    sample = df.head(5).to_string()
    quality_text = quality_report.to_prompt_text() if quality_report else "No issues detected."

    prompt = f"""You are a senior data analyst writing an executive summary for a stakeholder report.

Dataset columns:
{columns_info}

Data quality notes:
{quality_text}

Sample rows:
{sample}

Write a 4-6 sentence executive summary covering: what this dataset represents, any notable
patterns or concentrations worth investigating further, and data quality caveats a reader should
know about. Write in flowing prose, no bullet points, professional and specific, not generic.
"""
    response = call_with_retry(lambda: client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt
    ))
    return response.text.strip()

def generate_key_insights(df: pd.DataFrame, quality_report=None) -> list:
    columns_info = "\n".join([f"- {col} ({df[col].dtype})" for col in df.columns])
    sample = df.head(5).to_string()
    prompt = f"""You are a senior data analyst. Look at this dataset:

Columns:
{columns_info}

Sample rows:
{sample}

Generate exactly 3 short, specific, analytical insights a viewer would find valuable at a glance.
Be specific with column names and plausible patterns, not generic statements.
Return ONLY a JSON array of 3 strings, nothing else.
"""
    response = call_with_retry(lambda: client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt
    ))
    text = response.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        import json
        return json.loads(text)
    except Exception:
        return []