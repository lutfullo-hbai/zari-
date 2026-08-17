from datetime import UTC, datetime, timedelta

from core.scheduler import (
    ScheduledTask,
    _calculate_next_run,
    _row_to_task,
)


class TestCalculateNextRun:
    def test_once_returns_now(self):
        result = _calculate_next_run("once", "")
        assert result is not None
        assert result <= datetime.now(UTC) + timedelta(seconds=5)

    def test_daily_returns_future(self):
        result = _calculate_next_run("daily", "08:00")
        assert result is not None
        assert result > datetime.now(UTC)

    def test_daily_invalid_format_returns_tomorrow(self):
        result = _calculate_next_run("daily", "invalid")
        assert result is not None
        assert result > datetime.now(UTC)

    def test_interval_returns_future(self):
        result = _calculate_next_run("interval", "30")
        assert result is not None
        now = datetime.now(UTC)
        assert result > now
        assert result <= now + timedelta(minutes=31)

    def test_interval_invalid_returns_hour(self):
        result = _calculate_next_run("interval", "abc")
        assert result is not None
        assert result > datetime.now(UTC)

    def test_unknown_type_returns_now(self):
        result = _calculate_next_run("weekly", "monday")
        assert result is not None


class TestRowToTask:
    def test_converts_row(self):
        row = {
            "id": 1,
            "name": "test",
            "message": "salom",
            "schedule_type": "once",
            "schedule_value": "",
            "is_active": True,
            "last_run": None,
            "next_run": datetime.now(UTC),
        }
        task = _row_to_task(row)
        assert task.id == 1
        assert task.name == "test"
        assert task.message == "salom"
        assert task.is_active is True


class TestScheduledTask:
    def test_defaults(self):
        t = ScheduledTask()
        assert t.id is None
        assert t.is_active is True
        assert t.schedule_type == "once"
