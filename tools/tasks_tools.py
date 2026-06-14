from langchain_core.tools import tool

from tools.google_auth import get_service


@tool
def list_tasks(show_completed: bool = False) -> str:
    """List tasks from the user's default Google Tasks list."""
    service = get_service("tasks", "v1")
    items = service.tasks().list(tasklist="@default", showCompleted=show_completed).execute().get("items", [])

    if not items:
        return "No tasks found."

    lines = []
    for item in items:
        status = "done" if item.get("status") == "completed" else "pending"
        due = item.get("due", "no due date")
        lines.append(
            f"ID: {item['id']} | {status} | {item.get('title')} | "
            f"Due: {due} | Notes: {item.get('notes', '')}"
        )
    return "\n".join(lines)


@tool
def create_task(title: str, due_date: str = "", notes: str = "") -> str:
    """Create a task in Google Tasks. due_date should be 'YYYY-MM-DD'
    (e.g. '2026-06-15'), or empty for no due date."""
    service = get_service("tasks", "v1")

    body = {"title": title, "notes": notes}
    if due_date:
        body["due"] = f"{due_date}T00:00:00.000Z"

    service.tasks().insert(tasklist="@default", body=body).execute()
    return f"Task '{title}' created" + (f", due {due_date}." if due_date else ".")
