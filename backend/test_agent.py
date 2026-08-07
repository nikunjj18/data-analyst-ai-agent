from app.preprocessor import auto_clean, apply_user_decisions, collect_decisions_cli
from app.agent import generate_code_with_retry
from app.memory import ConversationMemory
from app.visualizer import render_chart
from app.executor import ExecutionError
import time

df, quality_report, pending = auto_clean("../data/messy_sales.csv")
decisions = collect_decisions_cli(pending)
df = apply_user_decisions(df, pending, decisions)

memory = ConversationMemory()

conversation = [
    "What is the total revenue by category?",
    "Now show that by region instead.",
    "Which one of those had the lowest value?",
    "What will be the value if we multiply the answer from previous question by 2"
]

for i, question in enumerate(conversation, start=1):
    print("=" * 60)
    print("Question:", question)

    try:
        result, code, history = generate_code_with_retry(question, df, quality_report, memory)
        print("\nResult:\n", result)
        memory.add(question, str(result)[:500])

        fig, chart_code = render_chart(result, question, save_path=f"chart_{i}.png")
        print("Chart saved:", f"chart_{i}.png" if fig else "No chart (or failed)")
    except ExecutionError as e:
        print("Failed:", e)

    time.sleep(4)