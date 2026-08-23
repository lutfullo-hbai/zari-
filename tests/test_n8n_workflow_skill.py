from unittest.mock import AsyncMock, patch

import pytest

from skills.n8n_workflow import N8nWorkflowSkill


@pytest.fixture
def mock_client():
    """Mock N8nTemplatesClient."""
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
def skill(mock_client):
    with patch("skills.n8n_workflow.N8nTemplatesClient", return_value=mock_client):
        s = N8nWorkflowSkill()
        s._client = mock_client
        return s


@pytest.mark.asyncio
async def test_stats(skill, mock_client):
    result = await skill.execute("statistika")
    assert result is not None
    assert "2053" in result["response"]
    assert "100" in result["response"]
    mock_client.get_stats.assert_called_once()


@pytest.mark.asyncio
async def test_stats_server_unavailable():
    client = AsyncMock()
    client.get_stats.return_value = None
    with patch("skills.n8n_workflow.N8nTemplatesClient", return_value=client):
        s = N8nWorkflowSkill()
        s._client = client
        result = await skill_execute_helper(s, "statistika")
        assert "server ishlamayapti" in result["response"]


@pytest.mark.asyncio
async def test_search(skill, mock_client):
    result = await skill.execute("telegram workflow")
    assert result is not None
    assert "Telegram Schedule Automation" in result["response"]
    mock_client.search_workflows.assert_called_once()


@pytest.mark.asyncio
async def test_search_no_results(skill, mock_client):
    mock_client.search_workflows.return_value = {
        "workflows": [],
        "total": 0,
        "page": 1,
        "per_page": 5,
        "pages": 0,
        "query": "nonexistent",
        "filters": {},
    }
    result = await skill.execute("nonexistent workflow")
    assert result is None


@pytest.mark.asyncio
async def test_categories(skill, mock_client):
    result = await skill.execute("kategoriyalar")
    assert result is not None
    assert "Telegram" in result["response"]
    assert "Gmail" in result["response"]
    mock_client.get_categories.assert_called_once()


@pytest.mark.asyncio
async def test_execute(skill, mock_client):
    result = await skill.execute("ishga tushir Telegram")
    assert result is not None
    assert "Telegram Schedule Automation" in result["response"]
    assert "localhost:5678" in result["response"]


@pytest.mark.asyncio
async def test_execute_not_found(skill, mock_client):
    mock_client.search_workflows.return_value = {
        "workflows": [],
        "total": 0,
        "page": 1,
        "per_page": 1,
        "pages": 0,
        "query": "nonexistent",
        "filters": {},
    }
    result = await skill.execute("ishga tushir nonexistent")
    assert result is not None
    assert "topilmadi" in result["response"]


@pytest.mark.asyncio
async def test_execute_no_name(skill, mock_client):
    result = await skill.execute("workflow ishga tushir")
    assert result is not None
    assert "Nomini ayting" in result["response"]


@pytest.mark.asyncio
async def test_create(skill, mock_client):
    result = await skill.execute("yarat yangi workflow")
    assert result is not None
    assert "localhost:5678" in result["response"]


@pytest.mark.asyncio
async def test_diagram(skill, mock_client):
    result = await skill.execute("diagram 0001_Telegram_Schedule_Automation_Scheduled.json")
    assert result is not None
    assert "graph TD" in result["response"]
    mock_client.get_workflow_diagram.assert_called_once()


@pytest.mark.asyncio
async def test_router_intent():
    from core.router import route

    assert route("telegram workflow") == "workflow"
    assert route("n8n shablon top") == "workflow"
    assert route("automation template") == "workflow"


async def skill_execute_helper(skill, query):
    return await skill.execute(query)
