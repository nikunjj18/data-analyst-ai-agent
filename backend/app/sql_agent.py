from google import genai
from app.config import config
from app.api_utils import call_with_retry
from app.sql_executor import safe_execute_sql, SQLExecutionError

client = genai.Client(api_key=config.GEMINI_API_KEY)


def build_sql_prompt(question: str, relevant_tables: list[dict], memory=None) -> str:
    schema_text = "\n\n".join([t["description"] for t in relevant_tables])
    memory_text = memory.to_prompt_text() if memory else "No previous questions in this conversation."

    prompt = f"""You are a SQL expert working with a SQLite database.

Only these tables are relevant to this question (retrieved via schema search):

{schema_text}

Previous questions and answers in this conversation:
{memory_text}

Write a single SQL SELECT query to answer this question:
"{question}"

Rules:
- Only use SELECT statements — no INSERT, UPDATE, DELETE, DROP, ALTER, or PRAGMA.
- Only reference the tables and columns shown above.
- Use proper JOINs based on the foreign key relationships shown.
- If revenue/profit is needed, calculate it explicitly as: quantity * unit_price * (1 - discount_pct / 100.0). The discount_pct column is stored as a percentage (0-100 scale, e.g. 10 means 10%), NOT as a decimal fraction — you must divide by 100 before using it as a multiplier.
- Return ONLY the raw SQL query, no explanations, no markdown fences, no semicolon needed but fine if included.
"""
    return prompt


def generate_sql_with_retry(question: str, relevant_tables: list[dict], db_path: str, memory=None, max_attempts: int = 3):
    """Generates SQL, executes it, self-corrects on failure. Returns (result_df, final_sql, history)."""
    prompt = build_sql_prompt(question, relevant_tables, memory)
    attempt_history = []

    for attempt in range(1, max_attempts + 1):
        response = call_with_retry(lambda: client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=prompt
        ))
        sql = response.text.strip().replace("```sql", "").replace("```", "").strip()

        try:
            result_df = safe_execute_sql(sql, db_path)
            attempt_history.append({"attempt": attempt, "sql": sql, "status": "success"})
            return result_df, sql, attempt_history
        except SQLExecutionError as e:
            attempt_history.append({"attempt": attempt, "sql": sql, "status": "failed", "error": str(e)})
            if attempt == max_attempts:
                raise SQLExecutionError(f"Failed after {max_attempts} attempts. Last error: {e}")
            prompt = f"""{prompt}

Your previous attempt produced this SQL:
{sql}

It failed with this error:
{e}

Fix the SQL so it runs correctly. Return ONLY the corrected SQL query, no explanations, no markdown fences.
"""

    raise SQLExecutionError("Unexpected: retry loop exited without result.")