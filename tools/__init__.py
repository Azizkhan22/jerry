from tools.datetime_tools import get_current_datetime
from tools.email_tools import list_recent_emails, read_email, send_email
from tools.calendar_tools import get_calendar_events, create_calendar_event
from tools.tasks_tools import list_tasks, create_task
from tools.attendance_tools import mark_attendance

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
    get_current_datetime,
    list_recent_emails,
    read_email,
    send_email,
    get_calendar_events,
    create_calendar_event,
    list_tasks,
    create_task,
    mark_attendance,
]
