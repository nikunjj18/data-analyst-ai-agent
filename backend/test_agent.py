from app.preprocessor import auto_clean, apply_user_decisions, collect_decisions_cli
from app.agent import ask_question_safely
from app.errors import AgentError
from app.memory import ConversationMemory
from app.visualizer import render_chart
import time

df, quality_report, pending = auto_clean("../data/messy_sales.csv")
decisions = collect_decisions_cli(pending)
df = apply_user_decisions(df, pending, decisions)

memory = ConversationMemory()

questions = [
    "What is the total revenue by category?",
    "Now show that by region instead.",
]

for i, question in enumerate(questions, start=1):
    print("=" * 60)
    print("Question:", question)

    try:
        result, code, history = ask_question_safely(question, df, quality_report, memory)
        print("\nGenerated code:\n", code)
        print("\nResult:\n", result)
        memory.add(question, str(result)[:500])

        fig, chart_code = render_chart(result, question, save_path=f"chart_{i}.png")
        print("Chart saved:", f"chart_{i}.png" if fig else "No chart (or failed)")

    except AgentError as e:
        print("User sees:", e.user_message)
        print("(Internal detail, logged, not shown to user):", e.internal_detail)

    time.sleep(4)