"""
Отправка писем через SMTP (Яндекс 360: smtp.yandex.ru, порт 465).
"""
import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from app.config import Config
from app.core.logging import get_logger

logger = get_logger(__name__)

VERIFICATION_HTML_SMTP = """
<!DOCTYPE html>
<html lang="ru">
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;font-family:'Helvetica Neue',Arial,sans-serif;background:#f4f7fa;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;margin:40px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
    <tr><td style="padding:32px 32px 0;text-align:center;">
      <h1 style="margin:0;font-size:22px;color:#0f172a;">Capital<span style="color:#3b82f6;">View</span></h1>
    </td></tr>
    <tr><td style="padding:24px 32px;text-align:center;">
      <p style="margin:0 0 16px;font-size:16px;color:#334155;">Подтвердите ваш email</p>
      <a href="{link}" target="_blank" style="display:inline-block;padding:14px 32px;background:#3b82f6;color:#fff;font-size:16px;font-weight:600;text-decoration:none;border-radius:10px;">Подтвердить email</a>
      <p style="margin:16px 0 0;font-size:13px;color:#94a3b8;">Или скопируйте ссылку:<br><a href="{link}" style="color:#3b82f6;word-break:break-all;">{link}</a></p>
      <p style="margin:16px 0 0;font-size:14px;color:#64748b;">Ссылка действительна 24 часа.<br>Если вы не регистрировались в CapitalView, проигнорируйте это письмо.</p>
    </td></tr>
    <tr><td style="padding:16px 32px 24px;text-align:center;font-size:12px;color:#94a3b8;">
      &copy; CapitalView
    </td></tr>
  </table>
</body>
</html>
""".strip()


def _send_verification_smtp_sync(to_email: str, verification_link: str) -> None:
    from_addr = (Config.SMTP_FROM_EMAIL or Config.SMTP_USER).strip()
    if not from_addr:
        raise ValueError("SMTP_FROM_EMAIL или SMTP_USER должен быть задан")

    body_html = VERIFICATION_HTML_SMTP.replace("{link}", verification_link)
    msg = EmailMessage()
    msg["Subject"] = "Подтверждение email — CapitalView"
    msg["From"] = f"{Config.SMTP_FROM_NAME} <{from_addr}>"
    msg["To"] = to_email
    msg.set_content(
        "Подтвердите регистрацию в CapitalView, открыв это письмо в почтовом клиенте с HTML."
    )
    msg.add_alternative(body_html, subtype="html")

    context = ssl.create_default_context()
    host = Config.SMTP_HOST
    port = Config.SMTP_PORT
    user = Config.SMTP_USER
    password = Config.SMTP_PASSWORD

    if Config.SMTP_USE_IMPLICIT_SSL:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.starttls(context=context)
            smtp.login(user, password)
            smtp.send_message(msg)


async def send_verification_email(to_email: str, verification_link: str) -> bool:
    """Письмо со ссылкой подтверждения через SMTP (Яндекс 360 и др.)."""
    if not Config.SMTP_USER or not Config.SMTP_PASSWORD:
        logger.warning("SMTP_USER или SMTP_PASSWORD не заданы")
        return False

    try:
        await asyncio.to_thread(_send_verification_smtp_sync, to_email, verification_link)
        logger.info(f"Verification email sent via SMTP to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP auth failed for {Config.SMTP_USER}: {e}")
        return False
    except Exception as e:
        logger.error(f"SMTP send failed to {to_email}: {e}", exc_info=True)
        return False
