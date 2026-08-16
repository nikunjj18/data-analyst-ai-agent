from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd
import sqlite3
import shutil
import os
import tempfile
import uuid
import time
from datetime import datetime

from app.preprocessor import auto_clean, apply_user_decisions
from app.agent import ask_question_safely, generate_explanation, generate_dataset_insights, generate_key_insights
from app.errors import AgentError
from app.memory import ConversationMemory
from app.visualizer import render_chart
from app.report_generator import generate_pdf_report
from app.dashboard_engine import compute_full_dashboard
from app.dashboard_pdf_charts import render_all_dashboard_charts
from app.multi_table_loader import load_zip_as_database
from app.vector_store import build_vector_store, retrieve_relevant_tables, expand_with_related_tables
from app.sql_agent import generate_sql_with_retry
from app.schema_reader import get_table_names

app = FastAPI(title="Data Analyst AI Agent", version="1.0")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5173", "https://data-analyst-ai-agent-nikunj.vercel.app/"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


session = {
    "df": None, "quality_report": None, "memory": ConversationMemory(),
    "mode": "single", "db_path": None, "vector_collection": None, "active_history_id": None,
}

report_history = []
dataset_history = []
MAX_HISTORY = 5

CHARTS_DIR = os.path.join(tempfile.gettempdir(), "agent_charts")
os.makedirs(CHARTS_DIR, exist_ok=True)


class QuestionRequest(BaseModel):
    question: str


class SwitchDatasetRequest(BaseModel):
    id: str


def _push_history(name, mode, df=None, db_path=None, vector_collection=None, quality_report=None, cleaning_actions=None, preview=None):
    entry = {
        "id": str(uuid.uuid4()), "name": name, "mode": mode, "uploaded_at": datetime.now().isoformat(),
        "df": df, "db_path": db_path, "vector_collection": vector_collection, "quality_report": quality_report,
        "cleaning_actions": cleaning_actions or [], "rows": len(df) if df is not None else None,
        "columns": list(df.columns) if df is not None else [], "preview": preview or [],
        "memory": ConversationMemory(), "conversation_log": [], "report_history": [],
    }
    dataset_history.insert(0, entry)
    del dataset_history[MAX_HISTORY:]
    return entry


def _get_active_entry():
    return next((e for e in dataset_history if e["id"] == session.get("active_history_id")), None)


def _log_conversation(question, result, explanation, code, chart_id, attempts):
    entry = _get_active_entry()
    if entry is None:
        return
    entry["conversation_log"].append({
        "question": question, "time_q": datetime.now().isoformat(), "result": str(result),
        "explanation": explanation, "code": code, "chart_id": chart_id, "attempts": attempts,
        "time_a": datetime.now().isoformat(),
    })


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    allowed_extensions = (".csv", ".xlsx", ".xls", ".zip")
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail="Only CSV, Excel, or ZIP files are supported.")

    temp_path = os.path.join(tempfile.gettempdir(), file.filename)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        if file.filename.lower().endswith(".zip"):
            db_path, table_names, previews = load_zip_as_database(temp_path)
            collection = build_vector_store(db_path)

            entry = _push_history(file.filename, "multi", db_path=db_path, vector_collection=collection)

            session["mode"] = "multi"
            session["db_path"] = db_path
            session["vector_collection"] = collection
            session["df"] = None
            session["quality_report"] = None
            session["memory"] = entry["memory"]
            session["active_history_id"] = entry["id"]
            report_history.clear()

            return {
                "status": "ready", "id": entry["id"], "mode": "multi", "tables": table_names,
                "rows": None, "columns": [], "preview": [], "table_previews": previews,
                "quality_report": "Multi-table dataset, per-table cleaning not applicable.",
                "cleaning_actions": [], "conversation": [],
            }

        df, quality_report, pending = auto_clean(temp_path)

        cleaning_actions = []
        if pending:
            auto_decisions = {}
            for issue in pending:
                choice = issue.recommended or list(issue.options.keys())[-1]
                auto_decisions[issue.issue_id] = choice
                label = issue.options[choice][0]
                cleaning_actions.append(f"{issue.description} -> {label}")
            df = apply_user_decisions(df, pending, auto_decisions)

        preview = df.head(5).fillna("").astype(str).to_dict(orient="records")
        entry = _push_history(file.filename, "single", df=df, quality_report=quality_report, cleaning_actions=cleaning_actions, preview=preview)

        session["mode"] = "single"
        session["df"] = df
        session["quality_report"] = quality_report
        session["db_path"] = None
        session["vector_collection"] = None
        session["memory"] = entry["memory"]
        session["active_history_id"] = entry["id"]
        report_history.clear()

        return {
            "status": "ready", "id": entry["id"], "mode": "single", "tables": [],
            "rows": len(df), "columns": list(df.columns), "preview": preview, "table_previews": {},
            "quality_report": quality_report.to_prompt_text(), "cleaning_actions": cleaning_actions,
            "conversation": [],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process file: {e}")
    finally:
        os.remove(temp_path)


@app.get("/history")
def get_history():
    return [
        {"id": e["id"], "name": e["name"], "mode": e["mode"], "uploaded_at": e["uploaded_at"], "rows": e["rows"], "columns": e["columns"]}
        for e in dataset_history
    ]


@app.post("/switch-dataset")
def switch_dataset(request: SwitchDatasetRequest):
    entry = next((e for e in dataset_history if e["id"] == request.id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Dataset not found in recent history.")

    session["mode"] = entry["mode"]
    session["df"] = entry["df"]
    session["db_path"] = entry["db_path"]
    session["vector_collection"] = entry["vector_collection"]
    session["quality_report"] = entry["quality_report"]
    session["memory"] = entry["memory"]
    session["active_history_id"] = entry["id"]
    report_history.clear()
    report_history.extend(entry["report_history"])

    if entry["mode"] == "single":
        return {
            "status": "ready", "id": entry["id"], "mode": "single", "tables": [],
            "rows": entry["rows"], "columns": entry["columns"], "preview": entry["preview"], "table_previews": {},
            "quality_report": entry["quality_report"].to_prompt_text() if entry["quality_report"] else "",
            "cleaning_actions": entry["cleaning_actions"], "conversation": entry["conversation_log"],
        }
    else:
        table_names = get_table_names(entry["db_path"]) if entry["db_path"] else []
        return {
            "status": "ready", "id": entry["id"], "mode": "multi", "tables": table_names,
            "rows": None, "columns": [], "preview": [], "table_previews": {},
            "quality_report": "Multi-table dataset, per-table cleaning not applicable.", "cleaning_actions": [],
            "conversation": entry["conversation_log"],
        }


@app.post("/ask")
def ask(request: QuestionRequest):
    chart_id = None

    if session["mode"] == "multi":
        if session["db_path"] is None:
            raise HTTPException(status_code=400, detail="No dataset uploaded yet. Call /upload first.")
        try:
            relevant = retrieve_relevant_tables(session["vector_collection"], request.question, top_k=3)
            expanded = expand_with_related_tables(session["db_path"], relevant)
            result, sql, history = generate_sql_with_retry(request.question, expanded, session["db_path"], session["memory"])
            session["memory"].add(request.question, str(result)[:500])

            explanation = None
            try:
                explanation = generate_explanation(request.question, result, sql)
            except Exception:
                explanation = None

            chart_id = str(uuid.uuid4())
            chart_path = os.path.join(CHARTS_DIR, f"{chart_id}.png")
            fig, chart_code = render_chart(result, request.question, save_path=chart_path)
            if fig is None:
                chart_id = None
                if os.path.exists(chart_path):
                    os.remove(chart_path)

            log_entry = {"question": request.question, "answer": str(result), "explanation": explanation, "chart_id": chart_id}
            report_history.append(log_entry)
            active = _get_active_entry()
            if active:
                active["report_history"].append(log_entry)
            _log_conversation(request.question, result, explanation, sql, chart_id, len(history))

            return {"question": request.question, "result": str(result), "explanation": explanation, "code": sql, "chart_id": chart_id, "attempts": len(history)}
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not answer that question: {e}")

    if session["df"] is None:
        raise HTTPException(status_code=400, detail="No dataset uploaded yet. Call /upload first.")

    try:
        result, code, history = ask_question_safely(request.question, session["df"], session["quality_report"], session["memory"])
        session["memory"].add(request.question, str(result)[:500])

        explanation = None
        if code is not None:
            try:
                explanation = generate_explanation(request.question, result, code)
            except Exception:
                explanation = None

        if code is not None:
            chart_id = str(uuid.uuid4())
            chart_path = os.path.join(CHARTS_DIR, f"{chart_id}.png")
            fig, chart_code = render_chart(result, request.question, save_path=chart_path)
            if fig is None:
                chart_id = None
                if os.path.exists(chart_path):
                    os.remove(chart_path)

        log_entry = {"question": request.question, "answer": str(result), "explanation": explanation, "chart_id": chart_id}
        report_history.append(log_entry)
        active = _get_active_entry()
        if active:
            active["report_history"].append(log_entry)
        _log_conversation(request.question, result, explanation, code, chart_id, len(history))

        return {"question": request.question, "result": str(result), "explanation": explanation, "code": code, "chart_id": chart_id, "attempts": len(history)}
    except AgentError as e:
        raise HTTPException(status_code=422, detail=e.user_message)


@app.get("/chart/{chart_id}")
def get_chart_by_id(chart_id: str):
    chart_path = os.path.join(CHARTS_DIR, f"{chart_id}.png")
    if not os.path.exists(chart_path):
        raise HTTPException(status_code=404, detail="Chart not found.")
    return FileResponse(chart_path, media_type="image/png")


@app.get("/dashboard-insights")
def dashboard_insights():
    if session["mode"] == "multi":
        return {
            "widgets": [], "reasoning": "", "ai_insights": [], "multi_table": True,
            "tables": get_table_names(session["db_path"]) if session["db_path"] else [],
        }
    if session["df"] is None:
        raise HTTPException(status_code=400, detail="No dataset loaded yet.")
    return compute_full_dashboard(session["df"])


@app.get("/table-dashboard")
def table_dashboard(table_name: str):
    if session["mode"] != "multi" or session["db_path"] is None:
        raise HTTPException(status_code=400, detail="No multi-table dataset loaded.")
    valid_tables = get_table_names(session["db_path"])
    if table_name not in valid_tables:
        raise HTTPException(status_code=400, detail="Unknown table name.")
    conn = sqlite3.connect(session["db_path"])
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return compute_full_dashboard(df)


@app.get("/generate-insights")
def generate_insights():
    if session["mode"] == "multi":
        return {"insights": "This is a multi-table dataset. Ask specific questions in Ask Your Data to explore relationships between tables."}
    if session["df"] is None:
        raise HTTPException(status_code=400, detail="No dataset loaded yet.")
    insights = generate_dataset_insights(session["df"], session["quality_report"])
    return {"insights": insights}


def _build_multi_table_sections():
    """Builds dashboard + summary + charts per table. Each table is isolated in its
    own try/except so one table failing doesn't kill the whole export, and a short
    pause between tables avoids tripping the free-tier rate limit across many AI calls."""
    table_names = get_table_names(session["db_path"])
    sections = []

    for i, table_name in enumerate(table_names):
        section = {
            "table_name": table_name, "summary": None, "preview_rows": [],
            "columns": [], "dashboard_data": None, "chart_images": [],
        }
        try:
            conn = sqlite3.connect(session["db_path"])
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            conn.close()

            section["columns"] = list(df.columns)
            section["preview_rows"] = df.head(5).fillna("").astype(str).to_dict(orient="records")

            try:
                section["dashboard_data"] = compute_full_dashboard(df)
            except Exception as e:
                section["dashboard_data"] = {"error": str(e)}

            if section["dashboard_data"] and section["dashboard_data"].get("widgets"):
                try:
                    section["chart_images"] = render_all_dashboard_charts(section["dashboard_data"])
                except Exception:
                    section["chart_images"] = []

            try:
                section["summary"] = generate_dataset_insights(df, None)
            except Exception:
                section["summary"] = f"This table has {len(df)} rows and {len(df.columns)} columns: {', '.join(df.columns[:8])}."

        except Exception as e:
            section["summary"] = f"Could not fully analyze this table: {e}"

        sections.append(section)

        if i < len(table_names) - 1:
            time.sleep(2)  # brief pause between tables to stay under the free-tier rate limit

    return sections


def _build_report_pdf(include_qa: bool, output_path: str):
    active = _get_active_entry()

    if session["mode"] == "multi":
        dataset_info = {"name": active["name"] if active else "Multi-table dataset", "rows": "N/A"}
        multi_table_sections = _build_multi_table_sections()
        history_to_include = report_history if include_qa else []

        generate_pdf_report(
            dataset_info, "", [], [], history_to_include,
            charts_dir=CHARTS_DIR, output_path=output_path,
            multi_table_sections=multi_table_sections,
        )
        return

    dataset_info = {"name": active["name"] if active else "Uploaded dataset", "rows": len(session["df"])}
    columns = list(session["df"].columns)
    quality_text = session["quality_report"].to_prompt_text() if session["quality_report"] else ""
    preview_rows = active["preview"] if active else session["df"].head(5).fillna("").astype(str).to_dict(orient="records")

    dashboard_data, chart_images = None, []
    try:
        dashboard_data = compute_full_dashboard(session["df"])
        chart_images = render_all_dashboard_charts(dashboard_data)
    except Exception:
        dashboard_data, chart_images = None, []

    try:
        summary = generate_dataset_insights(session["df"], session["quality_report"])
    except Exception:
        summary = None

    history_to_include = report_history if include_qa else []

    generate_pdf_report(
        dataset_info, quality_text, preview_rows, columns, history_to_include,
        dashboard_data=dashboard_data, dashboard_chart_images=chart_images,
        charts_dir=CHARTS_DIR, output_path=output_path, ai_summary=summary,
    )


@app.get("/export-report")
def export_report():
    if session["mode"] == "single" and session["df"] is None:
        raise HTTPException(status_code=400, detail="No dataset loaded yet.")
    if session["mode"] == "multi" and session["db_path"] is None:
        raise HTTPException(status_code=400, detail="No dataset loaded yet.")

    try:
        output_path = os.path.join(tempfile.gettempdir(), "data_analysis_report.pdf")
        _build_report_pdf(include_qa=True, output_path=output_path)
        return FileResponse(output_path, filename="data_analysis_report.pdf", media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {e}")


@app.get("/export-dashboard")
def export_dashboard():
    if session["mode"] == "single" and session["df"] is None:
        raise HTTPException(status_code=400, detail="No dataset loaded yet.")
    if session["mode"] == "multi" and session["db_path"] is None:
        raise HTTPException(status_code=400, detail="No dataset loaded yet.")

    try:
        output_path = os.path.join(tempfile.gettempdir(), "dashboard_report.pdf")
        _build_report_pdf(include_qa=False, output_path=output_path)
        return FileResponse(output_path, filename="dashboard_report.pdf", media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate dashboard report: {e}")