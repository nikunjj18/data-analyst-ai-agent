from app.preprocessor import auto_clean, apply_user_decisions, collect_decisions_cli
from app.agent import generate_code_with_retry
from app.visualizer import render_chart
from app.executor import ExecutionError
import time
# Load and clean data
df, quality_report, pending = auto_clean("../data/messy_sales.csv")
decisions = collect_decisions_cli(pending)
df = apply_user_decisions(df, pending, decisions)

# Questions covering different chart types
questions = [

    # Bar chart candidates — ranked category comparisons
    "What is the total revenue by category?",
    "Which product had the highest total quantity sold?",
    "What is the total revenue by region?",

    # Line chart candidates — trends over time
    "What is the trend of total revenue by month?",
    "How did average discount percentage change month over month?",

    # Pie chart candidates — parts of a whole, few categories
    "What percentage of total revenue comes from each customer segment?",
    "What is the proportion of orders by region?",

    # Histogram candidates — distribution of one numeric column
    "What is the distribution of unit prices across all orders?",
    "What is the distribution of discount percentages?",

    # Heatmap candidates — matrix across two categorical dimensions
    "What is the average revenue for each category across each region?",
    "What is the correlation between quantity, unit_price, and discount_pct?",

    # Scatter candidates — relationship between two numeric variables
    "What is the relationship between quantity and unit_price for each order?",
    "How does discount percentage relate to net revenue per order?",

    # Edge case — should trigger "none" (single number)
    "What is the total revenue across all orders?",
    "What is the average discount percentage overall?",
]

for i, question in enumerate(questions, start=1):
    print("=" * 60)
    print(f"[{i}] {question}")
    try:
        result, code, history = generate_code_with_retry(question, df, quality_report)
        print("Result:\n", result)
        fig, chart_code = render_chart(result, question, save_path=f"chart_{i}.png")
        print("Chart saved:", f"chart_{i}.png" if fig else "No chart (or failed)")
    except ExecutionError as e:
        print("Failed:", e)
    time.sleep(4)