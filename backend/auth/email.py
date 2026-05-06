import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import HTTPException

from .config import get_auth_settings

logger = logging.getLogger("auth.email")


async def send_password_reset_email(to_email: str, reset_link: str) -> None:
    settings = get_auth_settings()

    def _send() -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Reset your Tax Sathi password"
        msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        msg["To"] = to_email

        html = f"""
<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#1a1a1a">
  <h2 style="margin-bottom:8px">Reset your password</h2>
  <p style="color:#555;margin-bottom:24px">
    We received a request to reset your Tax Sathi password.
    Click the button below to set a new password.
  </p>
  <p style="margin:24px 0">
    <a href="{reset_link}"
       style="background:#2d6a4f;color:#fff;padding:12px 24px;border-radius:6px;
              text-decoration:none;display:inline-block;font-weight:600">
      Set New Password
    </a>
  </p>
  <p style="color:#888;font-size:13px">
    This link expires in {settings.reset_token_expire_minutes} minutes.
  </p>
  <p style="color:#888;font-size:13px">
    If you did not request a password reset, you can safely ignore this email.
  </p>
</body>
</html>
"""
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, to_email, msg.as_string())

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _send)
    except Exception as exc:
        logger.error("Failed to send reset email to %s: %s", to_email, exc)
        raise HTTPException(status_code=500, detail="Failed to send reset email")
