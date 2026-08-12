import pandas as pd
import numpy as np


class DataQualityReport:
    """Holds everything discovered during Stage 1 automatic cleaning."""

    def __init__(self):
        self.unlabeled_columns = []
        self.empty_columns = []
        self.null_summary = {}
        self.mixed_type_columns = {}
        self.duplicate_row_count = 0
        self.categorical_normalizations = {}
        self.total_rows = 0

    def to_prompt_text(self) -> str:
        lines = []
        if self.unlabeled_columns:
            lines.append(f"- Unlabeled columns (auto-renamed): {', '.join(self.unlabeled_columns)}")
        if self.empty_columns:
            lines.append(f"- Empty columns (dropped): {', '.join(self.empty_columns)}")
        if self.mixed_type_columns:
            for col, info in self.mixed_type_columns.items():
                lines.append(f"- '{col}': {info['bad_count']} non-numeric values coerced to NaN (e.g. {info['examples']})")
        if self.categorical_normalizations:
            for col, mapping in self.categorical_normalizations.items():
                merged = ", ".join(f"'{k}'->'{v}'" for k, v in mapping.items())
                lines.append(f"- '{col}': normalized casing ({merged})")
        if self.duplicate_row_count > 0:
            lines.append(f"- {self.duplicate_row_count} duplicate rows detected (not removed automatically)")
        if self.null_summary:
            null_lines = [
                f"  - {col}: {info['count']} nulls ({info['pct']}%)"
                for col, info in self.null_summary.items() if info["count"] > 0
            ]
            if null_lines:
                lines.append("- Missing values:\n" + "\n".join(null_lines))
        if not lines:
            return "No automatic cleaning issues detected."
        return "\n".join(lines)


class PendingDecision:
    """Represents one open question that needs a user's (or AI's) choice."""

    def __init__(self, issue_id, column, description, options):
        self.issue_id = issue_id
        self.column = column
        self.description = description
        self.options = options
        self.recommended = None


def recommend_decision(issue: PendingDecision, df: pd.DataFrame) -> str:
    """Picks a sensible default strategy for a data quality issue, without asking the user."""
    if issue.issue_id == "duplicates":
        return "a" if "a" in issue.options else list(issue.options.keys())[0]

    col = issue.column
    if col is None or col not in df.columns:
        return list(issue.options.keys())[-1]

    null_pct = df[col].isnull().mean() * 100

    if null_pct > 50:
        return "b" if "b" in issue.options else list(issue.options.keys())[0]

    is_numeric = pd.api.types.is_numeric_dtype(df[col])
    if is_numeric:
        try:
            skew = df[col].skew() if df[col].notna().sum() > 2 else 0
        except Exception:
            skew = 0
        if abs(skew) > 1 and "d" in issue.options:
            return "d"
        elif "c" in issue.options:
            return "c"
    else:
        if "c" in issue.options:
            return "c"

    return "b" if "b" in issue.options else list(issue.options.keys())[0]


def auto_clean(csv_path: str):
    """
    STAGE 1: Automatic, unambiguous cleaning only.
    Returns: (cleaned_df, quality_report, pending_decisions)
    """
    report = DataQualityReport()

    try:
        if csv_path.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(csv_path)
        else:
            df = pd.read_csv(csv_path)
    except pd.errors.EmptyDataError:
        raise ValueError("File is empty or has no columns.")
    except Exception as e:
        raise ValueError(f"Failed to read file: {e}")

    if df.shape[0] == 0:
        raise ValueError("File has headers but no data rows.")

    report.total_rows = len(df)

    # Fix unlabeled columns
    new_columns = {}
    for col in df.columns:
        if str(col).startswith("Unnamed:") or str(col).strip() == "":
            new_name = f"column_{len(new_columns) + 1}"
            new_columns[col] = new_name
            report.unlabeled_columns.append(new_name)
    if new_columns:
        df = df.rename(columns=new_columns)
    df.columns = [str(c).strip() for c in df.columns]

    # Drop fully empty columns
    for col in df.columns:
        if df[col].isnull().all():
            report.empty_columns.append(col)
    if report.empty_columns:
        df = df.drop(columns=report.empty_columns)

    # Strip whitespace, normalize null tokens
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"nan": np.nan, "None": np.nan, "N/A": np.nan, "": np.nan})

    # Coerce numeric-looking columns (>70% convertible)
    for col in df.select_dtypes(include="object").columns:
        coerced = pd.to_numeric(df[col], errors="coerce")
        non_null_original = df[col].notna().sum()
        non_null_coerced = coerced.notna().sum()
        if non_null_original > 0 and (non_null_coerced / non_null_original) > 0.7:
            bad_mask = df[col].notna() & coerced.isna()
            bad_count = bad_mask.sum()
            if bad_count > 0:
                examples = df.loc[bad_mask, col].unique()[:3].tolist()
                report.mixed_type_columns[col] = {"bad_count": int(bad_count), "examples": examples}
            df[col] = coerced

    # Normalize casing variants
    for col in df.select_dtypes(include="object").columns:
        non_null = df[col].dropna()
        if non_null.empty:
            continue
        lower_map = {}
        for val in non_null.unique():
            lower_map.setdefault(val.lower(), []).append(val)
        variants_found = {k: v for k, v in lower_map.items() if len(v) > 1}
        if variants_found:
            value_counts = df[col].value_counts()
            replace_map = {}
            for key, variants in variants_found.items():
                canonical = max(variants, key=lambda v: value_counts.get(v, 0))
                for v in variants:
                    if v != canonical:
                        replace_map[v] = canonical
            if replace_map:
                df[col] = df[col].replace(replace_map)
                report.categorical_normalizations[col] = replace_map

    # Null summary
    for col in df.columns:
        null_count = int(df[col].isnull().sum())
        report.null_summary[col] = {
            "count": null_count,
            "pct": round(null_count / len(df) * 100, 2),
        }

    report.duplicate_row_count = int(df.duplicated().sum())

    # Build pending decisions
    pending = []

    for col, info in report.null_summary.items():
        if info["count"] == 0:
            continue
        is_numeric = pd.api.types.is_numeric_dtype(df[col])
        options = {
            "a": ("Drop rows with missing values", "drop_rows"),
            "b": ("Leave as-is (NaN, handled per question)", "leave"),
        }
        if is_numeric:
            options["c"] = ("Fill with mean", "fill_mean")
            options["d"] = ("Fill with median", "fill_median")
        else:
            options["c"] = ("Fill with most common value", "fill_mode")

        pending.append(PendingDecision(
            issue_id=f"null_{col}",
            column=col,
            description=f"Column '{col}' has {info['count']} missing values ({info['pct']}%). How should this be handled?",
            options=options
        ))

    if report.duplicate_row_count > 0:
        pending.append(PendingDecision(
            issue_id="duplicates",
            column=None,
            description=f"{report.duplicate_row_count} duplicate rows detected. What should we do?",
            options={
                "a": ("Remove duplicates", "remove_duplicates"),
                "b": ("Keep as-is", "leave"),
            }
        ))

    for issue in pending:
        issue.recommended = recommend_decision(issue, df)

    return df, report, pending


def apply_user_decisions(df: pd.DataFrame, pending: list, decisions: dict) -> pd.DataFrame:
    """STAGE 3: Applies the chosen strategy for each pending decision."""
    for issue in pending:
        choice_key = decisions.get(issue.issue_id, "b")
        _, action = issue.options.get(choice_key, ("Leave as-is", "leave"))

        if issue.issue_id == "duplicates":
            if action == "remove_duplicates":
                df = df.drop_duplicates()
            continue

        col = issue.column
        if action == "drop_rows":
            df = df.dropna(subset=[col])
        elif action == "fill_mean":
            df[col] = df[col].fillna(df[col].mean())
        elif action == "fill_median":
            df[col] = df[col].fillna(df[col].median())
        elif action == "fill_mode":
            mode_val = df[col].mode()
            if not mode_val.empty:
                df[col] = df[col].fillna(mode_val[0])

    return df


def collect_decisions_cli(pending: list) -> dict:
    """Terminal-based version: asks the user interactively via input()."""
    decisions = {}
    if not pending:
        print("\nNo decisions needed — data was clean enough to proceed automatically.")
        return decisions

    print("\n" + "=" * 60)
    print("SOME DATA QUALITY ISSUES NEED YOUR INPUT")
    print("=" * 60)

    for issue in pending:
        print(f"\n{issue.description}")
        for key, (label, _) in issue.options.items():
            marker = " (AI recommended)" if issue.recommended == key else ""
            print(f"  [{key}] {label}{marker}")
        valid_keys = list(issue.options.keys())
        default = issue.recommended if issue.recommended in valid_keys else valid_keys[-1]
        choice = input(f"Choose [{'/'.join(valid_keys)}] (default {default}): ").strip().lower()
        if choice not in valid_keys:
            choice = default
        decisions[issue.issue_id] = choice

    return decisions