"""FastAPI application for the annual-report Q&A service."""

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator

from app.config import settings
from app.qa import QAService
from app.retrieval import BM25Retriever, load_evidence


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("question must not be blank")
        return normalized


class EvidenceConfigurationError(RuntimeError):
    """The configured local evidence corpus cannot be loaded or indexed."""


@lru_cache(maxsize=1)
def get_qa_service() -> QAService:
    evidence_path = Path(settings.evidence_path)
    if not evidence_path.is_absolute():
        evidence_path = Path(__file__).resolve().parent.parent / evidence_path
    try:
        evidence = load_evidence(evidence_path)
        retriever = BM25Retriever.from_evidence(evidence)
    except (OSError, ValueError, TypeError) as exc:
        raise EvidenceConfigurationError("Configured evidence corpus is unavailable") from exc
    return QAService(retriever)


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
        service = get_qa_service()
    except EvidenceConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Evidence corpus unavailable") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="LLM provider request failed") from exc
    try:
        return service.ask(request.question).to_dict()
    except Exception as exc:
        # Do not expose provider details or credentials through the API.
        raise HTTPException(status_code=502, detail="LLM provider request failed") from exc
