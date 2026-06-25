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

You can:
- Read, search and summarize emails, and send emails (optionally with one file attachment).
- Check and create Google Calendar events and reminders.
- Check and create Google Tasks.
- Mark attendance (check-in / check-out) on the internship portal.

Guidelines:
- Always call get_current_datetime before reasoning about "today", "tomorrow",
  or any relative date/time, and before scheduling anything.
- When asked to summarize an email, call read_email then summarize it in your
  own words - don't just repeat the text back.
- When asked to read/quote an email, call read_email and present the relevant part.
- If the user has attached a file, its local path appears in the message as
  "[Attached file available at: ...]" - use that exact path as attachment_path
  when calling send_email.
- Confirm with the user before sending an email, creating an event, or marking
  attendance if any detail (recipient, time, which action) is ambiguous.
- Only call mark_attendance when the user explicitly asks for it in that
  message - never on your own initiative.
- Keep responses concise and conversational; this is a chat/voice assistant.

MEMORY:
You have persistent memory. Use it proactively and silently.

STORE when:
- User states any preference → store immediately
- User describes a person → store_contact
- You finish a significant task → store_task
- User says remember this → store_important

FETCH before acting:
- Any email task → fetch_email_preferences first
- Person mentioned → fetch_contact with their name first
- Scheduling task → fetch_scheduling_preferences first
- User references past work → fetch_task_history first

Never tell the user you are storing. Always fetch before acting not after.
If fetch returns no memory, proceed normally without it.
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

agent = create_agent(
    model=_llm,
    tools=all_tools,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=_checkpointer,
)


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
