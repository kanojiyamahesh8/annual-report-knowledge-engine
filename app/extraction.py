"""Explicit PyMuPDF extraction models for audit-friendly PDF evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Iterable

import fitz


def _clean_cell(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split())


def _header_key(row: Iterable[str]) -> tuple[str, ...]:
    return tuple(_clean_cell(cell).casefold() for cell in row)


def _find_printed_page_number(text: str) -> int | None:
    """Return a nearby printed page label when it is explicitly extractable."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in [*lines[:10], *lines[-10:]]:
        if re.fullmatch(r"\d{1,4}", line):
            return int(line)
    return None


@dataclass(frozen=True)
class ExtractedPage:
    pdf_page_number: int
    printed_page_number: int | None
    text: str

    def to_dict(self) -> dict[str, object]:
        return {
            "pdf_page_number": self.pdf_page_number,
            "printed_page_number": self.printed_page_number,
            "text": self.text,
        }


@dataclass
class TableFragment:
    pdf_page_number: int
    rows: list[list[str]]
    raw_excerpt: str
    unit: str | None = None
    title: str | None = None

    @property
    def headers(self) -> list[str]:
        return self.rows[0] if self.rows else []

    @property
    def data_rows(self) -> list[list[str]]:
        return self.rows[1:] if self.rows else []


@dataclass
class FinancialTable:
    table_id: str
    source_pages: list[int]
    headers: list[str]
    rows: list[list[str]]
    raw_excerpts: list[str]
    unit: str | None = None
    title: str | None = None

    @property
    def raw_excerpt(self) -> str:
        return "\n".join(self.raw_excerpts)

    def to_dict(self) -> dict[str, object]:
        return {
            "table_id": self.table_id,
            "source_pages": self.source_pages,
            "headers": self.headers,
            "rows": self.rows,
            "raw_excerpts": self.raw_excerpts,
            "unit": self.unit,
            "title": self.title,
        }


@dataclass
class ExtractedDocument:
    source_path: str
    page_count: int
    pages: list[ExtractedPage] = field(default_factory=list)
    tables: list[FinancialTable] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "source_path": self.source_path,
            "page_count": self.page_count,
            "pages": [page.to_dict() for page in self.pages],
            "tables": [table.to_dict() for table in self.tables],
        }

    def write_json(self, output_path: str | Path) -> Path:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return destination


def _table_rows(table: Any) -> list[list[str]]:
    return [[_clean_cell(cell) for cell in row] for row in (table.extract() or [])]


def _raw_excerpt(rows: list[list[str]]) -> str:
    return "\n".join(" | ".join(row) for row in rows)


def _stitchable(previous: TableFragment, current: TableFragment) -> bool:
    return (
        current.pdf_page_number == previous.pdf_page_number + 1
        and bool(previous.headers)
        and _header_key(previous.headers) == _header_key(current.headers)
    )


def stitch_table_fragments(fragments: Iterable[TableFragment]) -> list[FinancialTable]:
    """Stitch consecutive fragments only when their extracted headers repeat."""
    ordered = sorted(fragments, key=lambda fragment: fragment.pdf_page_number)
    stitched: list[FinancialTable] = []
    current_fragment: TableFragment | None = None
    current_rows: list[list[str]] = []
    current_pages: list[int] = []
    current_excerpts: list[str] = []
    current_id = 0

    def flush() -> None:
        nonlocal current_fragment, current_rows, current_pages, current_excerpts, current_id
        if current_fragment is None:
            return
        current_id += 1
        stitched.append(
            FinancialTable(
                table_id=f"table-{current_id:04d}",
                source_pages=current_pages,
                headers=current_fragment.headers,
                rows=current_rows,
                raw_excerpts=current_excerpts,
                unit=current_fragment.unit,
                title=current_fragment.title,
            )
        )
        current_fragment = None
        current_rows = []
        current_pages = []
        current_excerpts = []

    for fragment in ordered:
        if current_fragment is None:
            current_fragment = fragment
            current_rows = list(fragment.data_rows)
            current_pages = [fragment.pdf_page_number]
            current_excerpts = [fragment.raw_excerpt]
        elif _stitchable(current_fragment, fragment):
            current_rows.extend(fragment.data_rows)
            current_pages.append(fragment.pdf_page_number)
            current_excerpts.append(fragment.raw_excerpt)
        else:
            flush()
            current_fragment = fragment
            current_rows = list(fragment.data_rows)
            current_pages = [fragment.pdf_page_number]
            current_excerpts = [fragment.raw_excerpt]
    flush()
    return stitched


def extract_document(
    pdf_path: str | Path,
    page_numbers: Iterable[int] | None = None,
) -> ExtractedDocument:
    """Extract page text and tables locally with PyMuPDF only."""
    source = Path(pdf_path)
    document = fitz.open(source)
    selected_pages = (
        list(range(1, document.page_count + 1))
        if page_numbers is None
        else sorted(set(page_numbers))
    )
    invalid_pages = [
        page_number
        for page_number in selected_pages
        if page_number < 1 or page_number > document.page_count
    ]
    if invalid_pages:
        raise ValueError(f"Page numbers out of range: {invalid_pages}")
    pages: list[ExtractedPage] = []
    fragments: list[TableFragment] = []

    for page_number in selected_pages:
        page = document[page_number - 1]
        text = page.get_text("text")
        pages.append(
            ExtractedPage(
                pdf_page_number=page_number,
                printed_page_number=_find_printed_page_number(text),
                text=text,
            )
        )
        for table in page.find_tables().tables:
            rows = _table_rows(table)
            if rows:
                fragments.append(
                    TableFragment(
                        pdf_page_number=page_number,
                        rows=rows,
                        raw_excerpt=_raw_excerpt(rows),
                    )
                )

    return ExtractedDocument(
        source_path=str(source),
        page_count=document.page_count,
        pages=pages,
        tables=stitch_table_fragments(fragments),
    )
