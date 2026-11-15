from pathlib import Path

import pytest

from app.retrieval import BM25Retriever, load_evidence


EVIDENCE_PATH = Path("data/selected_evidence.json")
FULL_EVIDENCE_PATH = Path("data/full_evidence.json")


@pytest.fixture(scope="module")
def retriever() -> BM25Retriever:
    return BM25Retriever.from_evidence(load_evidence(EVIDENCE_PATH))


@pytest.fixture(scope="module")
def full_retriever() -> BM25Retriever:
    return BM25Retriever.from_evidence(load_evidence(FULL_EVIDENCE_PATH))


@pytest.mark.parametrize(
    ("question", "table_id", "pages", "excerpt"),
    [
        (
            "What were total assets in the standalone balance sheet on March 31 2026?",
            "table-0001",
            [131],
            "Total assets (1+2) |  | 11,059.12 | 11,204.97",
        ),
        (
            "What was standalone revenue from operations in 2026?",
            "table-0002",
            [132],
            "Revenue from operations 28 |  | 9,730.56 | 7,760.93",
        ),
        (
            "What was consolidated revenue from operations in 2026?",
            "table-0019",
            [228],
            "Revenue from operations 30",
        ),
        (
            "What was consolidated cash and cash equivalents at the end of the year?",
            "table-0020",
            [229, 230],
            "Cash and cash equivalents at the end of the year",
        ),
        (
            "What were Apparao Mallavarapu's promoter shares at year end?",
            "table-0012",
            [165, 166],
            "52,31,549",
        ),
    ],
)
def test_real_annual_report_question_returns_expected_evidence(
    retriever: BM25Retriever,
    question: str,
    table_id: str,
    pages: list[int],
    excerpt: str,
) -> None:
    results = retriever.search(question, top_k=5)
    matching = [result for result in results if result.chunk.source_table_id == table_id]

    assert matching, [(result.chunk.source_table_id, result.chunk.source_pages) for result in results]
    result = matching[0]
    assert result.chunk.source_pages == pages
    assert excerpt in (result.chunk.raw_excerpt or "")
    assert result.chunk.chunk_id == f"table-{table_id}"


@pytest.mark.parametrize(
    ("question", "table_id", "pages", "excerpt"),
    [
        ("standalone total current assets 9,258.35", "table-0001", [131], "9,258.35"),
        (
            "standalone operating cash flow 284.44",
            "table-0003",
            [133, 134],
            "284.44",
        ),
        (
            "standalone ending cash equivalents 364.97",
            "table-0003",
            [133, 134],
            "364.97",
        ),
        ("trade receivables ageing 2,971.87", "table-0009", [161, 162], "2,971.87"),
        ("payables ageing total 2,549.37", "table-0015", [173, 174], "2,549.37"),
        (
            "property plant equipment net block 1,337.25",
            "table-0007",
            [155],
            "1,337.25",
        ),
        ("consolidated total assets 13,027.12", "table-0018", [227], "13,027.12"),
        (
            "consolidated investing cash flow (432.47)",
            "table-0020",
            [229, 230],
            "(432.47)",
        ),
    ],
)
def test_broader_questions_return_expected_table_in_top_five(
    retriever: BM25Retriever,
    question: str,
    table_id: str,
    pages: list[int],
    excerpt: str,
) -> None:
    results = retriever.search(question, top_k=5)
    matching = [result for result in results if result.chunk.source_table_id == table_id]

    assert matching, [(result.chunk.source_table_id, result.chunk.source_pages) for result in results]
    assert matching[0].chunk.source_pages == pages
    assert excerpt in (matching[0].chunk.raw_excerpt or "")


def test_scope_specific_questions_rank_expected_statement_first(retriever: BM25Retriever) -> None:
    standalone = retriever.search("standalone total current assets 9,258.35", top_k=3)
    consolidated = retriever.search("consolidated total assets 13,027.12", top_k=3)

    assert standalone[0].chunk.source_table_id == "table-0001"
    assert consolidated[0].chunk.source_table_id == "table-0018"


def test_full_report_scope_specific_question_ranks_consolidated_balance_sheet_first(
    full_retriever: BM25Retriever,
) -> None:
    results = full_retriever.search(
        "What were consolidated total assets in 2026?",
        top_k=5,
    )

    assert results[0].chunk.source_table_id == "table-0148"
    assert results[0].chunk.source_pages == [227]
    assert "13,027.12" in (results[0].chunk.raw_excerpt or "")


def test_negative_question_has_no_exact_unsupported_evidence(retriever: BM25Retriever) -> None:
    results = retriever.search("What was lunar mining revenue in 2026?", top_k=10)

    assert results
    assert all(
        not {"lunar", "mining"}.intersection(result.chunk.text.casefold().split())
        for result in results
    )
    assert all(
        "lunar mining" not in (result.chunk.raw_excerpt or "").casefold()
        for result in results
    )


def test_ambiguous_revenue_question_exposes_multiple_statement_scopes(
    retriever: BM25Retriever,
) -> None:
    results = retriever.search("What was revenue?", top_k=10)
    table_ids = {result.chunk.source_table_id for result in results}

    assert "table-0002" in table_ids  # standalone statement
    assert "table-0019" in table_ids  # consolidated statement
    assert {132, 228}.issubset(
        {page for result in results for page in result.chunk.source_pages}
    )


def test_retrieval_results_are_citation_ready(retriever: BM25Retriever) -> None:
    results = retriever.search("standalone total current assets 9,258.35", top_k=5)
    table_result = next(
        result for result in results if result.chunk.source_table_id == "table-0001"
    )

    assert table_result.chunk.chunk_id == "table-table-0001"
    assert table_result.chunk.source_pages == [131]
    assert table_result.chunk.source_table_id == "table-0001"
    assert table_result.chunk.raw_excerpt
    assert "9,258.35" in table_result.chunk.raw_excerpt
