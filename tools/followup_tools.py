import json
import os
from datetime import datetime, timezone

from langchain_core.tools import tool

import config
from tools.google_auth import get_service

_FOLLOWUPS_PATH = os.path.join(config.DATA_DIR, "followups.json")


def _load_followups() -> list[dict]:
    if os.path.exists(_FOLLOWUPS_PATH):
        with open(_FOLLOWUPS_PATH, "r") as f:
            return json.load(f)
    return []


def _save_followups(followups: list[dict]):
    with open(_FOLLOWUPS_PATH, "w") as f:
        json.dump(followups, f, indent=2)


@tool
def track_followup(to: str, subject: str) -> str:
    """Record a sent email for follow-up tracking. Call this right after
    sending an important email where you expect a reply. Stores the
    recipient, subject, and date so check_followups can later detect
    emails that never got a reply.

    Args:
        to: the recipient email address.
        subject: the email subject line.
    """
    followups = _load_followups()
    followups.append({
        "to": to,
        "subject": subject,
        "sent_date": datetime.now(timezone.utc).isoformat(),
        "resolved": False,
    })
    _save_followups(followups)
    return f"Tracking follow-up: email to {to} about '{subject}'."


@tool
def check_followups(days_threshold: int = 2) -> str:
    """Check all tracked sent emails and report which ones have NOT received
    a reply within the given number of days. Searches Gmail for replies
    matching each tracked subject and recipient. Automatically marks
    follow-ups as resolved when a reply is found.

    Args:
        days_threshold: number of days without a reply before flagging (default 2).
    """
    followups = _load_followups()
    if not followups:
        return "No emails are being tracked for follow-up."

    service = get_service("gmail", "v1")
    now = datetime.now(timezone.utc)
    pending = []
    changed = False

    for entry in followups:
        if entry.get("resolved"):
            continue

        sent_dt = datetime.fromisoformat(entry["sent_date"])
        age_days = (now - sent_dt).days

        query = f"from:{entry['to']} subject:{entry['subject']}"
        try:
            results = service.users().messages().list(
                userId="me", maxResults=1, q=query,
            ).execute()
            if results.get("messages"):
                entry["resolved"] = True
                changed = True
                continue
        except Exception:
            pass

        if age_days >= days_threshold:
            pending.append(
                f"- {entry['to']} | \"{entry['subject']}\" | sent {age_days} day(s) ago"
            )

    if changed:
        _save_followups(followups)

    if not pending:
        return "All tracked emails have been replied to — nothing overdue."

    header = f"Emails with no reply (>= {days_threshold} days):"
    return header + "\n" + "\n".join(pending)


@tool
def remove_followup(to: str, subject: str) -> str:
    """Stop tracking a follow-up. Use when the user says they no longer
    need to follow up on a particular email.

    Args:
        to: the recipient email address.
        subject: the email subject (partial match is fine).
    """
    followups = _load_followups()
    subject_lower = subject.lower()
    remaining = [
        f for f in followups
        if not (f["to"].lower() == to.lower() and subject_lower in f["subject"].lower())
    ]
    removed = len(followups) - len(remaining)
    if removed == 0:
        return f"No matching follow-up found for {to} about '{subject}'."
    _save_followups(remaining)
    return f"Removed {removed} follow-up(s) for {to} about '{subject}'."
