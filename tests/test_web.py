from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

import web.app as web_app
from web.app import app, set_pipeline
from web.schemas import ChatRequest, ChatResponse, StatusResponse, TaskCreateRequest


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
        mock_pipeline.ask = AsyncMock(return_value="salom, qanday?")
        set_pipeline(mock_pipeline)
        client = TestClient(app)
        resp = client.post("/api/chat", json={"message": "salom"})
        assert resp.status_code == 200
        assert resp.json()["response"] == "salom, qanday?"
        mock_pipeline.ask.assert_awaited_once_with("salom", timeout=65)

    def test_chat_timeout(self):
        mock_pipeline = MagicMock()
        mock_pipeline.ask = AsyncMock(side_effect=TimeoutError())
        set_pipeline(mock_pipeline)
        client = TestClient(app)
        resp = client.post("/api/chat", json={"message": "salom"})
        assert resp.status_code == 200
        assert "tugadi" in resp.json()["response"]

    def test_chat_offline_no_ask_call(self):
        mock_pipeline = MagicMock()
        set_pipeline(mock_pipeline)
        client = TestClient(app)
        resp = client.post("/api/chat", json={"message": ""})
        assert resp.status_code == 422


class TestDashboard:
    def test_dashboard_returns_html(self):
        set_pipeline(None)
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]


class TestAuth:
    def test_auth_disabled_by_default(self, monkeypatch):
        monkeypatch.setattr(web_app.settings, "web_api_key", "")
        set_pipeline(None)
        client = TestClient(app)
        resp = client.get("/api/status")
        assert resp.status_code == 200

    def test_auth_required_when_configured(self, monkeypatch):
        monkeypatch.setattr(web_app.settings, "web_api_key", "secret123")
        set_pipeline(None)
        client = TestClient(app)

        assert client.get("/api/status").status_code == 401
        assert client.get("/api/tasks").status_code == 401

        wrong = client.get("/api/status", headers={"X-API-Key": "wrong"})
        assert wrong.status_code == 401

    def test_auth_passes_with_valid_key(self, monkeypatch):
        monkeypatch.setattr(web_app.settings, "web_api_key", "secret123")
        set_pipeline(None)
        client = TestClient(app)
        resp = client.get("/api/status", headers={"X-API-Key": "secret123"})
        assert resp.status_code == 200

    def test_dashboard_open_even_with_key(self, monkeypatch):
        """Dashboard statik sahifa — kalitsiz ochiladi (token WS orqali)."""
        monkeypatch.setattr(web_app.settings, "web_api_key", "secret123")
        set_pipeline(None)
        client = TestClient(app)
        assert client.get("/").status_code == 200


class TestTaskEndpointValidation:
    def test_task_create_schema_defaults(self):
        req = TaskCreateRequest(message="salom ayt")
        assert req.name == "task"
        assert req.schedule_type == "once"

    def test_task_create_schema_rejects_bad_type(self):
        import pytest as _pytest
        from pydantic import ValidationError

        with _pytest.raises(ValidationError):
            TaskCreateRequest(message="x", schedule_type="hourly")

    def test_create_task_endpoint(self, monkeypatch):
        captured = {}

        async def fake_add_task(name, message, schedule_type, schedule_value):
            captured.update(
                name=name,
                message=message,
                schedule_type=schedule_type,
                schedule_value=schedule_value,
            )

            class FakeTask:
                id = 42

            return FakeTask()

        monkeypatch.setattr(web_app, "add_task", fake_add_task)
        set_pipeline(None)
        client = TestClient(app)

        resp = client.post(
            "/api/tasks",
            json={"name": "eslatma", "message": "cofe ich", "schedule_type": "daily", "schedule_value": "08:00"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"id": 42, "status": "created"}
        assert captured["schedule_value"] == "08:00"

    def test_create_task_endpoint_rejects_empty_message(self):
        set_pipeline(None)
        client = TestClient(app)
        resp = client.post("/api/tasks", json={"message": ""})
        assert resp.status_code == 422
