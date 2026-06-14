from datetime import datetime, timezone

from langchain_core.tools import tool

from tools._coerce import coerce_int
from tools.google_auth import get_service


@tool
def get_calendar_events(time_min: str = "", time_max: str = "", max_results: int | str = 10) -> str:
    """Get events from Google Calendar between time_min and time_max
    (ISO 8601 with timezone offset, e.g. '2026-06-15T00:00:00+05:00').
    If both are empty, returns the next upcoming events from right now.
    Always call get_current_datetime first to correctly resolve 'today',
    'tomorrow', 'this week', etc. before calling this."""
    max_results = coerce_int(max_results, 10)
    service = get_service("calendar", "v3")

    params = {
        "calendarId": "primary",
        "maxResults": max_results,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    params["timeMin"] = time_min or datetime.now(timezone.utc).isoformat()
    if time_max:
        params["timeMax"] = time_max

    events = service.events().list(**params).execute().get("items", [])

    if not events:
        return "No events found in that range."

    lines = []
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        end = event["end"].get("dateTime", event["end"].get("date"))
        lines.append(
            f"ID: {event['id']}\n"
            f"Title: {event.get('summary', '(no title)')}\n"
            f"Start: {start}\n"
            f"End: {end}\n"
            f"Description: {event.get('description', '')}"
        )
    return "\n\n".join(lines)


@tool
def create_calendar_event(summary: str, start_time: str, end_time: str, description: str = "") -> str:
    """Create a Google Calendar event - also useful as a timed reminder
    (it adds a 10-minute-before popup reminder automatically). start_time
    and end_time must be ISO 8601 with timezone offset, e.g.
    '2026-06-15T14:00:00+05:00'. Call get_current_datetime first to resolve
    relative dates like 'tomorrow' or 'next Monday'."""
    service = get_service("calendar", "v3")

    event_body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time},
        "end": {"dateTime": end_time},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": 10}],
        },
    }

    created = service.events().insert(calendarId="primary", body=event_body).execute()
    return f"Event '{summary}' created from {start_time} to {end_time}. Link: {created.get('htmlLink', '')}"
