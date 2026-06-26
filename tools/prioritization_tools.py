from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from langchain_core.tools import tool

import config
from tools.google_auth import get_service


@tool
def get_priorities() -> str:
    """Gather pending tasks, today's calendar events, and recent unread
    emails into a single structured view so the assistant can analyze
    urgency and importance and suggest what to work on first.

    Call this when the user asks 'what should I focus on', 'prioritize
    my day', 'what's most important right now', or similar.
    The assistant should then reason over the data and present a
    prioritized recommendation.
    """
    tz = ZoneInfo(config.TIMEZONE)
    now = datetime.now(tz)
    day_end = now.replace(hour=23, minute=59, second=59, microsecond=0)

    sections = []

    # --- Pending tasks with due dates ---
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
                due = item.get("due", "")
                overdue = ""
                if due:
                    try:
                        due_dt = datetime.fromisoformat(due.replace("Z", "+00:00"))
                        if due_dt.date() < now.date():
                            overdue = " [OVERDUE]"
                        elif due_dt.date() == now.date():
                            overdue = " [DUE TODAY]"
                    except ValueError:
                        pass
                due_display = due if due else "no due date"
                lines.append(
                    f"  - {item.get('title', '(untitled)')} | Due: {due_display}{overdue}"
                    + (f" | Notes: {item['notes']}" if item.get("notes") else "")
                )
            sections.append("PENDING TASKS (" + str(len(items)) + "):\n" + "\n".join(lines))
        else:
            sections.append("PENDING TASKS: None.")
    except Exception as e:
        sections.append(f"PENDING TASKS: Error ({e}).")

    # --- Today's remaining events ---
    try:
        cal = get_service("calendar", "v3")
        events = (
            cal.events()
            .list(
                calendarId="primary",
                timeMin=now.isoformat(),
                timeMax=day_end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                maxResults=15,
            )
            .execute()
            .get("items", [])
        )
        if events:
            lines = []
            for ev in events:
                start = ev["start"].get("dateTime", ev["start"].get("date"))
                lines.append(f"  - {ev.get('summary', '(no title)')} at {start}")
            sections.append("UPCOMING TODAY (" + str(len(events)) + " events):\n" + "\n".join(lines))
        else:
            sections.append("UPCOMING TODAY: No more events.")
    except Exception as e:
        sections.append(f"UPCOMING TODAY: Error ({e}).")

    # --- Unread emails (flagged / important first) ---
    try:
        gmail = get_service("gmail", "v1")
        for label, query in [("IMPORTANT/STARRED", "is:unread (is:important OR is:starred)"),
                             ("OTHER UNREAD", "is:unread -is:important -is:starred")]:
            results = gmail.users().messages().list(
                userId="me", maxResults=5, q=query,
            ).execute()
            messages = results.get("messages", [])
            if messages:
                batch_results = {}

                def _on_msg(request_id, response, exception):
                    if exception is None:
                        batch_results[request_id] = response

                batch = gmail.new_batch_http_request(callback=_on_msg)
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
                    lines.append(
                        f"  - {headers.get('From', '?')} | {headers.get('Subject', '(no subject)')}"
                    )
                sections.append(f"{label} EMAILS ({len(messages)}):\n" + "\n".join(lines))
    except Exception as e:
        sections.append(f"EMAILS: Error ({e}).")

    return (
        "PRIORITY DATA — use this to recommend what the user should focus on.\n"
        "Consider: overdue items first, then due-today, then meetings coming up, "
        "then important emails, then remaining tasks.\n\n"
        + "\n\n".join(sections)
    )
