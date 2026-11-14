"""FastAPI application for the annual-report Q&A service."""

from functools import lru_cache
from datetime import datetime, timezone
import logging
import json
import os
from pathlib import Path
import re
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator

from app.config import settings
from app.llm import LLMConfigurationError
from app.qa import LLMInvocationError, QAService
from app.retrieval import BM25Retriever, load_evidence


class JsonFormatter(logging.Formatter):
    """Compact JSON logs with only operational, non-sensitive fields."""

    _FIELDS = ("request_id", "method", "path", "status_code", "latency_ms", "result", "failure")

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for field in self._FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False)


logger = logging.getLogger("annual_report")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
logger.propagate = False


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


class ProviderConfigurationError(RuntimeError):
    """The configured provider cannot be initialized."""


class RuntimeInitializationError(RuntimeError):
    """Unexpected service initialization failure."""


_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class CitationResponse(BaseModel):
    text: str
    pages: list[int]


class AskResponse(BaseModel):
    answer: str
    excerpts: list[CitationResponse]


class ReadyResponse(BaseModel):
    status: str
    evidence_path: str
    page_count: int
    indexed_pages: int
    table_count: int


class ErrorResponse(BaseModel):
    detail: str


@lru_cache(maxsize=1)
def load_configured_evidence() -> dict:
    evidence_path = Path(settings.evidence_path)
    if not evidence_path.is_absolute():
        evidence_path = Path(__file__).resolve().parent.parent / evidence_path
    try:
        return load_evidence(evidence_path)
    except (OSError, ValueError, TypeError) as exc:
        raise EvidenceConfigurationError("Configured evidence corpus is unavailable") from exc


@lru_cache(maxsize=1)
def get_qa_service() -> QAService:
    try:
        retriever = BM25Retriever.from_evidence(load_configured_evidence())
    except EvidenceConfigurationError:
        raise
    except (ValueError, TypeError) as exc:
        raise EvidenceConfigurationError("Configured evidence corpus is unavailable") from exc
    try:
        return QAService(retriever)
    except LLMConfigurationError as exc:
        raise ProviderConfigurationError("Configured LLM provider is unavailable") from exc
    except Exception as exc:
        raise RuntimeInitializationError("Q&A service initialization failed") from exc


app = FastAPI(title="Provider-Agnostic Annual Report Knowledge Engine")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


def _request_id(request: Request) -> str:
    candidate = request.headers.get("X-Request-ID", "")
    return candidate if _REQUEST_ID_PATTERN.fullmatch(candidate) else uuid4().hex


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = _request_id(request)
    started = perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    logger.info(
        "http_request_completed",
        extra={
            "request_id": request.state.request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": round((perf_counter() - started) * 1000, 2),
        },
    )
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    response = JSONResponse(status_code=422, content={"detail": "Invalid request"})
    response.headers["X-Request-ID"] = getattr(request.state, "request_id", uuid4().hex)
    return response


def _request_error(status_code: int, detail: str, request_id: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail, headers={"X-Request-ID": request_id})


@app.get("/", response_class=HTMLResponse)
def homepage(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", response_model=ReadyResponse)
def readiness() -> ReadyResponse:
    try:
        get_qa_service()
        evidence = load_configured_evidence()
    except EvidenceConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Evidence corpus unavailable") from exc
    except ProviderConfigurationError as exc:
        raise HTTPException(status_code=503, detail="LLM provider unavailable") from exc
    except RuntimeInitializationError as exc:
        raise HTTPException(status_code=503, detail="Service initialization failed") from exc
    return ReadyResponse(
        status="ready",
        evidence_path=settings.evidence_path,
        page_count=int(evidence.get("page_count", 0)),
        indexed_pages=len(evidence.get("pages", [])),
        table_count=len(evidence.get("tables", [])),
    )


@app.post("/api/ask", response_model=AskResponse, responses={422: {"model": ErrorResponse, "description": "Invalid request"}, 502: {"model": ErrorResponse, "description": "Provider unavailable"}, 503: {"model": ErrorResponse, "description": "Evidence or service unavailable"}, 500: {"model": ErrorResponse, "description": "Internal server error"}})
def ask(request: AskRequest, response: Response, http_request: Request) -> AskResponse:
    """Answer from the configured local evidence corpus."""
    request_id = getattr(http_request.state, "request_id", uuid4().hex)
    response.headers["X-Request-ID"] = request_id
    started = perf_counter()
    try:
        service = get_qa_service()
    except EvidenceConfigurationError as exc:
        logger.error("qa_request_failed", extra={"request_id": request_id, "failure": "evidence", "latency_ms": round((perf_counter() - started) * 1000, 2)})
        raise HTTPException(status_code=503, detail="Evidence corpus unavailable") from exc
    except ProviderConfigurationError as exc:
        logger.error("qa_request_failed", extra={"request_id": request_id, "failure": "provider_configuration", "latency_ms": round((perf_counter() - started) * 1000, 2)})
        raise HTTPException(status_code=503, detail="LLM provider unavailable") from exc
    except RuntimeInitializationError as exc:
        logger.error("qa_request_failed", extra={"request_id": request_id, "failure": "initialization", "latency_ms": round((perf_counter() - started) * 1000, 2)})
        raise _request_error(500, "Service initialization failed", request_id) from exc
    try:
        result = service.ask(request.question)
        payload = result.to_dict()
        logger.info("qa_request_completed", extra={"request_id": request_id, "result": "answered" if payload["answer"] != "Information not found in the provided document" else "not_found", "latency_ms": round((perf_counter() - started) * 1000, 2)})
        return payload
    except LLMInvocationError as exc:
        logger.error("qa_request_failed", extra={"request_id": request_id, "failure": "provider_invocation", "latency_ms": round((perf_counter() - started) * 1000, 2)})
        raise _request_error(502, "LLM provider request failed", request_id) from exc
    except Exception as exc:
        logger.exception("qa_request_internal_error", extra={"request_id": request_id, "latency_ms": round((perf_counter() - started) * 1000, 2)})
        raise _request_error(500, "Internal server error", request_id) from exc
