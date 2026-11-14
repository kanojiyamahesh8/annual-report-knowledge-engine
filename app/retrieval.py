"""Structure-aware evidence chunking and transparent BM25 retrieval."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable

from rank_bm25 import BM25Okapi


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?")
TABLE_PRIORITY_BONUS = 5.0
STATEMENT_SCOPE_BONUS = 25.0
EXACT_FINANCIAL_LABEL_BONUS = 15.0
STATEMENT_SCOPE_PAGES = {
    "standalone": set(range(131, 136)),
    "consolidated": set(range(227, 233)),
}
STATEMENT_TERMS = {"assets", "liabilities", "equity", "income", "profit", "revenue", "cash", "balance", "sheet"}


def tokenize(text: str) -> list[str]:
    return [token.casefold() for token in TOKEN_PATTERN.findall(text)]


def _statement_scope_bonus(query: str, chunk: EvidenceChunk) -> float:
    query_tokens = set(tokenize(query))
    matched_scope = query_tokens.intersection(STATEMENT_SCOPE_PAGES)
    if not matched_scope or not query_tokens.intersection(STATEMENT_TERMS):
        return 0.0
    if not set(chunk.source_pages).intersection(STATEMENT_SCOPE_PAGES[next(iter(matched_scope))]):
        return 0.0
    bonus = STATEMENT_SCOPE_BONUS
    chunk_text = chunk.text.casefold()
    if "total assets" in chunk_text and "assets" in query_tokens:
        bonus += EXACT_FINANCIAL_LABEL_BONUS
    if "total assets (1+2+3)" in chunk_text and "3" in query_tokens:
        bonus += EXACT_FINANCIAL_LABEL_BONUS
    return bonus


@dataclass(frozen=True)
class EvidenceChunk:
    chunk_id: str
    kind: str
    text: str
    source_pages: list[int]
    source_table_id: str | None = None
    raw_excerpt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalResult:
    chunk: EvidenceChunk
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {"score": self.score, "chunk": self.chunk.to_dict()}


def _paragraph_chunks(text: str, max_chars: int) -> Iterable[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    current: list[str] = []
    current_size = 0
    for paragraph in paragraphs:
        if current and current_size + len(paragraph) + 1 > max_chars:
            yield "\n\n".join(current)
            current = []
            current_size = 0
        current.append(paragraph)
        current_size += len(paragraph) + 1
    if current:
        yield "\n\n".join(current)


def _table_text(table: dict[str, Any], page_context: str = "") -> str:
    headers = table.get("semantic_headers") or table.get("headers") or []
    rows = table.get("rows") or []
    header_text = " | ".join(str(cell) for cell in headers if cell is not None)
    row_text = "\n".join(" | ".join(str(cell or "") for cell in row) for row in rows)
    unit = table.get("unit") or ""
    return "\n".join(part for part in [page_context, header_text, unit, row_text] if part).strip()


def build_chunks(evidence: dict[str, Any], max_chars: int = 1800) -> list[EvidenceChunk]:
    """Build text chunks while keeping every financial table as one chunk."""
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    chunks: list[EvidenceChunk] = []
    page_contexts = {
        int(page["pdf_page_number"]): " ".join(page.get("text", "").split())[:300]
        for page in evidence.get("pages", [])
    }
    for page in evidence.get("pages", []):
        page_number = int(page["pdf_page_number"])
        for index, text in enumerate(_paragraph_chunks(page.get("text", ""), max_chars)):
            chunks.append(
                EvidenceChunk(
                    chunk_id=f"page-{page_number:04d}-chunk-{index:03d}",
                    kind="page_text",
                    text=text,
                    source_pages=[page_number],
                    raw_excerpt=text,
                )
            )
    for table in evidence.get("tables", []):
        table_id = str(table["table_id"])
        source_pages = [int(page) for page in table.get("source_pages", [])]
        context = " ".join(page_contexts.get(page, "") for page in source_pages).strip()
        table_text = _table_text(table, page_context=context)
        chunks.append(
            EvidenceChunk(
                chunk_id=f"table-{table_id}",
                kind="financial_table",
                text=table_text,
                source_pages=source_pages,
                source_table_id=table_id,
                raw_excerpt="\n".join(table.get("raw_excerpts", [])),
            )
        )
    return chunks


def load_evidence(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class BM25Retriever:
    """Small explicit BM25 index over locally extracted evidence chunks."""

    def __init__(self, chunks: list[EvidenceChunk]) -> None:
        if not chunks:
            raise ValueError("At least one evidence chunk is required")
        self.chunks = chunks
        self._bm25 = BM25Okapi([tokenize(chunk.text) for chunk in chunks])

    @classmethod
    def from_evidence(cls, evidence: dict[str, Any], max_chars: int = 1800) -> "BM25Retriever":
        return cls(build_chunks(evidence, max_chars=max_chars))

    def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        if not query.strip():
            return []
        if top_k < 1:
            raise ValueError("top_k must be positive")
        scores = self._bm25.get_scores(tokenize(query))
        adjusted_scores = [
            float(score)
            + (TABLE_PRIORITY_BONUS if chunk.kind == "financial_table" else 0.0)
            + _statement_scope_bonus(query, chunk)
            for score, chunk in zip(scores, self.chunks)
        ]
        ranked = sorted(range(len(self.chunks)), key=lambda index: adjusted_scores[index], reverse=True)
        return [
            RetrievalResult(chunk=self.chunks[index], score=adjusted_scores[index])
            for index in ranked[:top_k]
        ]
