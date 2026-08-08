import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import pytest
from app.executor import safe_execute, safe_execute_with_timeout, ExecutionError


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "category": ["A", "B", "A", "C"],
        "revenue": [100, 200, 150, 300],
    })


def test_safe_execute_basic_aggregation(sample_df):
    code = "result = df['revenue'].sum()"
    result = safe_execute(code, sample_df)
    assert result == 750


def test_safe_execute_groupby(sample_df):
    code = "result = df.groupby('category')['revenue'].sum()"
    result = safe_execute(code, sample_df)
    assert result["A"] == 250
    assert result["B"] == 200


def test_safe_execute_blocks_missing_result(sample_df):
    code = "x = 5"  # never sets `result`
    with pytest.raises(ExecutionError, match="did not set a `result`"):
        safe_execute(code, sample_df)


def test_safe_execute_blocks_dangerous_builtins(sample_df):
    code = "result = open('/etc/passwd').read()"
    with pytest.raises(ExecutionError):
        safe_execute(code, sample_df)


def test_safe_execute_blocks_import(sample_df):
    code = "import os\nresult = os.getcwd()"
    with pytest.raises(ExecutionError):
        safe_execute(code, sample_df)


def test_safe_execute_with_timeout_normal_case(sample_df):
    code = "result = df['revenue'].mean()"
    result = safe_execute_with_timeout(code, sample_df, timeout_seconds=5.0)
    assert result == 187.5


def test_safe_execute_with_timeout_catches_slow_code(sample_df):
    code = """
total = 0
for i in range(100_000_000):
    total += i
result = total
"""
    with pytest.raises(ExecutionError, match="timed out"):
        safe_execute_with_timeout(code, sample_df, timeout_seconds=1.0)