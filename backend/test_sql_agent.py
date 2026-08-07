from app.vector_store import build_vector_store, retrieve_relevant_tables, expand_with_related_tables
from app.sql_agent import generate_sql_with_retry
from app.sql_executor import SQLExecutionError
from app.visualizer import render_chart
import time

db_path = "../data/company_data.db"
collection = build_vector_store(db_path)

questions = [
    "What is the total revenue by region?",
    "Which department has the highest average salary?",
    "How many support tickets are currently open?",
]

for i, question in enumerate(questions, start=1):
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

        # Convert DataFrame result into something the chart function can use well
        if result_df.shape[1] == 2:
            chart_input = result_df.set_index(result_df.columns[0])[result_df.columns[1]]
        else:
            chart_input = result_df

        fig, chart_code = render_chart(chart_input, question, save_path=f"sql_chart_{i}.png")
        print("Chart saved:", f"sql_chart_{i}.png" if fig else "No chart (or failed)")

    except SQLExecutionError as e:
        print("Failed:", e)

    time.sleep(4)