from pathlib import Path

import fitz

from app.extraction import extract_document


PDF_PATH = Path("documents/Centum_Annual_Report.pdf")


def _pdf_rows(page_number: int, needle: str) -> list[list[str]]:
    document = fitz.open(PDF_PATH)
    rows: list[list[str]] = []
    for table in document[page_number - 1].find_tables().tables:
        for row in table.extract() or []:
            cleaned = [str(cell or "").replace("\n", " ").strip() for cell in row]
            if needle.casefold() in " ".join(cleaned).casefold():
                rows.append(cleaned)
    return rows


def _extracted_rows(document, needle: str) -> list[list[str]]:
    return [
        row
        for table in document.tables
        for row in table.rows
        if needle.casefold() in " ".join(row).casefold()
    ]


def test_standalone_financial_figures_match_pdf_tables() -> None:
    extracted = extract_document(PDF_PATH, [131, 132, 133])

    for page_number, needle in [
        (131, "Total assets"),
        (132, "Revenue from operations"),
        (133, "Cash and cash equivalents at the end of the year"),
    ]:
        pdf_rows = _pdf_rows(page_number, needle)
        extracted_rows = _extracted_rows(extracted, needle)
        assert pdf_rows
        assert extracted_rows
        assert extracted_rows[0] == pdf_rows[0]


def test_consolidated_financial_figures_match_pdf_tables() -> None:
    extracted = extract_document(PDF_PATH, [227, 228, 229, 230])

    for page_number, needle in [
        (227, "Total assets"),
        (228, "Revenue from operations"),
        (229, "Cash and cash equivalents at the end of the year"),
    ]:
        pdf_rows = _pdf_rows(page_number, needle)
        extracted_rows = _extracted_rows(extracted, needle)
        assert pdf_rows
        assert extracted_rows
        assert extracted_rows[0] == pdf_rows[0]
