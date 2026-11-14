from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
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
