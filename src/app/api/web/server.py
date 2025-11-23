import base64
import csv
import json
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.app.agents.user_requests_agent.run import run_agent


BASE_DIR = Path(__file__).resolve().parents[2]
RESOURCES_DIR = BASE_DIR / "resourses"
CSV_PATH = RESOURCES_DIR / "report.csv"
PNG_PATH = RESOURCES_DIR / "plot.png"


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class CSVPayload(BaseModel):
    headers: List[str]
    rows: List[List[str]]
    download_url: str


class PNGPayload(BaseModel):
    image_base64: str
    download_url: str


class ChatResponse(BaseModel):
    text: str
    csv: Optional[CSVPayload] = None
    png: Optional[PNGPayload] = None


app = FastAPI(title="Hihiton Web API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _extract_agent_text(content) -> str:
    """LangGraph может вернуть контент в формате списка словарей."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for chunk in content:
            value = chunk.get("text") if isinstance(chunk, dict) else str(chunk)
            if value:
                parts.append(value)
        return "".join(parts)
    return str(content)


def _build_csv_payload() -> Optional[CSVPayload]:
    if not CSV_PATH.exists():
        return None

    with CSV_PATH.open("r", newline="", encoding="utf-8") as csv_file:
        reader = list(csv.reader(csv_file))

    if not reader:
        return None

    headers = reader[0]
    rows = reader[1:] if len(reader) > 1 else []
    return CSVPayload(
        headers=headers,
        rows=rows,
        download_url="/api/download/csv",
    )


def _build_png_payload() -> Optional[PNGPayload]:
    if not PNG_PATH.exists():
        return None

    image_base64 = base64.b64encode(PNG_PATH.read_bytes()).decode("utf-8")
    return PNGPayload(image_base64=image_base64, download_url="/api/download/png")


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        raw_result = run_agent(request.message, thread_id=request.session_id or "web-session")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

    try:
        assistant_message = raw_result["messages"][-1].content
    except (KeyError, IndexError) as exc:
        raise HTTPException(status_code=500, detail="Unexpected agent response format") from exc

    text_payload = _extract_agent_text(assistant_message)

    try:
        parsed_payload = json.loads(text_payload)
        reply_text = parsed_payload.get("text", text_payload)
        csv_requested = parsed_payload.get("csv")
        png_requested = parsed_payload.get("png")
    except json.JSONDecodeError:
        reply_text = text_payload
        csv_requested = False
        png_requested = False

    csv_payload = _build_csv_payload() if csv_requested else None
    png_payload = _build_png_payload() if png_requested else None

    return ChatResponse(text=reply_text, csv=csv_payload, png=png_payload)


@app.get("/api/download/csv")
def download_csv():
    if not CSV_PATH.exists():
        raise HTTPException(status_code=404, detail="CSV report not found")
    return FileResponse(path=CSV_PATH, media_type="text/csv", filename=CSV_PATH.name)


@app.get("/api/download/png")
def download_png():
    if not PNG_PATH.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path=PNG_PATH, media_type="image/png", filename=PNG_PATH.name)
