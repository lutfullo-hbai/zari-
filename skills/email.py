import asyncio
import re
import smtplib
from email.message import EmailMessage

from skills.base import BaseSkill


def _send_sync(
    smtp_host: str, smtp_port: int, smtp_username: str, smtp_password: str, smtp_use_tls: bool, msg: EmailMessage
) -> None:
    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
        if smtp_use_tls:
            smtp.starttls()
        if smtp_username:
            smtp.login(smtp_username, smtp_password)
        smtp.send_message(msg)


class EmailSkill(BaseSkill):
    priority = 40
    timeout = 15.0
    requires_confirmation = True
    confirmation_type = "destructive"

    def __init__(
        self,
        smtp_host: str = "",
        smtp_port: int = 587,
        smtp_username: str = "",
        smtp_password: str = "",
        smtp_use_tls: bool = True,
        sender_address: str = "",
        default_recipient: str = "",
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.smtp_use_tls = smtp_use_tls
        self.sender_address = sender_address
        self.default_recipient = default_recipient

    async def execute(self, query: str) -> dict:
        recipient = self.default_recipient
        body = self._extract_message(query)

        if not self.smtp_host or not recipient:
            return {
                "status": "not_configured",
                "response": "Email yuborish uchun SMTP sozlamalari yetarli emas.",
            }

        msg = EmailMessage()
        msg["Subject"] = "Zari xabari"
        msg["From"] = self.sender_address or self.smtp_username or recipient
        msg["To"] = recipient
        msg.set_content(body or "Salom! Bu xabar Zari orqali yuborildi.")

        try:
            await asyncio.to_thread(
                _send_sync,
                self.smtp_host,
                self.smtp_port,
                self.smtp_username,
                self.smtp_password,
                self.smtp_use_tls,
                msg,
            )
        except Exception as exc:
            return {
                "status": "error",
                "response": f"Email yuborishda xatolik: {exc}",
            }

        return {
            "status": "sent",
            "response": f"Email muvaffaqiyatli yuborildi: {recipient}",
        }

    def _extract_message(self, query: str) -> str:
        match = re.search(r"(?:gmail|email|mail|xat)\s+(?:yubor|send)\s*[:\-]?\s*(.+)", query, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return query.strip()
