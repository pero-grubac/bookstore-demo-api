import smtplib
from email.message import EmailMessage

from app.core.config import settings


def send_email(to: str, subject: str, text: str, html: str | None = None) -> None:
    message = EmailMessage()
    message["From"] = settings.MAIL_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    if html:
        message.add_alternative(html, subtype="html")

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        smtp.send_message(message)
