from unittest.mock import patch

import pytest

from core.router import route
from skills.email import EmailSkill


@pytest.mark.asyncio
async def test_email_skill_sends_message_via_smtp():
    with patch("skills.email.smtplib.SMTP") as smtp_mock:
        smtp_instance = smtp_mock.return_value.__enter__.return_value
        skill = EmailSkill(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            smtp_password="secret",
            smtp_use_tls=False,
            sender_address="from@example.com",
            default_recipient="to@example.com",
        )

        result = await skill.execute("gmail yubor: salom")

        assert result["status"] == "sent"
        assert "yuborildi" in result["response"].lower()
        smtp_instance.login.assert_called_once_with("user@example.com", "secret")


@pytest.mark.asyncio
async def test_email_skill_empty_config_returns_not_configured():
    skill = EmailSkill()
    result = await skill.execute("gmail yubor: salom")

    assert result["status"] == "not_configured"


@pytest.mark.asyncio
async def test_email_skill_smtp_failure_returns_error():
    with patch("skills.email.smtplib.SMTP") as smtp_mock:
        smtp_instance = smtp_mock.return_value.__enter__.return_value
        smtp_instance.send_message.side_effect = ConnectionRefusedError("Port 587 refused")

        skill = EmailSkill(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            smtp_password="secret",
            smtp_use_tls=False,
            sender_address="from@example.com",
            default_recipient="to@example.com",
        )

        result = await skill.execute("gmail yubor: salom")

        assert result["status"] == "error"
        assert "xatolik" in result["response"].lower()


def test_router_detects_email_intent():
    assert route("gmail yubor") == "email"
