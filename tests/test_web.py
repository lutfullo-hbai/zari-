from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from web.app import app, set_pipeline
from web.schemas import ChatRequest, ChatResponse, StatusResponse


class TestSchemas:
    def test_chat_request(self):
        req = ChatRequest(message="salom")
        assert req.message == "salom"

    def test_chat_response(self):
        res = ChatResponse(response="javob")
        assert res.response == "javob"
        assert res.source == "llm"

    def test_status_response(self):
        res = StatusResponse(status="online", provider="groq")
        assert res.status == "online"


class TestStatusEndpoint:
    def test_status_offline(self):
        set_pipeline(None)
        client = TestClient(app)
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "offline"

    def test_status_online(self):
        mock_pipeline = MagicMock()
        mock_pipeline.memory.session_id = "test-123"
        mock_pipeline.memory.get.return_value = [{"role": "user", "content": "hi"}]
        set_pipeline(mock_pipeline)
        client = TestClient(app)
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert data["session_id"] == "test-123"


class TestChatEndpoint:
    def test_chat_offline(self):
        set_pipeline(None)
        client = TestClient(app)
        resp = client.post("/api/chat", json={"message": "salom"})
        assert resp.status_code == 200
        assert "ishga tushmagan" in resp.json()["response"]

    def test_chat_success(self):
        mock_pipeline = MagicMock()
        mock_queue = AsyncMock()
        mock_queue.get = AsyncMock(return_value="salom, qanday?")
        mock_pipeline.text_queue = AsyncMock()
        mock_pipeline.response_queue = mock_queue
        set_pipeline(mock_pipeline)
        client = TestClient(app)
        resp = client.post("/api/chat", json={"message": "salom"})
        assert resp.status_code == 200
        assert resp.json()["response"] == "salom, qanday?"

    def test_chat_timeout(self):
        mock_pipeline = MagicMock()
        mock_queue = AsyncMock()
        mock_queue.get = AsyncMock(side_effect=TimeoutError())
        mock_pipeline.text_queue = AsyncMock()
        mock_pipeline.response_queue = mock_queue
        set_pipeline(mock_pipeline)
        client = TestClient(app)
        resp = client.post("/api/chat", json={"message": "salom"})
        assert resp.status_code == 200
        assert "tugadi" in resp.json()["response"]


class TestDashboard:
    def test_dashboard_returns_html(self):
        set_pipeline(None)
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
