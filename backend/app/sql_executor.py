import sqlite3
import pandas as pd
import re
import threading


class SQLExecutionError(Exception):
    pass


FORBIDDEN_KEYWORDS = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "ATTACH", "PRAGMA"]


def is_safe_query(sql: str) -> bool:
    """Only allows read-only SELECT queries. Blocks anything destructive."""
    normalized = sql.strip().upper()
    if not normalized.startswith("SELECT"):
        return False
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", normalized):
            return False
    return True


def safe_execute_sql(sql: str, db_path: str, timeout: float = 5.0) -> pd.DataFrame:
    """Executes a SELECT-only SQL query safely against the database."""
    if not is_safe_query(sql):
        raise SQLExecutionError(
            "Only read-only SELECT queries are allowed. Generated query was blocked for safety."
        )

    try:
        conn = sqlite3.connect(db_path, timeout=timeout)
        result = pd.read_sql_query(sql, conn)
        conn.close()
        return result
    except Exception as e:
        raise SQLExecutionError(f"{type(e).__name__}: {e}")

   
def safe_execute_sql_with_timeout(sql: str, db_path: str, timeout_seconds: float = 10.0) -> pd.DataFrame:
    """Runs safe_execute_sql in a background thread with a timeout."""
    result_container = {}
    error_container = {}

    def target():
        try:
            result_container["result"] = safe_execute_sql(sql, db_path)
        except Exception as e:
            error_container["error"] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        raise SQLExecutionError(f"SQL execution timed out after {timeout_seconds} seconds.")

    if "error" in error_container:
        raise error_container["error"]

    return result_container["result"]