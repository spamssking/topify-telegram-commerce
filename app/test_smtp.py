import smtplib
from email.message import EmailMessage

from app.core.config import settings


message = EmailMessage()

message["Subject"] = "Telegram Cloud Storage SMTP Test"
message["From"] = settings.email_from
message["To"] = settings.email_from

message.set_content(
    "This is a test email from Telegram Cloud Storage."
)


with smtplib.SMTP(
    settings.smtp_host,
    settings.smtp_port,
) as smtp:

    smtp.starttls()

    smtp.login(
        settings.smtp_username,
        settings.smtp_password,
    )

    smtp.send_message(message)


print("SMTP TEST SUCCESS")
