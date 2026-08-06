import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from google import genai
from app.config import config
from app.api_utils import call_with_retry

client = genai.Client(api_key=config.GEMINI_API_KEY)


def describe_result(result) -> str:
    if isinstance(result, (int, float)):
        return f"Single numeric value: {result}"
    if isinstance(result, pd.Series):
        return (
            f"Pandas Series named '{result.name}' with {len(result)} entries.\n"
            f"Index: {list(result.index[:10])}\n"
            f"Values: {list(result.values[:10])}\n"
            f"Value dtype: {result.dtype}"
        )
    if isinstance(result, pd.DataFrame):
        return (
            f"Pandas DataFrame with shape {result.shape}.\n"
            f"Columns: {list(result.columns)}\n"
            f"Sample:\n{result.head(5).to_string()}"
        )
    return f"Unrecognized result type: {type(result)}"


def generate_chart_code(question: str, result) -> str:
    """Asks Gemini to write full, professional-quality matplotlib/seaborn code for this result."""
    result_desc = describe_result(result)

    prompt = f"""You are a senior data visualization designer. A user asked this question:
"{question}"

The analysis produced this result (available in code as the variable `result`):
{result_desc}

Write Python code using matplotlib and seaborn to create a publication-quality, professional chart for this result.

Requirements:
- Choose the most appropriate chart type yourself (bar, line, pie, histogram, heatmap, scatter, etc.) based on what best represents this data.
- Use an attractive, modern color palette (e.g. seaborn "Set2", "viridis", "rocket", or similar) — never default matplotlib blue.
- Use clean, readable fonts, a bold clear title based on the question, labeled axes, and no unnecessary chart clutter (remove top/right spines, use subtle gridlines).
- Add data labels/annotations on bars or slices where it improves readability.
- Rotate x-axis labels if they would overlap.
- If any axis contains Period, Timestamp, or datetime objects, convert them to strings first (e.g. .astype(str)) before plotting.
- Assume `result`, `pd` (pandas), `plt` (matplotlib.pyplot), and `sns` (seaborn) are already available — do NOT import anything.
- Create the figure with `fig, ax = plt.subplots(figsize=(9, 5.5), dpi=130)`.
- Do NOT call plt.show().
- At the end, the finished figure object must be stored in a variable called `fig`.

Return ONLY executable Python code. No explanations, no markdown fences.
"""
    response = call_with_retry(lambda: client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=prompt
    ))
    code = response.text.strip().replace("```python", "").replace("```", "").strip()
    return code


def render_chart(result, question: str, save_path: str = None, max_attempts: int = 2):
    """Generates chart code via Gemini, executes it safely, retries once on failure."""
    from app.executor import ExecutionError
    if isinstance(result, (int, float)):
        return None, "Result is a single number — no chart generated."
    code = generate_chart_code(question, result)

    for attempt in range(1, max_attempts + 1):
        safe_globals = {
            "pd": pd, "plt": plt, "sns": sns,
            "__builtins__": {"len": len, "range": range, "list": list, "str": str,
                  "int": int, "float": float, "round": round, "enumerate": enumerate,
                  "dict": dict, "zip": zip, "sorted": sorted, "min": min, "max": max}
        }
        local_vars = {"result": result}

        try:
            exec(code, safe_globals, local_vars)
            fig = local_vars.get("fig")
            if fig is None:
                raise ExecutionError("Generated chart code did not produce a `fig` variable.")

            plt.tight_layout()
            if save_path:
                fig.savefig(save_path, bbox_inches="tight", facecolor="white")
            return fig, code

        except Exception as e:
            if attempt == max_attempts:
                print(f"Chart generation failed after {max_attempts} attempts: {e}")
                return None, code
            # retry: feed the error back
            code = generate_chart_code(question, result)  # simple retry, regenerate fresh

    return None, code