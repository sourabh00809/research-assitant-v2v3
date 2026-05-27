from __future__ import annotations

import json
import logging
import urllib.request

from .config import settings

logger = logging.getLogger(__name__)

RESEND_API = "https://api.resend.com/emails"


def send_email(to: str, subject: str, body: str) -> bool:
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set, skipping email")
        return False
    payload = json.dumps({
        "from": "Research Assistant <notifications@research.local>",
        "to": [to],
        "subject": subject,
        "text": body,
    }).encode("utf-8")
    req = urllib.request.Request(
        RESEND_API,
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        logger.info("Email sent to %s: %s (status=%s)", to, subject, resp.status)
        return True
    except Exception as exc:
        logger.warning("Failed to send email to %s: %s", to, exc)
        return False
