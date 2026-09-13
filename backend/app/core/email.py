import asyncio
import smtplib
from email.message import EmailMessage

from app.config.settings import settings


def _send_email_sync(to: str, subject: str, html_body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.SMTP_USERNAME
    message["To"] = to
    message["Subject"] = subject
    message.set_content(html_body, subtype="html")

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(message)


async def send_email(to: str, subject: str, html_body: str) -> None:
    await asyncio.to_thread(_send_email_sync, to, subject, html_body)
