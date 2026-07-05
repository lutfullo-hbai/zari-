import pytest
from unittest.mock import patch, MagicMock
from skills.n8n_workflow import N8nWorkflowSkill


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_stats.return_value = {
        "total": 100,
        "active": 45,
        "inactive": 55,
        "triggers": {"Webhook": 40, "Scheduled": 20, "Manual": 25, "Complex": 15},
        "complexity": {"low": 30, "medium": 50, "high": 20},
        "total_nodes": 850,
        "unique_integrations": 65,
        "last_indexed": "2026-01-01",
    }
    db.search_workflows.return_value = (
        [
            {
                "filename": "test_workflow.json",
                "name": "Test Workflow",
                "trigger_type": "Webhook",
                "complexity": "low",
                "node_count": 5,
                "integrations": ["Telegram", "Slack"],
                "description": "Test description",
            }
        ],
        1,
    )
    db.get_service_categories.return_value = {
        "messaging": ["Telegram", "Slack"],
        "email": ["Gmail"],
    }
    return db


@pytest.mark.asyncio
async def test_n8n_workflow_search(mock_db):
    with patch("skills.n8n_workflow.N8N_PROJECT_DIR") as mock_dir:
        mock_dir.exists.return_value = True
        with patch.object(N8nWorkflowSkill, "db", mock_db):
            with patch.object(N8nWorkflowSkill, "_ensure_indexed", return_value=True):
                skill = N8nWorkflowSkill()
                result = await skill.execute("telegram bot workflow")

                assert result is not None
                assert "response" in result
                assert "Test Workflow" in result["response"]
                assert result["source"] == "n8n_workflow"


@pytest.mark.asyncio
async def test_n8n_workflow_stats(mock_db):
    with patch("skills.n8n_workflow.N8N_PROJECT_DIR") as mock_dir:
        mock_dir.exists.return_value = True
        with patch.object(N8nWorkflowSkill, "db", mock_db):
            with patch.object(N8nWorkflowSkill, "_ensure_indexed", return_value=True):
                skill = N8nWorkflowSkill()
                result = await skill.execute("statistika")

                assert result is not None
                assert "100" in result["response"]
                assert result["source"] == "n8n_workflow"


@pytest.mark.asyncio
async def test_n8n_workflow_missing_dir():
    with patch("skills.n8n_workflow.N8N_PROJECT_DIR") as mock_dir:
        mock_dir.exists.return_value = False
        skill = N8nWorkflowSkill()
        result = await skill.execute("workflow top")

        assert result is not None
        assert "topilmadi" in result["response"]


@pytest.mark.asyncio
async def test_n8n_workflow_no_results(mock_db):
    mock_db.search_workflows.return_value = ([], 0)
    with patch("skills.n8n_workflow.N8N_PROJECT_DIR") as mock_dir:
        mock_dir.exists.return_value = True
        with patch.object(N8nWorkflowSkill, "db", mock_db):
            with patch.object(N8nWorkflowSkill, "_ensure_indexed", return_value=True):
                skill = N8nWorkflowSkill()
                result = await skill.execute("nonexistent query")

                assert result is None


@pytest.mark.asyncio
async def test_n8n_workflow_categories(mock_db):
    with patch("skills.n8n_workflow.N8N_PROJECT_DIR") as mock_dir:
        mock_dir.exists.return_value = True
        with patch.object(N8nWorkflowSkill, "db", mock_db):
            with patch.object(N8nWorkflowSkill, "_ensure_indexed", return_value=True):
                skill = N8nWorkflowSkill()
                result = await skill.execute("kategoriyalar")

                assert result is not None
                assert "messaging" in result["response"]
                assert result["source"] == "n8n_workflow"


@pytest.mark.asyncio
async def test_n8n_workflow_router_intent():
    from core.router import route

    assert route("telegram workflow") == "workflow"
    assert route("n8n shablon top") == "workflow"
    assert route("automation template") == "workflow"


@pytest.mark.asyncio
async def test_n8n_workflow_execute_found_no_executor(mock_db):
    mock_db.search_workflows.return_value = (
        [{
            "filename": "test_workflow.json",
            "name": "Test Workflow",
            "trigger_type": "Webhook",
            "complexity": "low",
            "node_count": 5,
            "integrations": ["Telegram"],
        }],
        1,
    )
    with patch("skills.n8n_workflow.N8N_PROJECT_DIR") as mock_dir:
        mock_dir.exists.return_value = True
        with patch.object(N8nWorkflowSkill, "db", mock_db):
            with patch.object(N8nWorkflowSkill, "_ensure_indexed", return_value=True):
                with patch("skills.n8n_workflow._import_workflow_executor", return_value=None):
                    skill = N8nWorkflowSkill()
                    result = await skill.execute("run telegram bot workflow")

                    assert result is not None
                    assert "topildi" in result["response"]
                    assert "muharriki mavjud emas" in result["response"]


@pytest.mark.asyncio
async def test_n8n_workflow_execute_not_found_falls_to_search(mock_db):
    mock_db.search_workflows.return_value = ([], 0)
    with patch("skills.n8n_workflow.N8N_PROJECT_DIR") as mock_dir:
        mock_dir.exists.return_value = True
        with patch.object(N8nWorkflowSkill, "db", mock_db):
            with patch.object(N8nWorkflowSkill, "_ensure_indexed", return_value=True):
                skill = N8nWorkflowSkill()
                result = await skill.execute("ishlat nonexistent")

                assert result is None


@pytest.mark.asyncio
async def test_n8n_workflow_execute_with_executor(mock_db):
    mock_db.search_workflows.return_value = (
        [{
            "filename": "my_workflow.json",
            "name": "My Workflow",
            "trigger_type": "Manual",
            "complexity": "low",
            "node_count": 3,
            "integrations": ["HTTP"],
        }],
        1,
    )
    async def mock_run(workflow_name):
        return f"Executed {workflow_name}"

    with patch("skills.n8n_workflow.N8N_PROJECT_DIR") as mock_dir:
        mock_dir.exists.return_value = True
        with patch.object(N8nWorkflowSkill, "db", mock_db):
            with patch.object(N8nWorkflowSkill, "_ensure_indexed", return_value=True):
                with patch("skills.n8n_workflow._import_workflow_executor", return_value=mock_run):
                    skill = N8nWorkflowSkill()
                    result = await skill.execute("bajar My Workflow")

                    assert result is not None
                    assert "bajarildi" in result["response"]
                    assert "my_workflow.json" in result["response"]
                    assert result["source"] == "n8n_workflow"
