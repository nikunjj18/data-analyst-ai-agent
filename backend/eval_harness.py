"""
Runs N questions against the currently configured model (GEMINI_MODEL in .env).
Works with either a single CSV/Excel file (Pandas pipeline) or a ZIP of multiple
tables (SQL/RAG pipeline) — auto-detects based on the file extension.

Latency and cost are captured automatically by LangSmith (via the @traceable
decorators on generate_code_with_retry / generate_sql_with_retry) — view them
in the LangSmith "Monitor" tab, filtered to this run's time window.
"""
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from app.config import config
from app.preprocessor import auto_clean, apply_user_decisions
from app.agent import generate_code_with_retry
from app.executor import ExecutionError
from app.multi_table_loader import load_zip_as_database
from app.vector_store import build_vector_store, retrieve_relevant_tables, expand_with_related_tables
from app.sql_agent import generate_sql_with_retry
from app.memory import ConversationMemory


def load_questions(path="tests/eval_questions_40.txt"):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def run_eval_single_file(dataset_path: str, questions: list):
    print(f"Loading single-table dataset: {dataset_path}")
    df, quality_report, pending = auto_clean(dataset_path)
    if pending:
        auto_decisions = {}
        for issue in pending:
            choice = issue.recommended or list(issue.options.keys())[-1]
            auto_decisions[issue.issue_id] = choice
        df = apply_user_decisions(df, pending, auto_decisions)

    success_count = 0
    retried_count = 0
    failed_questions = []

    for i, question in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] {question}")
        try:
            result, code, history = generate_code_with_retry(question, df, quality_report)
            success_count += 1
            if len(history) > 1:
                retried_count += 1
            print(f"   -> success ({len(history)} attempt(s))")
        except ExecutionError as e:
            failed_questions.append({"question": question, "error": str(e)})
            print(f"   -> FAILED: {e}")
        time.sleep(3)

    return success_count, retried_count, failed_questions


def run_eval_multi_table(zip_path: str, questions: list):
    print(f"Loading multi-table dataset from zip: {zip_path}")
    db_path, table_names, _ = load_zip_as_database(zip_path)
    print(f"Loaded {len(table_names)} tables: {', '.join(table_names)}")
    collection = build_vector_store(db_path)
    memory = ConversationMemory()

    success_count = 0
    retried_count = 0
    failed_questions = []

    for i, question in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] {question}")
        try:
            relevant = retrieve_relevant_tables(collection, question, top_k=3)
            expanded = expand_with_related_tables(db_path, relevant)
            result, sql, history = generate_sql_with_retry(question, expanded, db_path, memory)
            success_count += 1
            if len(history) > 1:
                retried_count += 1
            print(f"   -> success ({len(history)} attempt(s))")
        except Exception as e:
            failed_questions.append({"question": question, "error": str(e)})
            print(f"   -> FAILED: {e}")
        time.sleep(3)

    return success_count, retried_count, failed_questions


def run_eval(dataset_path="data/eval_dataset.csv"):
    questions = load_questions()
    print(f"Loaded {len(questions)} questions. Model under test: {config.GEMINI_MODEL}")
    print(f"Run started at: {datetime.now().isoformat()}")
    print("(Latency + cost will be visible in LangSmith's Monitor tab for this time window)\n")

    if dataset_path.lower().endswith(".zip"):
        success_count, retried_count, failed_questions = run_eval_multi_table(dataset_path, questions)
    else:
        success_count, retried_count, failed_questions = run_eval_single_file(dataset_path, questions)

    total = len(questions)
    print("\n" + "=" * 60)
    print(f"Model: {config.GEMINI_MODEL}")
    print(f"Run finished at: {datetime.now().isoformat()}")
    print(f"Success rate: {success_count}/{total} ({round(success_count/total*100, 1)}%)")
    print(f"Self-correction rate: {retried_count}/{max(success_count,1)} successful questions needed a retry")
    if failed_questions:
        print("\nFailed questions:")
        for f in failed_questions:
            print(f"  - {f['question']}: {f['error']}")
    print("=" * 60)
    print("\nGo to smith.langchain.com -> your project -> Monitor tab,")
    print("filter to the time range printed above, to see latency and cost for this run.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="data/eval_dataset.csv", help="Path to CSV/Excel file or .zip of multiple tables")
    args = parser.parse_args()
    run_eval(dataset_path=args.dataset)