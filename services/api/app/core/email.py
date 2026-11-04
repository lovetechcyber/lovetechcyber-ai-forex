
import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


def email_is_configured() -> bool:
    return all(
        value.strip()
        for value in (
            settings.smtp_host,
            settings.smtp_username,
            settings.smtp_password,
            settings.smtp_from_email,
        )
    )


def _send_email(recipient: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = (
        f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    )
    message["To"] = recipient
    message.set_content(body)

    context = ssl.create_default_context()

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
        timeout=10,
    ) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)


async def send_password_reset_email(
    recipient: str,
    reset_url: str,
) -> None:
    body = (
        "We received a request to reset the password for your "
        "LovetechCyber AI Forex Analyst account.\n\n"
        f"Use this link to choose a new password:\n{reset_url}\n\n"
        "This link expires in 30 minutes and can only be used once.\n"
        "If you did not request this reset, you can ignore this email.\n\n"
        "For your security, do not share this link with anyone."
    )

    await asyncio.to_thread(
        _send_email,
        recipient,
        "Reset your LovetechCyber account password",
        body,
    )
