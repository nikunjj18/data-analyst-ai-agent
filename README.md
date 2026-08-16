# Data Analyst AI Agent

An AI agent that answers natural language questions about data (CSV/SQL) by autonomously writing, executing, and self-correcting Python code — then generating a professionally styled chart for the result. Built to demonstrate real agentic behavior and production-grade reliability, not just a prompt-wrapper demo. Tested end-to-end: **20/20 (100%)** on an independently verified evaluation suite, **22/22** unit tests passing, and confirmed resistant to adversarial prompt injection.

## What it does

Ask a plain-English question about your dataset — *"What was total revenue by category?"* — and the agent:

1. **Cleans your data first** — automatically fixes unambiguous issues (whitespace, empty columns, inconsistent casing) and asks you how to handle ambiguous ones (missing values, duplicates) instead of silently guessing
2. **Writes Python/Pandas code** to answer your question, using an LLM (Gemini) that's given your actual schema, data quality report, and value ranges — not just column names
3. **Executes that code in a sandboxed environment** — no file system access, no imports, no dangerous builtins
4. **Self-corrects on failure** — if the generated code errors out, the agent feeds the error back to the model and retries (up to 3 attempts) before giving up
5. **Generates a chart** — the LLM chooses the most appropriate chart type (bar, line, pie, histogram, heatmap, scatter) for the specific shape of the result and writes fully styled, professional matplotlib/seaborn code for it
6. **Handles real-world API constraints gracefully** — automatic retry with backoff on rate limits and network timeouts, so the agent doesn't crash under normal production conditions
7. **Remembers the conversation** — follow-up questions like *"now show that by region instead"* or *"which one of those was lowest?"* work correctly, using recent Q&A history as context
8. **Answers questions against a real multi-table SQL database** — retrieves relevant tables via semantic search + foreign-key relationship expansion, then generates and self-corrects SQL (SELECT-only, all destructive statements blocked); chart generation works on SQL results too, not just Pandas/CSV results

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
- **SQLite + Chroma (local embeddings) for RAG-based multi-table querying** — implemented and tested

## Key engineering decisions

**Why sandboxed exec() instead of a full code execution service?**
For this project's scope, a restricted `exec()` environment (no dangerous builtins, no imports, isolated namespace) provides real protection against destructive generated code while staying simple enough to reason about and test thoroughly. A full container-per-execution approach is the next step for true multi-tenant production use.

**Why a two-stage data cleaning process instead of full automation?**
Some data issues have an objectively correct fix (empty columns, whitespace) and get auto-corrected. Others (should missing revenue be dropped or filled with the median?) are business decisions that silently guessing on would produce misleading analysis. The agent surfaces these as explicit choices rather than making assumptions.

**Why let the LLM choose chart types instead of hardcoded rules?**
Rule-based chart selection is faster and cheaper, but genuinely worse at handling edge cases and doesn't scale to new chart types without code changes. Letting the model reason about the result's shape and the question's intent produces more contextually appropriate visualizations, at the cost of an extra API call per question.

**Why cap the number of tables retrieved for RAG instead of pulling in every related table?**
Pure semantic similarity search misses tables that are structurally required but textually dissimilar from the question (e.g. a "revenue by region" question needs the `orders` table even though "orders" isn't mentioned). The fix is bidirectional foreign-key expansion — pulling in tables connected to the retrieved ones, in both directions. But on a large schema (15-25+ tables), unbounded expansion could pull in most of the database for one question, defeating RAG's purpose. A `max_tables` cap keeps context bounded regardless of schema size. At production scale, this would also need re-ranking of expanded tables by relevance and a hop-limit on expansion depth, rather than including every directly connected table unconditionally.

**Tested finding: semantic retrieval precision is weak with short, generic table descriptions**
To actually test whether RAG retrieval excludes irrelevant tables (not just includes relevant ones), the schema was extended with three tables unrelated to the sales data (`employees`, `marketing_campaigns`, `support_tickets`, no foreign key connection to the sales tables). Result: retrieval consistently pulled in 1-3 irrelevant tables per question — e.g. "which department has the highest average salary" (needs only `employees`) also retrieved `support_tickets`, `products`, and `orders`. Despite this, every generated SQL query was still correct, because the LLM's own reasoning filtered out irrelevant tables when writing the query. This means the RAG layer, as currently built, is not meaningfully narrowing context — it's mostly acting as a no-op, with the LLM doing the real filtering work at generation time. Known causes and fixes: (1) table descriptions are currently just column lists with no explicit purpose statement — adding a one-line semantic summary per table should improve embedding separation; (2) no reranking step after initial retrieval; (3) no domain/category metadata tagging (e.g. `sales` vs `hr` vs `marketing`) to filter before semantic search runs. This is a common, well-documented RAG failure mode at small-to-medium schema scale, not unique to this implementation — logged here as tested, unresolved future work rather than glossed over.

**Tested finding: prompt injection and sandbox security hold under adversarial input**
A test suite of 5 adversarial questions was run against the agent — attempts to leak `.env` contents, read system files (`/etc/passwd`), trigger a "developer mode, no restrictions" jailbreak, and directly inject Python (`__import__('os').system(...)`) via the question text. Results: the LLM itself declined or ignored every malicious instruction in 4/5 cases, answering only the legitimate part of the question (or refusing outright). In the one case where the LLM *did* attempt to comply (writing `import os` to list directory contents), the sandboxed executor correctly blocked it with `ImportError: __import__ not found`, and the self-correction loop correctly gave up after 3 failed attempts rather than finding a workaround. This confirms defense-in-depth: security does not depend solely on the LLM behaving correctly — the restricted execution environment holds even when the prompt-level defense doesn't.

**Execution timeouts, thread-based for cross-platform compatibility**
Both Pandas code execution and SQL execution run in a background thread with a hard timeout (10s default) so a runaway query or accidental infinite loop can't hang the application. Implemented with `threading` rather than Unix `signal.alarm()` for Windows compatibility. Tested with a deliberately expensive cartesian join (`orders` cross-joined with itself three times, ~8 billion row combinations) against a 2-second timeout: the runaway query was correctly caught and raised a clean timeout error, while a normal query on the same table completed instantly and succeeded — confirming the timeout distinguishes real slow queries from normal ones rather than firing indiscriminately. Note: Python cannot forcibly kill a thread, so a timed-out background thread is abandoned rather than terminated — this protects the main application from hanging but does not reclaim the resources the runaway thread is using. A process-based timeout would be needed to fully kill runaway execution, which is a reasonable next step for true production hardening.

**Structured logging: dual-format, unified across pipelines**
Every question, generated code/SQL, execution attempt, and result (success or failure) is logged in two formats: a human-readable log for quick debugging, and a JSON-lines file (one JSON object per line) for programmatic analysis — e.g. computing accuracy metrics or failure rates later without re-parsing free text. Both the Pandas and SQL pipelines log through the same `logger.py` module with a `pipeline` field distinguishing them, so failure patterns can be compared across both code paths from one place. Logs are excluded from version control (`.gitignore`) since they accumulate real usage data and grow unbounded.

**Centralized error handling: safe messages to users, full detail preserved internally**
All entry points to the agent are wrapped so that any exception — expected (retries exhausted) or unexpected (a genuine bug) — is converted into a generic `AgentError` with a clean, non-technical `user_message` before it ever reaches the caller. The full technical detail (`internal_detail`) is always logged via the structured logging system, so nothing is lost for debugging — it's just never shown raw to whoever is using the tool. This is a standard production pattern: users should never see a stack trace, but developers should never lose the information in one.

## Testing & accuracy

**Evaluation suite:** 20 natural language questions with independently pre-calculated ground-truth answers (computed directly with Pandas, not by the agent) — covering simple aggregation, category/region grouping, conditional counting (e.g. "orders with discount > 15%"), date-range filtering (Q1 2024), and multi-level grouping to find a maximum. Current result: **20/20 (100%)**.

**Unit tests:** 22 Pytest tests covering the core safety and cleaning modules in isolation (no LLM calls) — sandboxed execution (blocks dangerous builtins, imports, and infinite loops), SQL safety filtering (blocks DROP/DELETE/UPDATE/PRAGMA), and data cleaning behavior (unlabeled columns, empty columns, casing normalization, empty-file handling). Current result: **22/22 passing**.

Run them yourself:
```bash
cd backend
python run_eval.py       # evaluation suite
pytest tests/ -v          # unit tests
```

## Known limitations (current stage)

- Memory is a simple recent-history buffer (last 5 turns), not persisted between sessions
- RAG retrieval precision is weak — tested against a 7-table schema with deliberately unrelated tables, retrieval consistently included 1-3 irrelevant tables per question. SQL generation stayed correct because the LLM filtered irrelevant tables itself, but this means the RAG layer isn't yet reducing context the way it's meant to. See "Key engineering decisions" for root causes and planned fixes.
- SQL execution is read-only by design (SELECT-only, all destructive statements blocked) — this is intentional, not a gap, but worth noting explicitly for anyone reviewing the security model
- The agent can produce numerically valid but statistically meaningless results for nonsensical questions (e.g. standard deviation of a categorical column) — it doesn't yet reason about whether a question is statistically sound, only whether the code runs
- Not yet deployed — currently runs locally via test scripts, no API or UI layer yet
- Free-tier API rate limits (15 req/min) constrain how many questions can be processed per minute; retry logic handles this gracefully but doesn't eliminate the wait
- Eval suite (20 questions) and unit tests (22 tests) cover the Pandas/CSV pipeline and core safety modules; the SQL pipeline doesn't yet have an equivalent ground-truth eval suite

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
- [x] SQLite multi-table support with RAG-based retrieval and SQL generation — tested end-to-end (retrieval, bidirectional relationship expansion, self-correcting SQL generation, safe read-only execution)
- [ ] Improve RAG retrieval precision (richer table descriptions, reranking, domain metadata tagging) — tested and found weak on a 7-table schema, see engineering decisions above
- [x] Prompt injection / adversarial input testing — tested against 5 adversarial cases, LLM-level and sandbox-level defenses both confirmed working
- [x] Execution timeouts (Pandas + SQL) — thread-based, tested with a deliberately expensive cartesian join query
- [x] Structured logging — every question, generated code/SQL, attempt number, and success/failure logged to both a readable log and a JSON-lines file, unified across the Pandas and SQL pipelines
- [x] Centralized error handling — safe user-facing messages, full detail preserved in logs
- [x] Automated evaluation suite with accuracy metrics — 20 questions, independently verified ground truth, 20/20 (100%)
- [x] Unit test suite — 22 Pytest tests across core safety/cleaning modules, 22/22 passing
- [ ] Docker + CI/CD + deployment
- [ ] FastAPI backend
- [ ] Streamlit frontend
- [ ] Usage tracking and feedback mechanism (beyond structured logging)

## License

MIT