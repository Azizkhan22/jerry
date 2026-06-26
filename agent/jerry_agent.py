import sqlite3
import traceback

from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver

import config
from tools import ALL_TOOLS
from tools.memory_tools import (
    fetch_contact,
    fetch_email_preferences,
    fetch_important,
    fetch_scheduling_preferences,
    fetch_task_history,
    store_contact,
    store_email_preference,
    store_important,
    store_scheduling_preference,
    store_task,
)

SYSTEM_PROMPT = f"""You are Jerry, {config.USER_NAME}'s personal assistant.
You are a chat/voice assistant — keep responses concise and conversational.
You can use markdown formatting in your responses: **bold**, *italic*,
bullet lists, numbered lists, and headings when they help readability.

CAPABILITIES:
1. Date & time — check the current date, time, and day of the week.
2. Email — search, read, summarize, and send emails (with optional file
   attachments).
3. Follow-up tracking — track sent emails and alert when a reply hasn't
   arrived within a configurable number of days. After sending an
   important email, automatically track it for follow-up.
4. Calendar — view upcoming events and create new events or reminders.
5. Smart scheduling — find free time slots on any day within working
   hours, then book a meeting in one of those slots.
6. Tasks — view, create, and manage tasks with optional due dates.
7. Task prioritization — analyze pending tasks, calendar, and emails
   together and recommend what to focus on first based on urgency and
   importance.
8. Daily briefing — generate a morning summary covering today's
   calendar, unread emails, and pending tasks in one view.
9. Google Drive — search for files, read/summarize documents (Docs,
   Sheets, text files), list folders, and move files between folders
   to auto-organize.
10. Persistent memory — silently remember user preferences, contacts,
    completed tasks, and important notes across conversations.

HOW TO WORK:
- When a request needs multiple steps, plan your approach, then execute
  every step in sequence — don't stop halfway. Use as many tools as
  needed to fully complete the request.
- For anything involving dates or scheduling, check the current date and
  time first.
- When writing an email, scheduling, or a person is mentioned — check
  memory for relevant preferences or contact info, BUT only if you don't
  already have that context in the current conversation. Don't re-fetch
  what you already know.
- When possible, call multiple tools at once rather than one at a time.
- When the user states a preference, describes a contact, or says
  "remember this" — store it silently. Never mention that you stored it.
- After sending an important email, track it for follow-up automatically.
- If the user attached a file, its path appears as
  "[Attached file available at: ...]" — use that exact path when sending.
- Confirm before sending an email or creating an event if any detail
  is ambiguous.
- When summarizing a document or email, read the full content first,
  then summarize in your own words — don't just echo the text.
- For smart scheduling: find free slots first, present options, then
  create the event once the user picks a time.

FOLLOW-UP SUGGESTIONS:
After completing a task, suggest 1-2 short related follow-up actions based
on what was just done and any relevant context from memory. Keep suggestions
brief and natural. Skip if nothing relevant comes to mind.
Examples:
- After sending an email: "Want me to track this for follow-up?"
- After checking calendar: "You have a task due that day — want to see it?"
- After a briefing: "Want me to prioritize what to tackle first?"
- After reading a Drive doc: "Want me to draft a reply based on this?"
"""

_llm = ChatGroq(model=config.GROQ_MODEL, api_key=config.GROQ_API_KEY, temperature=0.3)

_conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
_checkpointer = SqliteSaver(_conn)

all_tools = ALL_TOOLS + [
    store_email_preference,
    store_contact,
    store_scheduling_preference,
    store_task,
    store_important,
    fetch_email_preferences,
    fetch_contact,
    fetch_scheduling_preferences,
    fetch_task_history,
    fetch_important,
]

TOOL_FRIENDLY_NAMES = {
    "get_current_datetime": "Checking the time",
    "list_recent_emails": "Looking through emails",
    "read_email": "Reading email",
    "send_email": "Sending email",
    "get_calendar_events": "Checking calendar",
    "create_calendar_event": "Creating event",
    "list_tasks": "Looking at tasks",
    "create_task": "Creating task",
    "track_followup": "Setting up follow-up",
    "check_followups": "Checking follow-ups",
    "remove_followup": "Removing follow-up",
    "get_daily_briefing": "Preparing your briefing",
    "search_drive_files": "Searching Drive",
    "read_drive_file": "Reading document",
    "move_drive_file": "Organizing files",
    "list_drive_folders": "Browsing folders",
    "find_free_slots": "Finding free time",
    "get_priorities": "Analyzing priorities",
    "store_email_preference": "Noting preference",
    "store_contact": "Saving contact info",
    "store_scheduling_preference": "Noting preference",
    "store_task": "Logging task",
    "store_important": "Remembering that",
    "fetch_email_preferences": "Recalling preferences",
    "fetch_contact": "Looking up contact",
    "fetch_scheduling_preferences": "Checking preferences",
    "fetch_task_history": "Checking past work",
    "fetch_important": "Recalling notes",
}

agent = create_agent(
    model=_llm,
    tools=all_tools,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=_checkpointer,
)


def stream_chat(user_id, message: str, event_queue):
    """Stream agent execution events into *event_queue*.

    Each item is a dict: {"type": "tool_start"|"tool_end"|"response"|"error", ...}.
    A final ``None`` sentinel is NOT pushed here — the caller adds it."""
    run_config = {"configurable": {"thread_id": str(user_id)}}
    try:
        for chunk in agent.stream(
            {"messages": [{"role": "user", "content": message}]},
            config=run_config,
            stream_mode="updates",
        ):
            for node_name, node_output in chunk.items():
                messages = node_output.get("messages", [])
                if node_name == "model":
                    for msg in messages:
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tc in msg.tool_calls:
                                friendly = TOOL_FRIENDLY_NAMES.get(
                                    tc.get("name", ""), "Working"
                                )
                                event_queue.put({"type": "tool_start", "name": friendly})
                        elif hasattr(msg, "content") and msg.content:
                            event_queue.put({"type": "response", "content": msg.content})
                elif node_name == "tools":
                    for msg in messages:
                        name = getattr(msg, "name", "")
                        friendly = TOOL_FRIENDLY_NAMES.get(name, "Working")
                        event_queue.put({"type": "tool_end", "name": friendly})
    except Exception:
        traceback.print_exc()
        event_queue.put({
            "type": "error",
            "content": "Sorry, I ran into an issue handling that — could you try rephrasing, or ask again?",
        })


def chat(user_id, message: str) -> str:
    """Send a message to Jerry and return its text reply. Conversation
    history persists per user_id across restarts (SQLite-backed).

    If the underlying model or a tool call fails (e.g. a malformed tool
    call rejected by Groq), this returns a friendly message instead of
    raising, so the web UI shows something useful instead of a 500.
    The full error is still printed to the console for debugging."""
    run_config = {"configurable": {"thread_id": str(user_id)}}
    try:
        result = agent.invoke({"messages": [{"role": "user", "content": message}]}, config=run_config)
        return result["messages"][-1].content
    except Exception:
        traceback.print_exc()
        return "Sorry, I ran into an issue handling that - could you try rephrasing, or ask again?"


def get_history(thread_id) -> list[dict]:
    """Return the conversation so far for thread_id as a list of
    {"role": "user"|"assistant", "content": str} dicts, for rendering in a UI."""
    run_config = {"configurable": {"thread_id": str(thread_id)}}
    snapshot = agent.get_state(run_config)
    messages = (snapshot.values or {}).get("messages", [])

    history = []
    for m in messages:
        role = {"human": "user", "ai": "assistant"}.get(getattr(m, "type", None))
        content = m.content
        if role and isinstance(content, str) and content.strip():
            history.append({"role": role, "content": content})
    return history


def reset_thread(thread_id) -> None:
    """Permanently delete all stored messages/checkpoints for thread_id.
    Used by "New chat" to start Jerry's context completely fresh - both
    in the UI and in what gets sent to the LLM on the next message."""
    _checkpointer.delete_thread(str(thread_id))
