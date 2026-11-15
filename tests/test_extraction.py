from app.extraction import (
    ExtractedDocument,
    ExtractedPage,
    FinancialTable,
    TableFragment,
    resolve_table_cell,
    stitch_table_fragments,
)


def test_stitches_repeated_header_across_pages() -> None:
    fragments = [
        TableFragment(
            pdf_page_number=161,
            rows=[
                ["Particulars", "2026", "2025"],
                ["Trade receivables", "100.00", "90.00"],
            ],
            raw_excerpt="Particulars | 2026 | 2025\nTrade receivables | 100.00 | 90.00",
        ),
        TableFragment(
            pdf_page_number=162,
            rows=[
                ["Particulars", "2026", "2025"],
                ["Other receivables", "25.00", "20.00"],
            ],
            raw_excerpt="Particulars | 2026 | 2025\nOther receivables | 25.00 | 20.00",
        ),
    ]

    tables = stitch_table_fragments(fragments)

    assert len(tables) == 1
    assert tables[0].source_pages == [161, 162]
    assert tables[0].headers == ["Particulars", "2026", "2025"]
    assert tables[0].rows == [
        ["Trade receivables", "100.00", "90.00"],
        ["Other receivables", "25.00", "20.00"],
    ]
    first_row_cells = [cell for cell in tables[0].cells if cell["row_label"] == "Trade receivables"]
    second_row_cells = [cell for cell in tables[0].cells if cell["row_label"] == "Other receivables"]
    assert all(cell["pdf_pages"] == [161] for cell in first_row_cells)
    assert all(cell["pdf_pages"] == [162] for cell in second_row_cells)
    assert "Trade receivables" in tables[0].raw_excerpt
    assert "Other receivables" in tables[0].raw_excerpt


def test_does_not_merge_unrelated_or_nonconsecutive_tables() -> None:
    fragments = [
        TableFragment(1, [["Item", "2026"], ["A", "1"]], "A"),
        TableFragment(2, [["Different", "2026"], ["B", "2"]], "B"),
        TableFragment(4, [["Item", "2026"], ["C", "3"]], "C"),
    ]

    tables = stitch_table_fragments(fragments)

    assert len(tables) == 3
    assert [table.source_pages for table in tables] == [[1], [2], [4]]


def test_evidence_serialization_preserves_pages_tables_and_raw_excerpt(tmp_path) -> None:
    document = ExtractedDocument(
        source_path="documents/report.pdf",
        page_count=10,
        pages=[ExtractedPage(3, 26, "Balance Sheet")],
        tables=[
            FinancialTable(
                table_id="table-0001",
                source_pages=[3, 4],
                headers=["Particulars", "2026"],
                rows=[["Cash", "100.00"]],
                raw_excerpts=["Particulars | 2026\nCash | 100.00"],
                unit="INR million",
            )
        ],
    )

    output = document.write_json(tmp_path / "evidence.json")
    payload = output.read_text(encoding="utf-8")

    assert '"page_count": 10' in payload
    assert '"source_pages": [\n        3,\n        4\n      ]' in payload
    assert "Cash | 100.00" in payload


def test_cell_resolution_supports_year_alias_and_rejects_duplicate_columns() -> None:
    table = FinancialTable(
        table_id="table-0002",
        source_pages=[7],
        headers=["Particulars", "As at March 31, 2026", "As at March 31, 2025"],
        rows=[["Total", "100.00", "90.00"]],
        raw_excerpts=["Particulars | As at March 31, 2026 | As at March 31, 2025\nTotal | 100.00 | 90.00"],
        year_columns={"2026": 1, "2025": 2},
        row_labels=["Total"],
        cells=[
            {"row_label": "Total", "column_label": "As at March 31, 2026", "value": "100.00"},
            {"row_label": "Total", "column_label": "As at March 31, 2025", "value": "90.00"},
        ],
    )

    assert resolve_table_cell(table, "Total", "2026")["value"] == "100.00"
    table.cells.append({"row_label": "Total", "column_label": "2026", "value": "ambiguous"})
    assert resolve_table_cell(table, "Total", "2026") is None
