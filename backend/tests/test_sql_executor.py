import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.sql_executor import is_safe_query, safe_execute_sql, safe_execute_sql_with_timeout, SQLExecutionError

DB_PATH = "../data/company_data.db"


def test_is_safe_query_allows_select():
    assert is_safe_query("SELECT * FROM orders") is True


def test_is_safe_query_blocks_drop():
    assert is_safe_query("DROP TABLE orders") is False


def test_is_safe_query_blocks_delete():
    assert is_safe_query("DELETE FROM orders WHERE order_id = 1") is False


def test_is_safe_query_blocks_update():
    assert is_safe_query("UPDATE orders SET quantity = 0") is False


def test_is_safe_query_blocks_non_select_start():
    assert is_safe_query("orders; SELECT * FROM orders") is False


def test_is_safe_query_blocks_pragma():
    assert is_safe_query("SELECT * FROM orders; PRAGMA table_info(orders)") is False


def test_safe_execute_sql_runs_valid_query():
    result = safe_execute_sql("SELECT COUNT(*) as cnt FROM orders", DB_PATH)
    assert result["cnt"].iloc[0] > 0


def test_safe_execute_sql_blocks_destructive_query():
    with pytest.raises(SQLExecutionError, match="Only read-only SELECT"):
        safe_execute_sql("DELETE FROM orders", DB_PATH)


def test_safe_execute_sql_with_timeout_catches_slow_query():
    slow_sql = "SELECT COUNT(*) FROM orders o1, orders o2, orders o3"
    with pytest.raises(SQLExecutionError, match="timed out"):
        safe_execute_sql_with_timeout(slow_sql, DB_PATH, timeout_seconds=1.0)