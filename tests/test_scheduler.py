from datetime import UTC, datetime, timedelta

from core.scheduler import (
    ScheduledTask,
    _calculate_next_run,
    _row_to_task,
)


class TestCalculateNextRun:
    def test_once_empty_value_runs_now(self):
        """Bo'sh qiymat — eski xulq: darhol bajarish (backward compat)."""
        result = _calculate_next_run("once", "")
        assert result is not None
        assert result <= datetime.now(UTC) + timedelta(seconds=5)

    def test_once_future_time_today(self):
        """'HH:MM' — bugun o'sha vaqt ( agar o'tmagan bo'lsa)."""
        now = datetime.now(UTC)
        future_hour = (now.hour + 1) % 24
        value = f"{future_hour:02d}:30"
        result = _calculate_next_run("once", value)
        assert result is not None
        assert result > now
        assert result.minute == 30

    def test_once_past_time_runs_tomorrow(self):
        """ "HH:MM" allaqachon o'tgan bo'lsa — ertaga."""
        now = datetime.now(UTC)
        past_hour = (now.hour - 1) % 24
        value = f"{past_hour:02d}:00"
        result = _calculate_next_run("once", value)
        assert result is not None
        assert result > now
        assert result.date() > now.date()

    def test_once_iso_datetime_future(self):
        target = datetime.now(UTC) + timedelta(hours=2)
        result = _calculate_next_run("once", target.isoformat())
        assert result == target

    def test_once_iso_datetime_naive_gets_utc(self):
        target = datetime.now(UTC) + timedelta(hours=2)
        naive = target.replace(tzinfo=None).isoformat()
        result = _calculate_next_run("once", naive)
        assert result is not None
        assert result.tzinfo is not None
        assert abs((result - target).total_seconds()) < 1

    def test_once_invalid_string_falls_back_to_now(self):
        result = _calculate_next_run("once", "ertaga ertalab")
        assert result is not None
        assert result <= datetime.now(UTC) + timedelta(seconds=5)

    def test_once_bad_time_range_falls_back_to_now(self):
        result = _calculate_next_run("once", "25:99")
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
