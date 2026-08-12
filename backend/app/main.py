from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd
import sqlite3
import shutil
import os
import tempfile

from app.preprocessor import auto_clean, apply_user_decisions
from app.agent import ask_question_safely, generate_explanation, generate_dataset_insights, generate_key_insights
from app.errors import AgentError
from app.memory import ConversationMemory
from app.visualizer import render_chart
from app.report_generator import generate_pdf_report
from app.dashboard_insights import compute_dashboard_insights
from app.multi_table_loader import load_zip_as_database
from app.vector_store import build_vector_store, retrieve_relevant_tables, expand_with_related_tables
from app.sql_agent import generate_sql_with_retry
from app.schema_reader import get_table_names

app = FastAPI(title="Data Analyst AI Agent", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://your-app.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session = {
    "df": None,
    "quality_report": None,
    "memory": ConversationMemory(),
    "mode": "single",
    "db_path": None,
    "vector_collection": None,
}

report_history = []


class QuestionRequest(BaseModel):
    question: str


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

            session["mode"] = "multi"
            session["db_path"] = db_path
            session["vector_collection"] = collection
            session["df"] = None
            session["quality_report"] = None
            session["memory"] = ConversationMemory()
            report_history.clear()

            return {
                "status": "ready",
                "mode": "multi",
                "tables": table_names,
                "rows": None,
                "columns": [],
                "preview": [],
                "table_previews": previews,
                "quality_report": "Multi-table dataset, per-table cleaning not applicable.",
                "cleaning_actions": [],
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

        session["mode"] = "single"
        session["df"] = df
        session["quality_report"] = quality_report
        session["db_path"] = None
        session["vector_collection"] = None
        session["memory"] = ConversationMemory()
        report_history.clear()

        preview = df.head(5).fillna("").astype(str).to_dict(orient="records")

        return {
            "status": "ready",
            "mode": "single",
            "tables": [],
            "rows": len(df),
            "columns": list(df.columns),
            "preview": preview,
            "table_previews": {},
            "quality_report": quality_report.to_prompt_text(),
            "cleaning_actions": cleaning_actions,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process file: {e}")
    finally:
        os.remove(temp_path)


@app.post("/ask")
def ask(request: QuestionRequest):
    if session["mode"] == "multi":
        if session["db_path"] is None:
            raise HTTPException(status_code=400, detail="No dataset uploaded yet. Call /upload first.")

        try:
            relevant = retrieve_relevant_tables(session["vector_collection"], request.question, top_k=3)
            expanded = expand_with_related_tables(session["db_path"], relevant)
            result, sql, history = generate_sql_with_retry(
                request.question, expanded, session["db_path"], session["memory"]
            )
            session["memory"].add(request.question, str(result)[:500])

            explanation = None
            try:
                explanation = generate_explanation(request.question, result, sql)
            except Exception:
                explanation = None

            chart_path = os.path.join(tempfile.gettempdir(), "latest_chart.png")
            fig, chart_code = render_chart(result, request.question, save_path=chart_path)
            chart_generated = fig is not None

            report_history.append({"question": request.question, "answer": str(result), "code": sql})

            return {
                "question": request.question,
                "result": str(result),
                "explanation": explanation,
                "code": sql,
                "chart_generated": chart_generated,
                "attempts": len(history),
            }
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not answer that question: {e}")

    if session["df"] is None:
        raise HTTPException(status_code=400, detail="No dataset uploaded yet. Call /upload first.")

    try:
        result, code, history = ask_question_safely(
            request.question, session["df"], session["quality_report"], session["memory"]
        )
        session["memory"].add(request.question, str(result)[:500])

        explanation = None
        if code is not None:
            try:
                explanation = generate_explanation(request.question, result, code)
            except Exception:
                explanation = None

        chart_generated = False
        if code is not None:
            chart_path = os.path.join(tempfile.gettempdir(), "latest_chart.png")
            fig, chart_code = render_chart(result, request.question, save_path=chart_path)
            chart_generated = fig is not None

        report_history.append({"question": request.question, "answer": str(result), "code": code})

        return {
            "question": request.question,
            "result": str(result),
            "explanation": explanation,
            "code": code,
            "chart_generated": chart_generated,
            "attempts": len(history),
        }
    except AgentError as e:
        raise HTTPException(status_code=422, detail=e.user_message)


@app.get("/chart")
def get_chart():
    chart_path = os.path.join(tempfile.gettempdir(), "latest_chart.png")
    if not os.path.exists(chart_path):
        raise HTTPException(status_code=404, detail="No chart generated yet.")
    return FileResponse(chart_path)


@app.get("/dataset-summary")
def dataset_summary():
    if session["df"] is None:
        raise HTTPException(status_code=400, detail="No dataset loaded yet.")
    from app.dashboard_insights import compute_dashboard_insights as _unused  # placeholder no-op import guard
    return {"rows": len(session["df"]), "columns": list(session["df"].columns)}


@app.get("/dashboard-insights")
def dashboard_insights():
    if session["mode"] == "multi":
        return {
            "widgets": [],
            "reasoning": "",
            "ai_insights": [],
            "multi_table": True,
            "tables": get_table_names(session["db_path"]) if session["db_path"] else [],
        }
    if session["df"] is None:
        raise HTTPException(status_code=400, detail="No dataset loaded yet.")
    result = compute_dashboard_insights(session["df"])
    try:
        result["ai_insights"] = generate_key_insights(session["df"], session["quality_report"])
    except Exception:
        result["ai_insights"] = []
    result["multi_table"] = False
    return result


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

    result = compute_dashboard_insights(df)
    try:
        result["ai_insights"] = generate_key_insights(df, None)
    except Exception:
        result["ai_insights"] = []
    result["multi_table"] = False
    return result


@app.get("/generate-insights")
def generate_insights():
    if session["mode"] == "multi":
        return {"insights": "This is a multi-table dataset. Ask specific questions in Ask Your Data to explore relationships between tables."}
    if session["df"] is None:
        raise HTTPException(status_code=400, detail="No dataset loaded yet.")
    insights = generate_dataset_insights(session["df"], session["quality_report"])
    return {"insights": insights}


@app.get("/export-report")
def export_report():
    if session["mode"] == "single" and session["df"] is None:
        raise HTTPException(status_code=400, detail="No dataset loaded yet.")
    if session["mode"] == "multi" and session["db_path"] is None:
        raise HTTPException(status_code=400, detail="No dataset loaded yet.")

    if session["mode"] == "multi":
        dataset_info = {"name": "Multi-table dataset", "rows": "N/A", "columns": get_table_names(session["db_path"])}
        quality_text = "Multi-table dataset, per-table quality checks not applicable."
    else:
        dataset_info = {"name": "Uploaded dataset", "rows": len(session["df"]), "columns": list(session["df"].columns)}
        quality_text = session["quality_report"].to_prompt_text() if session["quality_report"] else ""

    chart_path = os.path.join(tempfile.gettempdir(), "latest_chart.png")
    output_path = os.path.join(tempfile.gettempdir(), "data_analysis_report.pdf")
    generate_pdf_report(
        dataset_info, quality_text, report_history,
        chart_path=chart_path if os.path.exists(chart_path) else None,
        output_path=output_path,
    )

    return FileResponse(output_path, filename="data_analysis_report.pdf", media_type="application/pdf")