"""Evidence-grounded Q&A over the existing BM25 retrieval index."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from app.llm import create_llm, qa_prompt
from app.retrieval import BM25Retriever, RetrievalResult, tokenize


NOT_FOUND = "Information not found in the provided document"


class LLMInvocationError(RuntimeError):
    """The configured provider could not complete an answer request."""
_SCOPE_WORDS = {"standalone", "consolidated", "group", "company", "parent"}
_STOPWORDS = {"a", "an", "and", "are", "at", "by", "for", "from", "how", "in", "is", "of", "on", "the", "their", "to", "was", "what", "were", "with"}
_GENERIC_TERMS = {"amount", "date", "ended", "march", "value", "year"}
_SCOPE_RANGES = (set(range(131, 136)), set(range(227, 233)))


class LLM(Protocol):
    def invoke(self, input: Any) -> Any: ...


@dataclass(frozen=True)
class Citation:
    text: str
    pages: list[int]


@dataclass(frozen=True)
class QAResponse:
    answer: str
    excerpts: list[Citation]

    def to_dict(self) -> dict[str, Any]:
        return {"answer": self.answer, "excerpts": [{"text": e.text, "pages": e.pages} for e in self.excerpts]}


def _content_tokens(text: str) -> set[str]:
    return set(tokenize(text)) - _STOPWORDS


def _has_relevant_overlap(question: str, results: list[RetrievalResult]) -> bool:
    question_tokens = _content_tokens(question)
    evidence_tokens = set().union(*(_content_tokens(result.chunk.text) for result in results)) if results else set()
    matched = question_tokens & evidence_tokens
    unmatched = (question_tokens - evidence_tokens) - _GENERIC_TERMS
    return bool(matched) and len(unmatched) <= 1


def _is_scope_ambiguous(question: str, results: list[RetrievalResult]) -> bool:
    if _SCOPE_WORDS.intersection(_content_tokens(question)):
        return False
    question_tokens = _content_tokens(question)
    if not question_tokens.intersection({"revenue", "assets", "income", "profit", "cash", "equity", "liabilities"}):
        return False
    scopes = []
    for result in results:
        pages = set(result.chunk.source_pages)
        scopes.extend(index for index, page_range in enumerate(_SCOPE_RANGES) if pages & page_range)
    return 0 in scopes and 1 in scopes


def _compact_excerpt(chunk: Any, question: str, max_chars: int = 2200) -> list[str]:
    """Keep exact, query-relevant table lines while bounding prompt size."""
    raw_lines = [line for line in (chunk.raw_excerpt or chunk.text).splitlines() if line.strip()]
    if not raw_lines:
        return []
    if chunk.kind != "financial_table":
        return raw_lines[:1]
    query_tokens = _content_tokens(question)
    selected_indices = {index for index, line in enumerate(raw_lines[:2])}
    selected_indices.update(
        index for index, line in enumerate(raw_lines) if query_tokens.intersection(_content_tokens(line))
    )
    selected: list[str] = []
    current_size = 0
    for index, line in enumerate(raw_lines):
        if index not in selected_indices:
            continue
        if current_size + len(line) + 1 > max_chars and index not in selected_indices.intersection(
            {i for i, candidate in enumerate(raw_lines) if query_tokens.intersection(_content_tokens(candidate))}
        ):
            continue
        selected.append(line)
        current_size += len(line) + 1
    return selected


def _evidence_payload(results: list[RetrievalResult], question: str) -> str:
    payload = []
    for result in results:
        chunk = result.chunk
        exact_lines = _compact_excerpt(chunk, question)
        payload.append({
            "chunk_id": chunk.chunk_id,
            "text": chunk.text if chunk.kind != "financial_table" else chunk.text[:600],
            "exact_excerpt_lines": exact_lines,
            "pdf_pages": chunk.source_pages,
        })
    return json.dumps(payload, ensure_ascii=False)


def _message_text(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, list):
        return "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
    return str(content)


def _parse_response(raw: Any) -> dict[str, Any] | None:
    text = _message_text(raw).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _answer_claim_tokens(answer: str) -> set[str]:
    """Return claims that can be checked mechanically: figures, years, units and scope."""
    numeric_claims = set(re.findall(r"(?<![A-Za-z])(?:\(?\d[\d,]*(?:\.\d+)?\)?)(?![A-Za-z])", answer))
    lowered = answer.casefold()
    scope_claims = {word for word in _SCOPE_WORDS if re.search(rf"\b{re.escape(word)}\b", lowered)}
    unit_claims = {word for word in ("million", "billion", "percent", "%") if word in lowered}
    return {claim.casefold() for claim in numeric_claims | scope_claims | unit_claims}


def validate_citations(answer: str, excerpts: list[dict[str, Any]], results: list[RetrievalResult]) -> list[Citation] | None:
    """Validate exact excerpt text and page claims against retrieved stored evidence."""
    if answer == NOT_FOUND:
        return []
    valid: list[Citation] = []
    for item in excerpts:
        if not isinstance(item, dict) or not isinstance(item.get("text"), str) or not isinstance(item.get("pages"), list):
            return None
        text = item["text"]
        pages = item["pages"]
        if not text.strip() or not pages or not all(isinstance(page, int) for page in pages):
            return None
        matched = False
        for result in results:
            stored = result.chunk.raw_excerpt or result.chunk.text
            if text in stored and set(pages).issubset(set(result.chunk.source_pages)):
                matched = True
                break
        if not matched:
            return None
        valid.append(Citation(text=text, pages=pages))
    if not valid:
        return None
    cited_text = " ".join(
        result.chunk.text
        for result in results
        if any(
            citation.text in (result.chunk.raw_excerpt or result.chunk.text)
            and set(citation.pages).issubset(set(result.chunk.source_pages))
            for citation in valid
        )
    ).casefold()
    if any(claim not in cited_text for claim in _answer_claim_tokens(answer)):
        return None
    return valid


class QAService:
    def __init__(self, retriever: BM25Retriever, llm: LLM | None = None, top_k: int = 5) -> None:
        self.retriever = retriever
        self.llm = llm or create_llm()
        self.top_k = top_k
        self._prompt = qa_prompt()

    def ask(self, question: str) -> QAResponse:
        results = self.retriever.search(question, top_k=self.top_k)
        if not question.strip() or not results or not _has_relevant_overlap(question, results) or _is_scope_ambiguous(question, results):
            return QAResponse(NOT_FOUND, [])
        prompt_value = self._prompt.invoke({"question": question, "evidence": _evidence_payload(results, question)})
        try:
            raw_response = self.llm.invoke(prompt_value)
        except Exception as exc:
            raise LLMInvocationError("LLM provider invocation failed") from exc
        parsed = _parse_response(raw_response)
        if not parsed or not isinstance(parsed.get("answer"), str):
            return QAResponse(NOT_FOUND, [])
        answer = parsed["answer"].strip()
        if answer == NOT_FOUND:
            return QAResponse(NOT_FOUND, [])
        excerpts = parsed.get("excerpts")
        citations = validate_citations(answer, excerpts, results) if isinstance(excerpts, list) else None
        if citations is None:
            return QAResponse(NOT_FOUND, [])
        return QAResponse(answer, citations)
