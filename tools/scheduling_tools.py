from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from langchain_core.tools import tool

import config
from tools._coerce import coerce_int
from tools.google_auth import get_service


@tool
def find_free_slots(date: str, duration_minutes: int | str = 30) -> str:
    """Find available time slots on a given day by checking the user's
    Google Calendar for gaps between events. Returns a list of free
    windows that are at least duration_minutes long, within working
    hours (9 AM to 6 PM in the user's timezone).

    Use this when the user asks to 'find a free slot', 'schedule a
    meeting when I'm free', or 'what time works this week'. After
    finding a slot, use create_calendar_event to book it.

    Args:
        date: the date to check, as 'YYYY-MM-DD' (e.g. '2026-06-25').
        duration_minutes: minimum slot length in minutes (default 30).
    """
    duration_minutes = coerce_int(duration_minutes, 30)
    tz = ZoneInfo(config.TIMEZONE)

    day_start = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=tz)
    work_start = day_start.replace(hour=9, minute=0, second=0, microsecond=0)
    work_end = day_start.replace(hour=18, minute=0, second=0, microsecond=0)

    service = get_service("calendar", "v3")
    events = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=work_start.isoformat(),
            timeMax=work_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=50,
        )
        .execute()
        .get("items", [])
    )

    busy = []
    for ev in events:
        start_str = ev["start"].get("dateTime")
        end_str = ev["end"].get("dateTime")
        if not start_str or not end_str:
            busy.append((work_start, work_end))
            continue
        busy.append((
            datetime.fromisoformat(start_str),
            datetime.fromisoformat(end_str),
        ))
    busy.sort(key=lambda x: x[0])

    min_duration = timedelta(minutes=duration_minutes)
    free_slots = []
    cursor = work_start

    for ev_start, ev_end in busy:
        if cursor < ev_start and (ev_start - cursor) >= min_duration:
            free_slots.append((cursor, ev_start))
        if ev_end > cursor:
            cursor = ev_end

    if cursor < work_end and (work_end - cursor) >= min_duration:
        free_slots.append((cursor, work_end))

    if not free_slots:
        return f"No free slots of {duration_minutes}+ minutes on {date} (9 AM – 6 PM)."

    lines = []
    for start, end in free_slots:
        s = start.strftime("%I:%M %p")
        e = end.strftime("%I:%M %p")
        mins = int((end - start).total_seconds() // 60)
        lines.append(f"  {s} – {e}  ({mins} min free)")

    header = f"Free slots on {date} (minimum {duration_minutes} min):"
    return header + "\n" + "\n".join(lines)
