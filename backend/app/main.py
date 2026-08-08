from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import pandas as pd
import shutil
import os
import tempfile

from app.preprocessor import auto_clean, apply_user_decisions
from app.agent import ask_question_safely
from app.errors import AgentError
from app.memory import ConversationMemory
from app.visualizer import render_chart
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Data Analyst AI Agent", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://your-app.vercel.app"],  # update the Vercel URL once deployed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory session state (single-user demo scope — see README limitations)
session = {
    "df": None,
    "quality_report": None,
    "memory": ConversationMemory(),
}


class QuestionRequest(BaseModel):
    question: str


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Uploads and cleans a CSV, storing it in the session for subsequent questions."""
    temp_path = os.path.join(tempfile.gettempdir(), file.filename)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        df, quality_report, pending = auto_clean(temp_path)
        # For the API, auto-apply safe defaults for ambiguous decisions
        # (a real UI would surface `pending` to the user — Phase 8 improvement)
        df = apply_user_decisions(df, pending, {})

        session["df"] = df
        session["quality_report"] = quality_report
        session["memory"] = ConversationMemory()

        return {
            "message": "File uploaded and cleaned successfully",
            "rows": len(df),
            "columns": list(df.columns),
            "quality_report": quality_report.to_prompt_text(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process file: {e}")
    finally:
        os.remove(temp_path)


@app.post("/ask")
def ask(request: QuestionRequest):
    if session["df"] is None:
        raise HTTPException(status_code=400, detail="No dataset uploaded yet. Call /upload first.")

    try:
        result, code, history = ask_question_safely(
            request.question, session["df"], session["quality_report"], session["memory"]
        )
        session["memory"].add(request.question, str(result)[:500])

        chart_generated = False
        if code is not None:  # only chart real analysis results, not conversational replies
            chart_path = os.path.join(tempfile.gettempdir(), "latest_chart.png")
            fig, chart_code = render_chart(result, request.question, save_path=chart_path)
            chart_generated = fig is not None

        return {
            "question": request.question,
            "result": str(result),
            "code": code,
            "chart_generated": chart_generated,
            "attempts": len(history),
        }
    except AgentError as e:
        raise HTTPException(status_code=422, detail=e.user_message)



@app.get("/chart")
def get_chart():
    """Returns the most recently generated chart image."""
    from fastapi.responses import FileResponse
    chart_path = os.path.join(tempfile.gettempdir(), "latest_chart.png")
    if not os.path.exists(chart_path):
        raise HTTPException(status_code=404, detail="No chart generated yet.")
    return FileResponse(chart_path)