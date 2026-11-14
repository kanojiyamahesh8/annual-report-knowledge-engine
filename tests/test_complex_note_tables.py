from pathlib import Path

from app.extraction import extract_document


PDF_PATH = Path("documents/Centum_Annual_Report.pdf")


def _table_with_pages(document, pages: list[int], header_size: int):
    return next(
        table
        for table in document.tables
        if table.source_pages == pages and len(table.headers) == header_size
    )


def test_ppe_grouped_headers_and_units_are_retained_in_raw_evidence() -> None:
    document = extract_document(PDF_PATH, [155])
    table = document.tables[0]
    page_text = document.pages[0].text

    assert len(table.headers) == 23
    assert "Gross block" in table.headers[1]
    assert "As at April 01, 2024" in table.headers[2]
    assert table.semantic_headers[1:4] == ["Freehold land", "Leasehold improvements", "Building"]
    assert table.semantic_headers[-1] == "Total"
    assert set(table.semantic_groups) == {
        "Gross block (at cost/deemed cost)",
        "Accumulated depreciation",
        "Net block",
    }
    assert "in million" in page_text
    assert "As at March 31, 2026" in table.raw_excerpt
    assert "1,337.25" in table.raw_excerpt


def test_ageing_table_preserves_year_values_and_continuity() -> None:
    document = extract_document(PDF_PATH, [161, 162])
    table = _table_with_pages(document, [161, 162], 9)

    assert table.source_pages == [161, 162]
    assert table.headers[0] == "Particulars"
    assert table.headers[3].endswith("/ Less than 6 months")
    assert table.headers[-1] == "Total"
    receivables = next(row for row in table.rows if "considered good" in row[0])
    assert receivables[1:3] == ["13.65", "1,981.72"]
    assert receivables[-1] == "2,971.87"


def test_promoter_and_payables_tables_stitch_and_preserve_relationships() -> None:
    document = extract_document(PDF_PATH, [165, 166, 173, 174])
    promoter = _table_with_pages(document, [165, 166], 6)
    payables = _table_with_pages(document, [173, 174], 8)

    assert promoter.rows[0][0] == "Equity shares of ` 10 each fully paid"
    apparao = next(row for row in promoter.rows if "Apparao" in row[0])
    assert apparao[1:4] == ["58,97,549", "(6,66,000)", "52,31,549"]
    total = next(row for row in payables.rows if row[0] == "Total")
    assert total[-1] == "2,549.37"
    assert payables.headers[1].endswith("/ Unbilled dues")
    assert payables.source_pages == [173, 174]
