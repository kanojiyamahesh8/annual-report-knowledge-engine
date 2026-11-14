import json
from types import SimpleNamespace
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app, get_qa_service
from app.qa import NOT_FOUND


client = TestClient(app)


class FakeService:
    def __init__(self, response=None, error=None):
        self.response = response or {"answer": "Standalone total assets were 11,059.12 INR million.", "excerpts": [{"text": "Total assets |  | 11,059.12 | 11,204.97", "pages": [131]}]}
        self.error = error
        self.questions = []

    def ask(self, question):
        self.questions.append(question)
        if self.error:
            raise self.error
        return SimpleNamespace(to_dict=lambda: self.response)


class MockLLM:
    def __init__(self, payload):
        self.payload = payload

    def invoke(self, prompt):
        return SimpleNamespace(content=json.dumps(self.payload))


def test_ask_endpoint_returns_answer_and_citations(monkeypatch):
    service = FakeService()
    monkeypatch.setattr("app.main.get_qa_service", lambda: service)

    response = client.post("/api/ask", json={"question": "What were standalone total assets in 2026?"})

    assert response.status_code == 200
    assert response.json()["answer"].startswith("Standalone total assets")
    assert response.json()["excerpts"][0]["pages"] == [131]
    assert service.questions == ["What were standalone total assets in 2026?"]


def test_ask_endpoint_preserves_exact_not_found_response(monkeypatch):
    service = FakeService({"answer": NOT_FOUND, "excerpts": []})
    monkeypatch.setattr("app.main.get_qa_service", lambda: service)

    response = client.post("/api/ask", json={"question": "What was lunar mining revenue?"})

    assert response.status_code == 200
    assert response.json() == {"answer": NOT_FOUND, "excerpts": []}


def test_ask_endpoint_rejects_empty_question():
    response = client.post("/api/ask", json={"question": ""})
    assert response.status_code == 422


def test_ask_endpoint_rejects_whitespace_only_question():
    response = client.post("/api/ask", json={"question": "   "})
    assert response.status_code == 422


def test_ask_endpoint_uses_real_retriever_and_qa_service_with_mocked_llm(monkeypatch):
    monkeypatch.setattr(
        "app.qa.create_llm",
        lambda: MockLLM({"answer": "Standalone total assets were 11,059.12 INR million.", "excerpts": [{"text": "Total assets (1+2) |  | 11,059.12 | 11,204.97", "pages": [131]}]}),
    )
    get_qa_service.cache_clear()
    try:
        response = client.post("/api/ask", json={"question": "What were standalone total assets in 2026?"})
    finally:
        get_qa_service.cache_clear()

    assert response.status_code == 200
    assert response.json()["answer"].startswith("Standalone total assets")
    assert response.json()["excerpts"][0]["pages"] == [131]


def test_ask_endpoint_classifies_missing_evidence_as_service_unavailable(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("app.main.settings", SimpleNamespace(evidence_path=str(tmp_path / "missing.json")))
    get_qa_service.cache_clear()
    try:
        response = client.post("/api/ask", json={"question": "What were total assets?"})
    finally:
        get_qa_service.cache_clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Evidence corpus unavailable"}


def test_ask_endpoint_classifies_provider_initialization_failure(monkeypatch):
    monkeypatch.setattr("app.qa.create_llm", lambda: (_ for _ in ()).throw(RuntimeError("provider init failure")))
    get_qa_service.cache_clear()
    try:
        response = client.post("/api/ask", json={"question": "What were total assets?"})
    finally:
        get_qa_service.cache_clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "LLM provider request failed"}


def test_ask_endpoint_hides_provider_failures(monkeypatch):
    service = FakeService(error=RuntimeError("secret provider detail"))
    monkeypatch.setattr("app.main.get_qa_service", lambda: service)

    response = client.post("/api/ask", json={"question": "What were total assets?"})

    assert response.status_code == 502
    assert response.json() == {"detail": "LLM provider request failed"}
    assert "secret provider detail" not in response.text


def test_homepage_exposes_qa_interface():
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="ask-form"' in response.text
    assert 'id="question"' in response.text
