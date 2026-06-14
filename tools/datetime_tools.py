from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool

import config


@tool
def get_current_datetime() -> str:
    """Get the current date and time. Call this before reasoning about
    relative dates/times like 'today', 'tomorrow', 'in an hour', or 'next
    Monday' so calendar events, tasks and reminders are scheduled correctly."""
    now = datetime.now(ZoneInfo(config.TIMEZONE))
    return now.strftime("Current date and time: %A, %Y-%m-%d %H:%M %z (%Z)")
