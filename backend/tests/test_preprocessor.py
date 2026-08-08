import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import pytest
from app.preprocessor import auto_clean, apply_user_decisions


def test_auto_clean_renames_unlabeled_columns(tmp_path):
    csv_content = "a,b,\n1,2,3\n4,5,6\n"
    file_path = tmp_path / "test.csv"
    file_path.write_text(csv_content)

    df, report, pending = auto_clean(str(file_path))
    assert "column_1" in report.unlabeled_columns


def test_auto_clean_drops_empty_columns(tmp_path):
    csv_content = "a,b,empty_col\n1,2,\n3,4,\n"
    file_path = tmp_path / "test.csv"
    file_path.write_text(csv_content)

    df, report, pending = auto_clean(str(file_path))
    assert "empty_col" in report.empty_columns
    assert "empty_col" not in df.columns


def test_auto_clean_normalizes_casing(tmp_path):
    csv_content = "region\nNorth\nnorth\nNORTH\nSouth\n"
    file_path = tmp_path / "test.csv"
    file_path.write_text(csv_content)

    df, report, pending = auto_clean(str(file_path))
    unique_regions = df["region"].unique()
    assert len(unique_regions) == 2  # North (merged) and South


def test_auto_clean_raises_on_empty_file(tmp_path):
    file_path = tmp_path / "empty.csv"
    file_path.write_text("")

    with pytest.raises(ValueError):
        auto_clean(str(file_path))


def test_apply_user_decisions_drop_rows():
    df = pd.DataFrame({"price": [10, None, 30]})
    from app.preprocessor import PendingDecision
    pending = [PendingDecision("null_price", "price", "desc", {"a": ("Drop", "drop_rows")})]
    result = apply_user_decisions(df, pending, {"null_price": "a"})
    assert len(result) == 2


def test_apply_user_decisions_fill_mean():
    df = pd.DataFrame({"price": [10.0, None, 30.0]})
    from app.preprocessor import PendingDecision
    pending = [PendingDecision("null_price", "price", "desc", {"c": ("Fill mean", "fill_mean")})]
    result = apply_user_decisions(df, pending, {"null_price": "c"})
    assert result["price"].iloc[1] == 20.0