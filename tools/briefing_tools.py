from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from langchain_core.tools import tool

import config
from tools.google_auth import get_service


@tool
def get_daily_briefing() -> str:
    """Generate a morning briefing that summarizes today's emails, calendar
    events, and pending tasks in one call. Returns a structured overview so
    the assistant can present a clear, prioritized start to the day.
    Call this when the user asks for a briefing, morning summary, or
    'what does my day look like'.
    """
    tz = ZoneInfo(config.TIMEZONE)
    now = datetime.now(tz)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    start_iso = day_start.isoformat()
    end_iso = day_end.isoformat()

    sections = []

    # --- Calendar events ---
    try:
        cal = get_service("calendar", "v3")
        events = (
            cal.events()
            .list(
                calendarId="primary",
                timeMin=start_iso,
                timeMax=end_iso,
                singleEvents=True,
                orderBy="startTime",
                maxResults=20,
            )
            .execute()
            .get("items", [])
        )
        if events:
            lines = []
            for ev in events:
                start = ev["start"].get("dateTime", ev["start"].get("date"))
                end = ev["end"].get("dateTime", ev["end"].get("date"))
                lines.append(f"  - {ev.get('summary', '(no title)')} | {start} to {end}")
            sections.append("CALENDAR (" + str(len(events)) + " events):\n" + "\n".join(lines))
        else:
            sections.append("CALENDAR: No events today.")
    except Exception as e:
        sections.append(f"CALENDAR: Could not fetch events ({e}).")

    # --- Unread emails ---
    try:
        gmail = get_service("gmail", "v1")
        results = gmail.users().messages().list(
            userId="me", maxResults=10, q="is:unread",
        ).execute()
        messages = results.get("messages", [])
        if messages:
            batch_results = {}

            def _on_email(request_id, response, exception):
                if exception is None:
                    batch_results[request_id] = response

            batch = gmail.new_batch_http_request(callback=_on_email)
            for msg in messages:
                batch.add(
                    gmail.users().messages().get(
                        userId="me", id=msg["id"], format="metadata",
                        metadataHeaders=["From", "Subject"],
                    ),
                    request_id=msg["id"],
                )
            batch.execute()

            lines = []
            for msg in messages:
                meta = batch_results.get(msg["id"])
                if not meta:
                    continue
                headers = {h["name"]: h["value"] for h in meta["payload"]["headers"]}
                lines.append(f"  - From: {headers.get('From', '?')} | {headers.get('Subject', '(no subject)')}")
            sections.append("UNREAD EMAILS (" + str(len(messages)) + "):\n" + "\n".join(lines))
        else:
            sections.append("UNREAD EMAILS: Inbox zero — no unread messages.")
    except Exception as e:
        sections.append(f"UNREAD EMAILS: Could not fetch emails ({e}).")

    # --- Pending tasks ---
    try:
        tasks_svc = get_service("tasks", "v1")
        items = (
            tasks_svc.tasks()
            .list(tasklist="@default", showCompleted=False)
            .execute()
            .get("items", [])
        )
        if items:
            lines = []
            for item in items:
                due = item.get("due", "no due date")
                lines.append(f"  - {item.get('title', '(untitled)')} | Due: {due}")
            sections.append("PENDING TASKS (" + str(len(items)) + "):\n" + "\n".join(lines))
        else:
            sections.append("PENDING TASKS: All clear — nothing pending.")
    except Exception as e:
        sections.append(f"PENDING TASKS: Could not fetch tasks ({e}).")

    date_str = now.strftime("%A, %B %d, %Y")
    return f"DAILY BRIEFING — {date_str}\n\n" + "\n\n".join(sections)
