# app/core/template_helpers.py
"""
Jinja2 template filters and context processors.
Registered on the Jinja2 environment in pages.py.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo


def format_meeting_time(dt: datetime, tz_name: str = "Europe/London") -> str:
    """
    Convert a UTC datetime to a human-readable local time string.
    e.g. "Saturday 12 April 2026 at 18:00 (UK time)"
    """
    try:
        local_tz = ZoneInfo(tz_name)
        local_dt = dt.astimezone(local_tz)
        return local_dt.strftime("%-d %B %Y at %H:%M")
    except Exception:
        return dt.strftime("%d %B %Y at %H:%M UTC")


def meeting_state(meeting) -> str:
    """
    Return the display state of a meeting object.

    States:
        cancelled   — is_cancelled is True
        imminent    — starts within 30 minutes
        upcoming    — scheduled in the future
        past        — start_at has passed
        none        — meeting is None
    """
    if meeting is None:
        return "none"
    if meeting.is_cancelled:
        return "cancelled"

    now = datetime.now(timezone.utc)
    diff = meeting.start_at - now

    if diff <= timedelta(minutes=30) and diff >= timedelta(minutes=-120):
        return "imminent"
    if diff > timedelta(minutes=30):
        return "upcoming"
    return "past"


def mask_email(email: str) -> str:
    """
    Partially mask an email address for display in admin panel.
    jane.doe@example.com → ja*****@ex*****.com
    """
    if not email or "@" not in email:
        return email

    local, domain = email.split("@", 1)
    masked_local = local[:2] + "*" * max(len(local) - 2, 3)

    dot_pos = domain.rfind(".")
    if dot_pos > 2:
        domain_name = domain[:dot_pos]
        tld = domain[dot_pos:]
        masked_domain = domain_name[:2] + "*" * max(len(domain_name) - 2, 3) + tld
    else:
        masked_domain = domain

    return f"{masked_local}@{masked_domain}"


def pluralise(count: int, singular: str, plural: str) -> str:
    """Return singular or plural form based on count."""
    return singular if count == 1 else plural


def suggestion_status_label(status: str) -> str:
    """Human-readable suggestion status."""
    return {
        "pending": "Pending review",
        "approved": "Added to queue",
        "rejected": "Not selected",
    }.get(status, status)