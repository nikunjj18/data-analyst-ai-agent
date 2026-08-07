# Data Analyst AI Agent

An AI agent that answers natural language questions about data (CSV/SQL) by autonomously writing, executing, and self-correcting Python code — then generating a professionally styled chart for the result. Built to demonstrate real agentic behavior and production-grade reliability, not just a prompt-wrapper demo.

## What it does

Ask a plain-English question about your dataset — *"What was total revenue by category?"* — and the agent:

1. **Cleans your data first** — automatically fixes unambiguous issues (whitespace, empty columns, inconsistent casing) and asks you how to handle ambiguous ones (missing values, duplicates) instead of silently guessing
2. **Writes Python/Pandas code** to answer your question, using an LLM (Gemini) that's given your actual schema, data quality report, and value ranges — not just column names
3. **Executes that code in a sandboxed environment** — no file system access, no imports, no dangerous builtins
4. **Self-corrects on failure** — if the generated code errors out, the agent feeds the error back to the model and retries (up to 3 attempts) before giving up
5. **Generates a chart** — the LLM chooses the most appropriate chart type (bar, line, pie, histogram, heatmap, scatter) for the specific shape of the result and writes fully styled, professional matplotlib/seaborn code for it
6. **Handles real-world API constraints gracefully** — automatic retry with backoff on rate limits and network timeouts, so the agent doesn't crash under normal production conditions
7. **Remembers the conversation** — follow-up questions like *"now show that by region instead"* or *"which one of those was lowest?"* work correctly, using recent Q&A history as context

## Why this project exists

Most "AI data analyst" demos assume clean data and a stable API connection. This one doesn't. It was deliberately built and stress-tested against messy CSVs (nulls, mixed types, unlabeled columns, inconsistent casing, duplicates) and real API failure modes (rate limits, timeouts) — the actual conditions a production tool has to survive.

## Architecture

```
Question (natural language)
        │
        ▼
┌─────────────────────┐
│ Data preprocessing   │  auto-fix safe issues, flag ambiguous ones for user decision
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│ Code generation       │  LLM writes Pandas code, aware of schema, data quality,
│ (agent.py)            │  and recent conversation history (memory.py)
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│ Sandboxed execution   │  restricted builtins, no file/network access
│ (executor.py)         │
└─────────────────────┘
        │
   error? ──yes──▶ feed error back to LLM, retry (max 3x)
        │ no
        ▼
┌─────────────────────┐
│ Chart generation      │  LLM picks chart type + writes styled matplotlib/seaborn code
│ (visualizer.py)       │
└─────────────────────┘
        │
        ▼
   Answer + Chart
```

## Tech stack

- **Python** — core language
- **Gemini API** (`google-genai`) — code generation, chart design decisions
- **Pandas** — data manipulation
- **Matplotlib + Seaborn** — chart rendering
- **LangGraph** *(planned integration)* — agent orchestration
- **FastAPI** *(planned)* — backend API layer
- **Streamlit** *(planned)* — frontend UI
- **SQLite + RAG/vector store** *(planned)* — multi-table schema-aware querying

## Key engineering decisions

**Why sandboxed exec() instead of a full code execution service?**
For this project's scope, a restricted `exec()` environment (no dangerous builtins, no imports, isolated namespace) provides real protection against destructive generated code while staying simple enough to reason about and test thoroughly. A full container-per-execution approach is the next step for true multi-tenant production use.

**Why a two-stage data cleaning process instead of full automation?**
Some data issues have an objectively correct fix (empty columns, whitespace) and get auto-corrected. Others (should missing revenue be dropped or filled with the median?) are business decisions that silently guessing on would produce misleading analysis. The agent surfaces these as explicit choices rather than making assumptions.

**Why let the LLM choose chart types instead of hardcoded rules?**
Rule-based chart selection is faster and cheaper, but genuinely worse at handling edge cases and doesn't scale to new chart types without code changes. Letting the model reason about the result's shape and the question's intent produces more contextually appropriate visualizations, at the cost of an extra API call per question.

## Known limitations (current stage)

- CSV only — SQL/multi-table support not yet implemented
- Memory is a simple recent-history buffer (last 5 turns), not persisted between sessions
- No RAG layer yet — schema is passed directly in the prompt, which won't scale to very wide/many-table datasets
- The agent can produce numerically valid but statistically meaningless results for nonsensical questions (e.g. standard deviation of a categorical column) — it doesn't yet reason about whether a question is statistically sound, only whether the code runs
- Not yet deployed — currently runs locally via test scripts, no API or UI layer yet
- Free-tier API rate limits (15 req/min) constrain how many questions can be processed per minute; retry logic handles this gracefully but doesn't eliminate the wait

## Setup

```bash
git clone <your-repo-url>
cd data-analyst-ai-agent
python -m venv venv
source venv/Scripts/activate   # or source venv/bin/activate on Mac/Linux
pip install -r backend/requirements.txt
```

Create a `.env` file in the project root (see `.env.example`):
```
GEMINI_API_KEY=your_key_here
ENVIRONMENT=development
```

Run the test pipeline:
```bash
cd backend
python test_agent.py
```

## Roadmap

- [x] Core NL → Pandas pipeline
- [x] Sandboxed code execution
- [x] Two-stage data cleaning (automatic + user-decision)
- [x] Self-correction on execution errors
- [x] LLM-driven chart generation with professional styling
- [x] Rate limit / network timeout resilience
- [x] Conversation memory for follow-up questions
- [ ] RAG-based schema retrieval for SQL/multi-table support
- [ ] FastAPI backend
- [ ] Streamlit frontend
- [ ] Prompt injection / adversarial input hardening
- [ ] Automated evaluation suite with accuracy metrics
- [ ] Docker + CI/CD + deployment
- [ ] Usage logging and observability

## License

MIT