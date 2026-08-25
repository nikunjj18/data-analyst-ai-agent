import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from google import genai
from app.config import config
from app.api_utils import call_with_retry

client = genai.Client(api_key=config.GEMINI_API_KEY)


def is_chart_worthy(result) -> bool:
    if isinstance(result, (int, float, str)):
        return False
    if isinstance(result, pd.Series):
        return len(result) >= 2
    if isinstance(result, pd.DataFrame):
        return len(result) >= 2 and result.shape[1] >= 1
    return False


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
    result_desc = describe_result(result)

    prompt = f"""You are a senior data visualization designer. A user asked this question:
"{question}"

The analysis produced this result (available in code as the variable `result`):
{result_desc}

Write Python code using matplotlib and seaborn to create a publication-quality, professional chart for this result.

Requirements:
- Choose the most appropriate chart type yourself (bar, line, pie, histogram, heatmap, scatter, etc.) based on what best represents this data.
- Match the chart type strictly to what the question is actually asking: a single ranked comparison wants a bar chart, a trend over time wants a line chart, a share/percentage-of-whole with under 8 categories wants a pie chart, distribution of one numeric column wants a histogram, relationship between two numeric variables wants a scatter plot. Do not default to bar chart out of habit if another type fits the question better.
- Use an attractive, modern color palette (e.g. seaborn "Set2", "viridis", "rocket", or similar) — never default matplotlib blue.
- Use clean, readable fonts, a bold clear title based on the question, labeled axes, and no unnecessary chart clutter (remove top/right spines, use subtle gridlines).
- CRITICAL: since this image will be downloaded and viewed statically (no hover/tooltips available), you MUST add visible data labels directly on the chart:
  - Bar charts: put the value on top of (or at the end of) every bar using ax.bar_label() or ax.text() for each bar, formatted with thousands separators / 1 decimal place as appropriate.
  - Line charts: annotate each data point with its value using ax.annotate() or ax.text() near each point.
  - Pie charts: show both percentage AND the actual value in each slice label (e.g. "Electronics: 42% ($120K)").
  - Histograms: show the count on top of each bin bar.
  - Scatter plots: labeling every point is optional if it would be cluttered, but label any clear outliers.
- Rotate x-axis labels if they would overlap.
- If any axis contains Period, Timestamp, or datetime objects, convert them to strings first (e.g. .astype(str)) before plotting.
- Assume `result`, `pd` (pandas), `plt` (matplotlib.pyplot), and `sns` (seaborn) are already available — do NOT import anything.
- Create the figure with `fig, ax = plt.subplots(figsize=(9, 5.5), dpi=130)`.
- Do NOT call plt.show().
- At the end, the finished figure object must be stored in a variable called `fig`.

Return ONLY executable Python code. No explanations, no markdown fences.
"""
    response = call_with_retry(lambda: client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt
    ))
    code = response.text.strip().replace("```python", "").replace("```", "").strip()
    return code


def render_chart(result, question: str, save_path: str = None, max_attempts: int = 2):
    from app.executor import ExecutionError

    if not is_chart_worthy(result):
        return None, "not_chart_worthy"

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
            code = generate_chart_code(question, result)

    return None, code