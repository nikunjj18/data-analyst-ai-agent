from app.agent import load_data, generate_code
from app.executor import safe_execute, ExecutionError

df = load_data("../data/sample_sales.csv")

question = "What is the total revenue by category?"

code = generate_code(question, df)
print("Generated code:\n", code)

try:
    result = safe_execute(code, df)
    print("\nResult:\n", result)
except ExecutionError as e:
    print("\nExecution failed:", e)