import smtplib
from email.message import EmailMessage

from app.core.config import settings


class EmailService:

    def send_verification_email(
        self,
        email: str,
        token: str,
    ) -> None:

        verification_url = (
            f"{settings.frontend_url}"
            f"/verify-email?token={token}"
        )

        message = EmailMessage()

        message["Subject"] = (
            "Verify your Telegram Cloud Storage account"
        )

        message["From"] = settings.email_from
        message["To"] = email

        message.set_content(
            f"""
Welcome to Telegram Cloud Storage!

Thank you for creating your account.

Please verify your email address by opening this link:

{verification_url}

This verification link expires in 24 hours.

If you did not create this account, you can ignore this email.
"""
        )

        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=30,
        ) as smtp:

            smtp.starttls()

            smtp.login(
                settings.smtp_username,
                settings.smtp_password,
            )

            smtp.send_message(message)
