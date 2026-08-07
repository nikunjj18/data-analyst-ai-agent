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
import threading


def safe_execute_with_timeout(code: str, df: pd.DataFrame, timeout_seconds: float = 10.0):
    """
    Runs safe_execute in a background thread with a timeout.
    If execution takes too long, raises ExecutionError instead of hanging forever.
    """
    result_container = {}
    error_container = {}

    def target():
        try:
            result_container["result"] = safe_execute(code, df)
        except Exception as e:
            error_container["error"] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        raise ExecutionError(f"Execution timed out after {timeout_seconds} seconds.")

    if "error" in error_container:
        raise error_container["error"]

    return result_container["result"]