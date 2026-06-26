from tools.datetime_tools import get_current_datetime
from tools.email_tools import list_recent_emails, read_email, send_email
from tools.calendar_tools import get_calendar_events, create_calendar_event
from tools.tasks_tools import list_tasks, create_task
from tools.followup_tools import track_followup, check_followups, remove_followup
from tools.briefing_tools import get_daily_briefing
from tools.drive_tools import search_drive_files, read_drive_file, move_drive_file, list_drive_folders
from tools.scheduling_tools import find_free_slots
from tools.prioritization_tools import get_priorities

# ----------------------------------------------------------------------
# Adding a new task/tool later:
#   1. Create tools/your_feature.py with one or more functions decorated
#      with @tool (from langchain_core.tools) and a clear docstring -
#      the docstring is how Jerry decides when to use it.
#   2. Import the function(s) here.
#   3. Add it to ALL_TOOLS below.
# That's it - no other code needs to change.
# ----------------------------------------------------------------------

ALL_TOOLS = [
    # Date & time
    get_current_datetime,
    # Email
    list_recent_emails,
    read_email,
    send_email,
    # Calendar
    get_calendar_events,
    create_calendar_event,
    # Tasks
    list_tasks,
    create_task,
    # Follow-up tracker
    track_followup,
    check_followups,
    remove_followup,
    # Daily briefing
    get_daily_briefing,
    # Google Drive
    search_drive_files,
    read_drive_file,
    move_drive_file,
    list_drive_folders,
    # Smart scheduling
    find_free_slots,
    # Task prioritization
    get_priorities,
]
