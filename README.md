# AI Data Analyst Agent

An AI agent that turns a spreadsheet (or a set of related tables) into a conversation. Upload a dataset, and the agent cleans it, builds a dashboard, answers questions in plain English with real generated code, and produces a downloadable report — all automatically.

**Live demo:** [https://data-analyst-nikunj.vercel.app/]

---

## Screenshots

**Upload & Clean**
![](data/images/data-analyst-ai-agent\data\images\WhatsApp Image 2026-09-19 at 3.38.45 PM.jpeg)

![](data-analyst-ai-agent\data\images\WhatsApp Image 2026-09-19 at 3.40.00 PM.jpeg)

**Dashboard**
![](data-analyst-ai-agent\data\images\WhatsApp Image 2026-09-19 at 3.40.25 PM.jpeg)

**Ask Your Data**
![](data-analyst-ai-agent\data\images\WhatsApp Image 2026-09-19 at 3.40.57 PM.jpeg)

**Export Report**
![](data-analyst-ai-agent\data\images\WhatsApp Image 2026-09-19 at 3.43.07 PM.jpeg)

---

## What it does

1. **Upload** a CSV, Excel file, or a ZIP containing multiple related tables.
2. **Automatic cleaning** — the agent detects issues (missing values, duplicates, inconsistent casing, mixed types) and picks a sensible fix for each one automatically, then tells you exactly what it did.
3. **Dashboard** — the agent profiles the real data, infers the business domain (sales, HR, finance, etc.), and designs a dashboard suited to that specific dataset: KPIs with period-over-period comparisons, trend charts, breakdowns, correlations, and anomaly detection. No two datasets get the same dashboard.
4. **Ask Your Data** — a chat interface where you ask questions in plain English. The agent writes real Python (Pandas) or SQL code, runs it in a sandboxed environment, self-corrects if it fails, and explains why the answer makes sense. The generated code is visible if you want to check it.
5. **Export Report** — a downloadable PDF with the dataset overview, data quality summary, dashboard, and the full Q&A conversation.

For datasets with multiple related tables (uploaded as a ZIP), the agent uses retrieval (RAG) to figure out which tables are relevant to a question and writes SQL joins automatically.

---

## Tech stack

**Backend**
- Python, FastAPI
- Google Gemini API (`google-genai`) — code generation, chart design, explanations
- Pandas, NumPy — data processing
- SQLite — multi-table storage for ZIP uploads
- ChromaDB — vector store for RAG (schema retrieval across tables)
- Matplotlib, Seaborn — chart rendering (AI-generated code, and static charts for PDF export)
- ReportLab — PDF report generation
- Docker — containerized backend

**Frontend**
- React + Vite
- Recharts — interactive dashboard charts
- Plain CSS (no framework) — custom dark theme

**Observability**
- LangSmith — tracing, latency, and error-rate monitoring on every LLM call

**Deployment**
- Backend: Render (Docker)
- Frontend: Vercel

---

## Architecture

```
Upload (CSV / Excel / ZIP)
        │
        ▼
Data cleaning (automatic, AI-recommended fixes)
        │
        ├──────────────────────────────┐
        ▼                              ▼
Single table → Pandas pipeline   Multiple tables → SQLite + RAG pipeline
        │                              │
        └──────────────┬───────────────┘
                        ▼
        Dashboard engine (profile → domain inference →
        KPIs → anomaly detection → chart selection)
                        │
                        ▼
        Ask Your Data (question → generated code/SQL →
        sandboxed execution → self-correction → explanation)
                        │
                        ▼
            Export (PDF report with charts)
```

---

## Core engineering decisions

**Sandboxed code execution, not arbitrary code execution.**
Every piece of AI-generated code (Pandas or SQL) runs inside a restricted environment — no file access, no imports, no dangerous builtins, and a hard timeout. SQL is additionally checked to block anything except `SELECT` statements. This was tested against adversarial prompts (attempts to leak `.env`, read system files, inject Python) — the model itself declined most attempts, and the sandbox blocked the one case where it tried to comply.

**Data cleaning is automatic but transparent, not silent.**
Rather than asking the user to manually choose how to handle every missing-value column, the agent picks a statistically sensible default (e.g. median for skewed data, mean otherwise, drop for high-missing columns) and reports exactly what it changed. This was a deliberate tradeoff between full manual control and full automation.

**The dashboard is grounded in real computed statistics, not guessed from column names.**
Early versions had the AI design the dashboard purely from column names and a few sample rows, which produced generic, repetitive dashboards and occasionally misclassified columns (e.g. a continuous `revenue` column was flagged as an identifier because of its high cardinality). The current version computes real statistics first (skew, outliers, cardinality, null rates) and gives those facts to the AI, which then designs KPIs, picks the correct aggregation per metric (sum vs. average — a rate/percentage column should never be summed), and selects chart types based on what the data actually supports.

**RAG retrieval for multi-table datasets has a known precision limitation.**
Tested against a schema with unrelated tables mixed in, semantic retrieval alone pulled in 1–3 irrelevant tables per question. The generated SQL still stayed correct because the model filtered out irrelevant tables at generation time, but this means retrieval isn't yet reducing context the way it's meant to at scale. Logged as a known limitation, not silently ignored.

**Charts are generated by the AI, not templated.**
Instead of a fixed set of "if numeric, use bar chart" rules, the agent is given the shape and meaning of the result and asked to pick the most appropriate chart type and write the plotting code itself, including data labels (since a downloaded image has no hover tooltips).

---

## Problems faced and how they were fixed

| Problem | Fix |
|---|---|
| Deprecated SDK and shifting model names caused 404/quota errors | Migrated to `google-genai`, switched to `-latest` model aliases |
| Rate limits (15 req/min) and transient 503s failed questions outright | Retry with backoff for rate limits, server errors, and timeouts |
| Percentage columns treated as 0–1 fractions, producing negative revenue | Added value-range context to prompts so the model checks scale first |
| "North" / "north" / "NORTH" counted as separate categories | Case-insensitive normalization during automatic cleaning |
| Continuous `revenue` column misclassified as an identifier | Cardinality-based ID detection now skips float columns |
| Year columns (`1990`) parsed as 1970 timestamps, flattening trends | Dedicated date parser that detects year-like integer columns |
| 12-table ZIP fired 24 concurrent API calls, hitting rate limits | Per-table dashboards now load sequentially and render as they finish |
| PDF export showed KPIs as text but no charts | Separate matplotlib renderer for static PDF charts |
| CORS blocked the deployed frontend from reaching the backend | Added the real Vercel domain to backend CORS settings |
| LangSmith didn't track token usage automatically | Manual instrumentation via `usage_metadata` (partial — full cost tracking needs deeper LangChain integration) |

---

## Evaluation

A 40-question benchmark was run against a real multi-table dataset (downloaded from Kaggle, loaded via the ZIP/RAG pipeline) to compare two Gemini model variants, tracked with LangSmith.

| Model | Traces | Error Rate | P50 Latency | P99 Latency |
|---|---|---|---|---|
| gemini-3.1-flash-lite | 40 | 5% | 1.45s | 24.41s |
| gemini-3.5-flash-lite | 40 | 3% | 2.00s | 28.08s |

**Takeaway:** gemini-3.1-flash-lite is faster at the median but has a higher error rate; gemini-3.5-flash-lite is slower but more reliable. This kind of tradeoff is exactly why model selection should be measured, not assumed — the "newer" or "bigger" model isn't automatically the better choice for every use case.

A separate suite of 22 Pytest unit tests covers the core sandboxing, SQL-safety, and data-cleaning logic in isolation — all passing.

---

## Known limitations

- **RAG precision** — retrieval doesn't reliably exclude irrelevant tables on larger schemas.
- **Per-table dashboards, not unified** — no automatic join across tables into one combined view.
- **Cold starts** — Render's free tier sleeps after ~15 min idle; first request can take 30–50s.
- **In-memory state** — datasets and chat history are lost on backend restart.
- **Single session** — not built for concurrent multi-user use as-is.
- **Partial cost tracking** — latency and errors are automatic, token cost is manually instrumented.
- **No statistical sanity check** — the agent verifies code runs, not whether a question makes statistical sense (e.g. standard deviation of a categorical column).

---

## Project structure

```
data-analyst-ai-agent/
├── backend/
│   ├── app/
│   │   ├── main.py                 FastAPI app, all endpoints
│   │   ├── agent.py                Pandas code generation, self-correction
│   │   ├── sql_agent.py            SQL generation for multi-table datasets
│   │   ├── preprocessor.py         Automatic data cleaning
│   │   ├── dashboard_engine.py     Dashboard orchestration
│   │   ├── data_profiler.py        Real statistical profiling
│   │   ├── domain_inference.py     AI domain + metric detection
│   │   ├── kpi_engine.py           KPI computation with correct aggregation
│   │   ├── anomaly_detector.py     Statistical anomaly detection
│   │   ├── viz_selector.py         AI chart type/layout selection
│   │   ├── executor.py             Sandboxed Pandas execution
│   │   ├── sql_executor.py         Sandboxed, read-only SQL execution
│   │   ├── vector_store.py         RAG retrieval over table schemas
│   │   ├── visualizer.py           AI-generated matplotlib charts
│   │   ├── report_generator.py     PDF report building
│   │   └── ...
│   ├── tests/                      Pytest unit tests + eval question sets
│   ├── eval_harness.py             Model comparison evaluation script
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/                  Upload, Dashboard, AskData, ExportReport
│   │   ├── components/             TopNav
│   │   ├── DatasetContext.jsx      Shared app state
│   │   └── api.js                  Backend API calls
│   └── Dockerfile
└── docker-compose.yml
```

---

## Running locally

**Backend**
```bash
cd backend
python -m venv venv
source venv/Scripts/activate      # or source venv/bin/activate on Mac/Linux
pip install -r requirements.txt
```

Create `backend/.env`:
```
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-flash-lite-latest
LANGSMITH_API_KEY=your_key_here      # optional, for tracing
LANGSMITH_PROJECT=data-analyst-agent
LANGSMITH_TRACING=true
```

```bash
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

**With Docker**
```bash
docker compose up -d
```

---

## Roadmap / possible next steps

- Unified cross-table dashboard (auto-join related tables instead of per-table views)
- Persistent storage (database-backed sessions instead of in-memory)
- Improved RAG retrieval precision (richer table descriptions, reranking)
- CI pipeline running the test suite on every push
- Multi-user session isolation

---

Built by Nikunj.