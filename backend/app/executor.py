import pandas as pd


class ExecutionError(Exception):
    """Raised when generated code fails to execute."""
    pass


def safe_execute(code: str, df: pd.DataFrame):
    """
    Executes LLM-generated Pandas code in a restricted namespace.
    Only exposes `df` and `pd` — nothing else from the outside world.
    """
    # Restricted set of builtins — blocks things like open(), exec(), __import__()
    safe_builtins = {
        "len": len,
        "range": range,
        "sum": sum,
        "min": min,
        "max": max,
        "sorted": sorted,
        "round": round,
        "abs": abs,
        "list": list,
        "dict": dict,
        "str": str,
        "int": int,
        "float": float,
    }

    local_vars = {"df": df, "pd": pd}
    global_vars = {"__builtins__": safe_builtins}

    try:
        exec(code, global_vars, local_vars)
    except Exception as e:
        raise ExecutionError(f"{type(e).__name__}: {e}")

    if "result" not in local_vars:
        raise ExecutionError("Generated code did not set a `result` variable.")

    return local_vars["result"]