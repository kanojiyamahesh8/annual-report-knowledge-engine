"""FastAPI application for the annual-report Q&A service."""

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.config import settings
from app.qa import QAService
from app.retrieval import BM25Retriever, load_evidence


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@lru_cache(maxsize=1)
def get_qa_service() -> QAService:
    evidence_path = Path(settings.evidence_path)
    if not evidence_path.is_absolute():
        evidence_path = Path(__file__).resolve().parent.parent / evidence_path
    evidence = load_evidence(evidence_path)
    return QAService(BM25Retriever.from_evidence(evidence))


app = FastAPI(title="Provider-Agnostic Annual Report Knowledge Engine")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
def homepage(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/ask")
def ask(request: AskRequest) -> dict:
    """Answer from the configured local evidence corpus."""
    try:
        return get_qa_service().ask(request.question).to_dict()
    except Exception as exc:
        # Do not expose provider details or credentials through the API.
        from fastapi import HTTPException

        raise HTTPException(status_code=502, detail="LLM provider request failed") from exc
