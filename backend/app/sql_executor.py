import sqlite3
import pandas as pd
import re


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