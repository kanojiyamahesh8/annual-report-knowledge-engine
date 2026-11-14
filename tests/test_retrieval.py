from app.retrieval import BM25Retriever, build_chunks


def _evidence() -> dict:
    return {
        "pages": [
            {"pdf_page_number": 10, "text": "Accounting policies and inventory valuation."},
            {"pdf_page_number": 11, "text": "Corporate governance and audit committee."},
            {"pdf_page_number": 12, "text": "Risk management and internal controls."},
        ],
        "tables": [
            {
                "table_id": "table-0001",
                "source_pages": [131],
                "semantic_headers": ["Particulars", "2026", "2025"],
                "rows": [["Total assets", "11,059.12", "11,204.97"]],
                "raw_excerpts": ["Total assets | 11,059.12 | 11,204.97"],
                "unit": "INR million",
            }
        ],
    }


def test_tables_are_atomic_chunks_with_source_pages() -> None:
    chunks = build_chunks(_evidence(), max_chars=20)
    table_chunks = [chunk for chunk in chunks if chunk.kind == "financial_table"]

    assert len(table_chunks) == 1
    assert table_chunks[0].source_pages == [131]
    assert table_chunks[0].source_table_id == "table-0001"
    assert "11,059.12" in table_chunks[0].text


def test_bm25_ranks_matching_financial_table() -> None:
    retriever = BM25Retriever.from_evidence(_evidence())

    results = retriever.search("total assets 11,059.12", top_k=2)

    assert results
    assert results[0].chunk.kind == "financial_table"
    assert results[0].chunk.source_pages == [131]
    assert results[0].chunk.source_table_id == "table-0001"


def test_empty_queries_return_no_results() -> None:
    retriever = BM25Retriever.from_evidence(_evidence())
    assert retriever.search("   ") == []
