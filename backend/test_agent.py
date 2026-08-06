from app.preprocessor import auto_clean, apply_user_decisions, collect_decisions_cli
from app.agent import generate_code_with_retry
from app.executor import ExecutionError

df, quality_report, pending = auto_clean("../data/messy_sales.csv")
decisions = collect_decisions_cli(pending)
df = apply_user_decisions(df, pending, decisions)

questions = [
    "What is the average of the 'total_profit_margin' column grouped by category?"
]

for question in questions:
    print("=" * 60)
    print("Question:", question)
    try:
        result, final_code, history = generate_code_with_retry(question, df, quality_report)
        print(f"\nSucceeded in {len(history)} attempt(s)")
        print("\nFinal code:\n", final_code)
        print("\nResult:\n", result)
    except ExecutionError as e:
        print("\nGave up after retries:", e)