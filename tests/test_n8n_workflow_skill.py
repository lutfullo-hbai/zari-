from unittest.mock import AsyncMock, patch

import pytest

from skills.n8n_workflow import N8nWorkflowSkill


@pytest.fixture
def mock_n8n():
    """Mock N8nClient (real n8n server)."""
    client = AsyncMock()
    client.health_check.return_value = True
    client.list_workflows.return_value = [
        {"id": "wf-1", "name": "Telegram Bot", "active": True},
        {"id": "wf-2", "name": "Email Sender", "active": False},
    ]
    client.search_workflows.return_value = [
        {"id": "wf-1", "name": "Telegram Bot", "active": True},
    ]
    client.activate_workflow.return_value = True
    client.deactivate_workflow.return_value = True
    client.trigger_webhook.return_value = {"status": "ok"}
    client.get_executions.return_value = [
        {"status": "success", "createdAt": "2026-01-01T12:00:00Z"},
    ]
    return client


@pytest.fixture
def mock_templates():
    """Mock N8nTemplatesClient (templates API server)."""
    client = AsyncMock()
    client.health_check.return_value = True
    client.get_stats.return_value = {
        "total": 2053,
        "active": 100,
        "inactive": 1953,
        "triggers": {"Manual": 500, "Webhook": 300, "Scheduled": 200, "Complex": 53},
        "complexity": {"low": 800, "medium": 1000, "high": 253},
        "total_nodes": 15000,
        "unique_integrations": 150,
        "last_indexed": "2026-01-01",
    }
    client.search_workflows.return_value = {
        "workflows": [
            {
                "id": 1,
                "filename": "0001_Telegram_Schedule_Automation_Scheduled.json",
                "name": "Telegram Schedule Automation",
                "active": False,
                "description": "Telegram bot with schedule trigger",
                "trigger_type": "Scheduled",
                "complexity": "low",
                "node_count": 5,
                "integrations": ["Telegram"],
                "tags": ["messaging", "automation"],
            }
        ],
        "total": 1,
        "page": 1,
        "per_page": 5,
        "pages": 1,
        "query": "telegram",
        "filters": {},
    }
    client.get_categories.return_value = {
        "categories": {
            "messaging": ["Telegram", "Slack"],
            "email": ["Gmail"],
        }
    }
    client.get_workflow_diagram.return_value = "graph TD\n  A[Telegram] --> B[HTTP]"
    return client


@pytest.fixture
def skill(mock_n8n, mock_templates):
    with (
        patch("skills.n8n_workflow.N8nClient", return_value=mock_n8n),
        patch("skills.n8n_workflow.N8nTemplatesClient", return_value=mock_templates),
    ):
        s = N8nWorkflowSkill()
        s._n8n = mock_n8n
        s._templates = mock_templates
        return s


@pytest.mark.asyncio
async def test_stats(skill, mock_templates):
    result = await skill.execute("statistika")
    assert result is not None
    assert "2053" in result["response"]
    assert "100" in result["response"]
    mock_templates.get_stats.assert_called_once()


@pytest.mark.asyncio
async def test_stats_server_unavailable(mock_templates):
    mock_templates.get_stats.return_value = None
    with (
        patch("skills.n8n_workflow.N8nClient", return_value=AsyncMock()),
        patch("skills.n8n_workflow.N8nTemplatesClient", return_value=mock_templates),
    ):
        s = N8nWorkflowSkill()
        s._templates = mock_templates
        result = await s.execute("statistika")
        assert "server ishlamayapti" in result["response"]


@pytest.mark.asyncio
async def test_search(skill, mock_templates):
    result = await skill.execute("telegram workflow top")
    assert result is not None
    assert "Telegram Schedule Automation" in result["response"]
    mock_templates.search_workflows.assert_called()


@pytest.mark.asyncio
async def test_search_no_results(skill, mock_templates):
    mock_templates.search_workflows.return_value = {
        "workflows": [],
        "total": 0,
        "page": 1,
        "per_page": 5,
        "pages": 0,
        "query": "nonexistent",
        "filters": {},
    }
    result = await skill.execute("nonexistent workflow top")
    assert result is None


@pytest.mark.asyncio
async def test_categories(skill, mock_templates):
    result = await skill.execute("kategoriyalar")
    assert result is not None
    assert "Telegram" in result["response"]
    assert "Gmail" in result["response"]
    mock_templates.get_categories.assert_called_once()


@pytest.mark.asyncio
async def test_list_workflows(skill, mock_n8n):
    result = await skill.execute("workflowlar ro'yxati")
    assert result is not None
    assert "Telegram Bot" in result["response"]
    assert "Email Sender" in result["response"]
    mock_n8n.list_workflows.assert_called_once()


@pytest.mark.asyncio
async def test_activate_workflow(skill, mock_n8n):
    result = await skill.execute("ishga tushir Telegram")
    assert result is not None
    assert "faollashtirildi" in result["response"]
    mock_n8n.activate_workflow.assert_called_once()


@pytest.mark.asyncio
async def test_deactivate_workflow(skill, mock_n8n):
    result = await skill.execute("to'xtat Telegram")
    assert result is not None
    assert "o'chirildi" in result["response"]
    mock_n8n.deactivate_workflow.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_webhook(skill, mock_n8n):
    result = await skill.execute("webhook my-webhook")
    assert result is not None
    assert "ishga tushirildi" in result["response"]
    mock_n8n.trigger_webhook.assert_called_once()


@pytest.mark.asyncio
async def test_executions(skill, mock_n8n):
    result = await skill.execute("tarix Telegram")
    assert result is not None
    assert "success" in result["response"]
    mock_n8n.get_executions.assert_called_once()


@pytest.mark.asyncio
async def test_create(skill):
    result = await skill.execute("yarat yangi workflow")
    assert result is not None
    assert "localhost:5678" in result["response"]


@pytest.mark.asyncio
async def test_diagram(skill, mock_templates):
    result = await skill.execute("diagram 0001_Telegram_Schedule_Automation_Scheduled.json")
    assert result is not None
    assert "graph TD" in result["response"]
    mock_templates.get_workflow_diagram.assert_called_once()


@pytest.mark.asyncio
async def test_router_intent():
    from core.router import route

    assert route("telegram workflow") == "workflow"
    assert route("n8n shablon top") == "workflow"
    assert route("automation template") == "workflow"


@pytest.mark.asyncio
async def test_n8n_server_unavailable(skill, mock_n8n):
    mock_n8n.health_check.return_value = False
    result = await skill.execute("workflowlar ro'yxati")
    assert result is not None
    assert "server ishlamayapti" in result["response"]


@pytest.mark.asyncio
async def test_activate_not_found(skill, mock_n8n):
    mock_n8n.search_workflows.return_value = []
    mock_n8n.list_workflows.return_value = []
    result = await skill.execute("ishga tushir nonexistent")
    assert result is not None
    assert "topilmadi" in result["response"]
