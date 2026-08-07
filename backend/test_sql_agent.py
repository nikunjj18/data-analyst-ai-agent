from app.vector_store import build_vector_store, retrieve_relevant_tables, expand_with_related_tables
from app.sql_agent import generate_sql_with_retry
from app.sql_executor import SQLExecutionError
import time

db_path = "../data/company_data.db"
collection = build_vector_store(db_path)

questions = [
    "What is the total revenue by region?",
    "Which product has the highest profit margin?",
    "How many customers are in the Wholesale segment?",
]

for question in questions:
    print("=" * 60)
    print("Question:", question)

    relevant = retrieve_relevant_tables(collection, question, top_k=3)
    expanded = expand_with_related_tables(db_path, relevant)
    print("Tables used:", [t["table_name"] for t in expanded])

    try:
        result_df, sql, history = generate_sql_with_retry(question, expanded, db_path)
        print(f"\nSucceeded in {len(history)} attempt(s)")
        print("\nSQL:\n", sql)
        print("\nResult:\n", result_df)
    except SQLExecutionError as e:
        print("Failed:", e)

    time.sleep(4)