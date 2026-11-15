import json
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.llm import LLMConfigurationError, create_llm
from app.qa import NOT_FOUND, QAService, _evidence_payload
from app.retrieval import BM25Retriever, EvidenceChunk, RetrievalResult


def evidence() -> dict:
    return {
        "pages": [
            {"pdf_page_number": 131, "text": "Standalone Ind AS Balance Sheet Total assets 11,059.12 11,204.97"},
            {"pdf_page_number": 227, "text": "Consolidated Ind AS Balance Sheet Total assets 13,027.12 12,394.46"},
        ],
        "tables": [
            {"table_id": "table-0001", "source_pages": [131], "semantic_headers": ["Particulars", "2026", "2025"], "rows": [["Total assets", "11,059.12", "11,204.97"]], "raw_excerpts": ["Total assets |  | 11,059.12 | 11,204.97"], "unit": "INR million"},
            {"table_id": "table-0018", "source_pages": [227], "semantic_headers": ["Particulars", "2026", "2025"], "rows": [["Total assets", "13,027.12", "12,394.46"]], "raw_excerpts": ["Total assets | 13,027.12 | 12,394.46"], "unit": "INR million"},
        ],
    }


class MockLLM:
    def __init__(self, payload):
        self.payload = payload
        self.inputs = []

    def invoke(self, prompt):
        self.inputs.append(prompt)
        return SimpleNamespace(content=json.dumps(self.payload))


def test_qa_returns_only_validated_exact_excerpt_and_pages():
    llm = MockLLM({"answer": "Standalone total assets were 11,059.12 INR million.", "excerpts": [{"text": "Total assets |  | 11,059.12 | 11,204.97", "pages": [131]}]})
    response = QAService(BM25Retriever.from_evidence(evidence()), llm=llm).ask("What were standalone total assets in 2026?")
    assert response.answer.startswith("Standalone total assets")
    assert response.excerpts[0].pages == [131]
    assert "Retrieved evidence" in str(llm.inputs[0])


def test_invalid_citation_is_rejected():
    llm = MockLLM({"answer": "The answer is 999.", "excerpts": [{"text": "invented excerpt", "pages": [131]}]})
    response = QAService(BM25Retriever.from_evidence(evidence()), llm=llm).ask("What were standalone total assets in 2026?")
    assert response.answer == NOT_FOUND
    assert response.excerpts == []


def test_large_table_payload_keeps_relevant_exact_lines_and_is_bounded():
    chunk = EvidenceChunk(
        chunk_id="table-large",
        kind="financial_table",
        text="Consolidated balance sheet " + "irrelevant " * 3000,
        source_pages=[227],
        raw_excerpt="\n".join(
            ["Particulars | March 31, 2026 | March 31, 2025"]
            + [f"Other row {index} | {index} | {index}" for index in range(200)]
            + ["Total assets (1+2+3) | 13,027.12 | 12,394.46"]
        ),
    )
    payload = json.loads(_evidence_payload([RetrievalResult(chunk=chunk, score=1.0)], "consolidated total assets 2026"))
    assert "Total assets (1+2+3) | 13,027.12 | 12,394.46" in payload[0]["exact_excerpt_lines"]
    assert len(json.dumps(payload)) < 5000


def test_payload_includes_unambiguous_deterministic_cell_mapping():
    retriever = BM25Retriever.from_evidence(evidence())
    results = retriever.search("standalone total assets 2026", top_k=2)
    payload = json.loads(_evidence_payload(results, "standalone total assets 2026"))
    standalone = next(item for item in payload if item["pdf_pages"] == [131])
    assert standalone["deterministic_cells"][0]["value"] == "11,059.12"
    assert standalone["deterministic_cells"][0]["column_label"] == "2026"
    assert standalone["deterministic_cells"][0]["pdf_pages"] == [131]
    assert standalone["deterministic_cells"][0]["table_id"] == "table-0001"


def test_payload_does_not_leak_deterministic_cells_across_scope():
    retriever = BM25Retriever.from_evidence(evidence())
    results = [
        RetrievalResult(chunk=chunk, score=1.0)
        for chunk in retriever.chunks
        if chunk.kind == "financial_table"
    ]
    payload = json.loads(_evidence_payload(results, "standalone total assets 2026"))
    consolidated = next(item for item in payload if item["pdf_pages"] == [227])
    assert "deterministic_cells" not in consolidated


def test_answer_with_wrong_year_cell_is_rejected_even_with_valid_excerpt():
    llm = MockLLM({
        "answer": "Standalone total assets were 11,204.97 INR million.",
        "excerpts": [{"text": "Total assets |  | 11,059.12 | 11,204.97", "pages": [131]}],
    })
    response = QAService(BM25Retriever.from_evidence(evidence()), llm=llm).ask(
        "What were standalone total assets in 2026?"
    )
    assert response.answer == NOT_FOUND


def test_empty_pages_are_rejected():
    llm = MockLLM({"answer": "Standalone total assets were 11,059.12 INR million.", "excerpts": [{"text": "Total assets |  | 11,059.12 | 11,204.97", "pages": []}]})
    response = QAService(BM25Retriever.from_evidence(evidence()), llm=llm).ask("What were standalone total assets in 2026?")
    assert response.answer == NOT_FOUND


def test_hallucinated_figure_is_rejected_even_with_valid_excerpt():
    llm = MockLLM({"answer": "Standalone total assets were 999.99 INR million.", "excerpts": [{"text": "Total assets |  | 11,059.12 | 11,204.97", "pages": [131]}]})
    response = QAService(BM25Retriever.from_evidence(evidence()), llm=llm).ask("What were standalone total assets in 2026?")
    assert response.answer == NOT_FOUND


def test_unsupported_and_ambiguous_questions_return_exact_not_found():
    service = QAService(BM25Retriever.from_evidence(evidence()), llm=MockLLM({}))
    assert service.ask("What was lunar mining revenue in 2026?").answer == NOT_FOUND
    assert service.ask("What were total assets?").answer == NOT_FOUND


def test_unsupported_substantive_terms_do_not_reach_llm():
    llm = MockLLM({"answer": "not used", "excerpts": []})
    service = QAService(BM25Retriever.from_evidence(evidence()), llm=llm)
    assert service.ask("What were standalone lunar mining assets in 2026?").answer == NOT_FOUND
    assert llm.inputs == []


@pytest.mark.parametrize("provider", ["openai", "gemini", "anthropic", "groq"])
def test_provider_switching_uses_env_provider(monkeypatch, provider):
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    config = Settings()
    fake = object()
    if provider == "openai":
        monkeypatch.setattr("langchain_openai.ChatOpenAI", lambda **kwargs: (fake, kwargs))
    elif provider == "gemini":
        monkeypatch.setattr("langchain_google_genai.ChatGoogleGenerativeAI", lambda **kwargs: (fake, kwargs))
    elif provider == "anthropic":
        monkeypatch.setattr("langchain_anthropic.ChatAnthropic", lambda **kwargs: (fake, kwargs))
    else:
        monkeypatch.setattr("langchain_groq.ChatGroq", lambda **kwargs: (fake, kwargs))
    model, kwargs = create_llm(config)
    assert model is fake
    assert kwargs["model"] == getattr(config, f"{provider if provider != 'gemini' else 'gemini'}_model")
    assert kwargs["timeout"] == config.llm_timeout_seconds
    assert kwargs["max_retries"] == config.llm_max_retries


def test_unknown_provider_is_rejected():
    with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
        create_llm(Settings(llm_provider="unknown"))


def test_provider_configuration_requires_credentials():
    with pytest.raises(LLMConfigurationError, match="Missing API key"):
        create_llm(Settings(llm_provider="openai", openai_api_key=""))
