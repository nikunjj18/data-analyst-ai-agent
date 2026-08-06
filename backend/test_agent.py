from app.preprocessor import auto_clean, apply_user_decisions, collect_decisions_cli
from app.agent import build_prompt, generate_code
from app.executor import safe_execute, ExecutionError

# Stage 1: automatic cleaning
df, quality_report, pending = auto_clean("../data/messy_sales.csv")

print("=" * 60)
print("AUTOMATIC CLEANING REPORT")
print("=" * 60)
print(quality_report.to_prompt_text())

# Stage 2: ask user for decisions on ambiguous issues
decisions = collect_decisions_cli(pending)

# Stage 3: apply chosen decisions
df = apply_user_decisions(df, pending, decisions)

print(f"\nFinal cleaned dataframe shape: {df.shape}")

# Now run questions against the fully cleaned data
questions = [
    "What is the total revenue by category?",
    "How many orders are there per region?",
]

for question in questions:
    print("=" * 60)
    print("Question:", question)
    code = generate_code(question, df, quality_report)
    print("\nGenerated code:\n", code)
    try:
        result = safe_execute(code, df)
        print("\nResult:\n", result)
    except ExecutionError as e:
        print("\nExecution failed:", e)