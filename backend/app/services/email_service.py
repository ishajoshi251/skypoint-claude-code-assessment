"""
Email service — sends via SMTP (MailHog in dev, real SMTP in prod).

Uses asyncio.to_thread to keep the event loop unblocked (smtplib is sync).
All functions take plain Python types so this module has zero FastAPI imports.
"""
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


def _send_sync(
    to_address: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> None:
    """Blocking SMTP send — called from a thread pool via asyncio.to_thread."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_ADDRESS}>"
    msg["To"] = to_address

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.sendmail(settings.EMAILS_FROM_ADDRESS, to_address, msg.as_string())


async def send_email(
    to_address: str,
    subject: str,
    html_body: str,
    text_body: str = "",
) -> bool:
    """Async wrapper — returns True on success, False on failure (non-fatal)."""
    if not text_body:
        # Strip tags for a basic plain-text fallback
        import re
        text_body = re.sub(r"<[^>]+>", "", html_body)

    try:
        await asyncio.to_thread(_send_sync, to_address, subject, html_body, text_body)
        logger.info("Email sent", to=to_address, subject=subject)
        return True
    except Exception as exc:
        logger.warning("Email send failed", to=to_address, error=str(exc))
        return False


# ---------------------------------------------------------------------------
# Invite email templates
# ---------------------------------------------------------------------------

def build_invite_email(
    *,
    candidate_name: str,
    job_title: str,
    company_name: str,
    matched_skills: list[str],
    match_score: float,
    custom_message: str | None = None,
) -> tuple[str, str]:
    """Return (subject, html_body) for a personalised invite email."""
    subject = f"You're a {int(match_score)}% match for {job_title} at {company_name}!"

    skills_list = (
        "".join(f"<li>{s}</li>" for s in matched_skills)
        if matched_skills
        else "<li>Your profile skills</li>"
    )

    personal_note = (
        f"<p><em>{custom_message}</em></p>" if custom_message else ""
    )

    html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
  <div style="background: #4f46e5; padding: 24px; border-radius: 8px 8px 0 0;">
    <h1 style="color: white; margin: 0; font-size: 24px;">TalentBridge</h1>
  </div>
  <div style="padding: 32px; background: #fff; border: 1px solid #e5e7eb; border-top: none;">
    <h2 style="color: #4f46e5;">Hi {candidate_name},</h2>
    <p>You're a <strong style="color: #4f46e5; font-size: 20px;">{int(match_score)}% match</strong>
       for the <strong>{job_title}</strong> role at <strong>{company_name}</strong>!</p>
    {personal_note}
    <p>Here's why you're a great fit — skills we found on your profile:</p>
    <ul style="background: #f9fafb; padding: 16px 16px 16px 32px; border-radius: 6px;">
      {skills_list}
    </ul>
    <p style="margin-top: 24px;">
      <a href="http://localhost:3000/jobs"
         style="background: #4f46e5; color: white; padding: 12px 24px;
                border-radius: 6px; text-decoration: none; font-weight: bold;">
        View Job &amp; Apply
      </a>
    </p>
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 32px 0;">
    <p style="color: #9ca3af; font-size: 12px;">
      You're receiving this because your profile matched our search.
      TalentBridge — intelligent hiring.
    </p>
  </div>
</body>
</html>
"""
    return subject, html_body
