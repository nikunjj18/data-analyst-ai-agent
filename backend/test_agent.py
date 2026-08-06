from app.agent import load_data, generate_code
from app.executor import safe_execute, ExecutionError

df = load_data("../data/sample_sales.csv")

questions = [
    "What is the total revenue by category?",
    "What was total revenue by region and month?",
    "Which product had the highest quantity sold?",
    "What's the average discount percentage by customer segment?",
]

for question in questions:
    print("=" * 60)
    print("Question:", question)

    code = generate_code(question, df)
    print("\nGenerated code:\n", code)

    try:
        result = safe_execute(code, df)
        print("\nResult:\n", result)
    except ExecutionError as e:
        print("\nExecution failed:", e)

    print()