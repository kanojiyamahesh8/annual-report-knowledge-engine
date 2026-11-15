"""Explicit PyMuPDF extraction models for audit-friendly PDF evidence."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Iterable

import fitz


PPE_COLUMNS = [
    "Particulars",
    "Freehold land",
    "Leasehold improvements",
    "Building",
    "Plant and equipments",
    "Electrical installations",
    "Computers",
    "Office equipments",
    "Furniture and fixtures",
    "Vehicles",
    "Leasehold land",
    "Total",
]
PPE_GROUPS = {
    "Gross block (at cost/deemed cost)": PPE_COLUMNS,
    "Accumulated depreciation": PPE_COLUMNS,
    "Net block": PPE_COLUMNS,
}
_YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")


def _clean_cell(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split())


def _header_key(row: Iterable[str]) -> tuple[str, ...]:
    return tuple(_clean_cell(cell).casefold() for cell in row)


def _normalized_label(value: str) -> str:
    return " ".join(_clean_cell(value).casefold().split())


def _year_columns(headers: list[str]) -> dict[str, int]:
    """Map each explicitly printed year to its table column index."""
    columns: dict[str, int] = {}
    for index, header in enumerate(headers):
        for year in _YEAR_PATTERN.findall(header):
            columns.setdefault(year, index)
    return columns


def _table_cells(
    headers: list[str],
    rows: list[list[str]],
    semantic_headers: list[str] | None = None,
    raw_excerpt: str = "",
    row_pages: list[int] | None = None,
) -> list[dict[str, Any]]:
    """Create auditable row/column/value records without changing raw rows."""
    cells: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        if not row:
            continue
        row_label = row[0]
        cell_pages = (
            [row_pages[row_index]]
            if row_pages is not None and row_index < len(row_pages)
            else []
        )
        for index, value in enumerate(row[1:], start=1):
            if index >= len(headers):
                continue
            cells.append(
                {
                    "row_label": row_label,
                    "column_label": headers[index],
                    "column_index": index,
                    "value": value,
                    "pdf_pages": cell_pages,
                }
            )
    # PyMuPDF can transpose complex grouped tables. Preserve an explicit
    # semantic PPE total when the extractor has already identified that schema.
    if semantic_headers == PPE_COLUMNS and "Net block" in raw_excerpt:
        tail = raw_excerpt[raw_excerpt.casefold().find("net block") :]
        values = re.findall(r"(?<![A-Za-z])\(?\d[\d,]*(?:\.\d+)?\)?", tail)
        if values:
            cells.append({
                "row_label": "Net block",
                "column_label": "Total",
                "column_index": len(PPE_COLUMNS) - 1,
                "value": values[0],
                "pdf_pages": sorted(set(row_pages or [])),
            })
    return cells


def _annotate_cells(
    cells: list[dict[str, Any]],
    table_id: str,
    source_pages: list[int],
    section: str | None,
    scope: str | None,
) -> list[dict[str, Any]]:
    """Attach stable provenance to every cell without changing its value mapping."""
    return [
        {
            **cell,
            "table_id": table_id,
            "pdf_pages": cell.get("pdf_pages") or list(source_pages),
            "section": section,
            "scope": scope,
        }
        for cell in cells
    ]


def resolve_table_cell(
    table: "FinancialTable", row_label: str, column_label: str
) -> dict[str, Any] | None:
    """Resolve one exact row/column pair; return None when it is missing or ambiguous."""
    wanted_row = _normalized_label(row_label)
    wanted_column = _normalized_label(column_label)
    matches = [
        cell
        for cell in table.cells
        if _normalized_label(str(cell["row_label"])) == wanted_row
        and (
            _normalized_label(str(cell["column_label"])) == wanted_column
            or (
                wanted_column in _year_columns([str(cell["column_label"])])
                and wanted_column in _normalized_label(str(cell["column_label"]))
            )
        )
    ]
    return matches[0] if len(matches) == 1 else None


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
    section: str | None = None
    scope: str | None = None

    @property
    def headers(self) -> list[str]:
        return _normalized_headers(self.rows)[0]

    @property
    def data_rows(self) -> list[list[str]]:
        return _normalized_headers(self.rows)[1]

    @property
    def semantic_headers(self) -> list[str]:
        if self.rows and any(
            "Gross block (at cost/deemed cost)" in cell for cell in self.rows[0]
        ):
            return PPE_COLUMNS
        return self.headers

    @property
    def semantic_groups(self) -> dict[str, list[str]]:
        if self.semantic_headers == PPE_COLUMNS:
            return PPE_GROUPS
        return {}


@dataclass
class FinancialTable:
    table_id: str
    source_pages: list[int]
    headers: list[str]
    rows: list[list[str]]
    raw_excerpts: list[str]
    unit: str | None = None
    title: str | None = None
    semantic_headers: list[str] | None = None
    semantic_groups: dict[str, list[str]] = field(default_factory=dict)
    section: str | None = None
    scope: str | None = None
    year_columns: dict[str, int] = field(default_factory=dict)
    row_labels: list[str] = field(default_factory=list)
    cells: list[dict[str, Any]] = field(default_factory=list)

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
            "semantic_headers": self.semantic_headers or self.headers,
            "semantic_groups": self.semantic_groups,
            "section": self.section,
            "scope": self.scope,
            "year_columns": self.year_columns,
            "row_labels": self.row_labels,
            "cells": self.cells,
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


def _infer_section(text: str) -> str | None:
    for line in (line.strip() for line in text.splitlines() if line.strip()):
        lowered = line.casefold()
        if any(term in lowered for term in ("balance sheet", "statement of profit", "cash flows", "notes to")):
            return line[:160]
    return None


def _infer_scope(text: str) -> str | None:
    lowered = text.casefold()
    if "consolidated" in lowered:
        return "consolidated"
    if "standalone" in lowered:
        return "standalone"
    return None


def _normalized_headers(rows: list[list[str]]) -> tuple[list[str], list[list[str]]]:
    """Combine obvious two-row grouped headers without discarding raw rows."""
    if len(rows) < 2:
        return (rows[0] if rows else []), (rows[1:] if rows else [])
    first, second = rows[0], rows[1]
    first_label = first[0].casefold() if first else ""
    grouped_marker = (
        first_label in {"particulars", "name of shareholder", "name of promoter"}
        or "outstanding" in first_label
    )
    if not grouped_marker or second[0] or sum(bool(cell) for cell in second) < 2:
        return first, rows[1:]

    headers: list[str] = []
    for parent, child in zip(first, second):
        parent = _clean_cell(parent)
        child = _clean_cell(child)
        headers.append(f"{parent} / {child}" if parent and child else parent or child)
    return headers, rows[2:]


def _page_may_contain_table(text: str) -> bool:
    """Cheap candidate filter to avoid find_tables() on narrative-only pages."""
    lowered = text.casefold()
    if "particulars" in lowered or "in million" in lowered:
        return True
    has_year_columns = "march 31, 2026" in lowered and "march 31, 2025" in lowered
    numeric_tokens = re.findall(r"\b\d[\d,]*(?:\.\d+)?\b", text)
    return has_year_columns and len(numeric_tokens) >= 12 and "total" in lowered


def _extract_page_table_fragments_batch(
    arguments: tuple[str, list[int]],
) -> list[TableFragment]:
    """Extract a page batch with one isolated PyMuPDF document per worker."""
    source_path, page_numbers = arguments
    document = fitz.open(source_path)
    fragments: list[TableFragment] = []
    for page_number in page_numbers:
        page = document[page_number - 1]
        page_text = page.get_text("text")
        for table in page.find_tables().tables:
            rows = _table_rows(table)
            if rows:
                fragments.append(
                    TableFragment(
                        pdf_page_number=page_number,
                        rows=rows,
                        raw_excerpt=_raw_excerpt(rows),
                        section=_infer_section(page_text),
                        scope=_infer_scope(page_text),
                    )
                )
    document.close()
    return fragments


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
    current_row_pages: list[int] = []
    current_pages: list[int] = []
    current_excerpts: list[str] = []
    current_id = 0

    def flush() -> None:
        nonlocal current_fragment, current_rows, current_row_pages, current_pages, current_excerpts, current_id
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
                semantic_headers=current_fragment.semantic_headers,
                semantic_groups=current_fragment.semantic_groups,
                section=current_fragment.section,
                scope=current_fragment.scope,
                year_columns=_year_columns(current_fragment.headers),
                row_labels=[row[0] for row in current_rows if row],
                cells=_annotate_cells(
                    _table_cells(
                        current_fragment.headers,
                        current_rows,
                        current_fragment.semantic_headers,
                        "\n".join(current_excerpts),
                        current_row_pages,
                    ),
                    f"table-{current_id:04d}",
                    current_pages,
                    current_fragment.section,
                    current_fragment.scope,
                ),
            )
        )
        current_fragment = None
        current_rows = []
        current_row_pages = []
        current_pages = []
        current_excerpts = []

    for fragment in ordered:
        if current_fragment is None:
            current_fragment = fragment
            current_rows = list(fragment.data_rows)
            current_row_pages = [fragment.pdf_page_number] * len(fragment.data_rows)
            current_pages = [fragment.pdf_page_number]
            current_excerpts = [fragment.raw_excerpt]
        elif _stitchable(current_fragment, fragment):
            current_rows.extend(fragment.data_rows)
            current_row_pages.extend([fragment.pdf_page_number] * len(fragment.data_rows))
            current_pages.append(fragment.pdf_page_number)
            current_excerpts.append(fragment.raw_excerpt)
        else:
            flush()
            current_fragment = fragment
            current_rows = list(fragment.data_rows)
            current_row_pages = [fragment.pdf_page_number] * len(fragment.data_rows)
            current_pages = [fragment.pdf_page_number]
            current_excerpts = [fragment.raw_excerpt]
    flush()
    return stitched


def extract_document(
    pdf_path: str | Path,
    page_numbers: Iterable[int] | None = None,
    table_workers: int | None = None,
) -> ExtractedDocument:
    """Extract page text and tables locally with PyMuPDF only."""
    source = Path(pdf_path)
    document = fitz.open(source)
    page_count = document.page_count
    selected_pages = (
        list(range(1, document.page_count + 1))
        if page_numbers is None
        else sorted(set(page_numbers))
    )
    invalid_pages = [
        page_number
        for page_number in selected_pages
        if page_number < 1 or page_number > page_count
    ]
    if invalid_pages:
        raise ValueError(f"Page numbers out of range: {invalid_pages}")
    pages: list[ExtractedPage] = []
    candidate_pages: list[int] = []

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
        if _page_may_contain_table(text):
            candidate_pages.append(page_number)

    document.close()
    workers = table_workers if table_workers is not None else (4 if page_numbers is None else 1)
    if workers < 1:
        raise ValueError("table_workers must be at least 1")
    if not candidate_pages:
        fragments: list[TableFragment] = []
    elif workers == 1:
        fragments = _extract_page_table_fragments_batch((str(source), candidate_pages))
    else:
        chunks = [candidate_pages[index::workers] for index in range(workers)]
        chunks = [chunk for chunk in chunks if chunk]
        arguments = [(str(source), chunk) for chunk in chunks]
        with ProcessPoolExecutor(max_workers=workers) as pool:
            fragment_groups = pool.map(_extract_page_table_fragments_batch, arguments)
            fragments = [fragment for group in fragment_groups for fragment in group]

    return ExtractedDocument(
        source_path=str(source),
        page_count=page_count,
        pages=pages,
        tables=stitch_table_fragments(fragments),
    )
