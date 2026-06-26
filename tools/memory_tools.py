from langchain_core.tools import tool
from memory import retrieve_memory, store_memory

# ── STORE TOOLS ────────────────────────────────────────────────────────────────

@tool
def store_email_preference(preference: str) -> str:
    """
    ALWAYS call this immediately when the user mentions ANYTHING about how they
    like emails written — tone (formal/casual), length, sign-off style, language,
    structure, or any writing preference. Do NOT wait. Store first, then respond.
    Example triggers: "I prefer formal emails", "keep replies short", "always CC my manager".
    """
    return store_memory(content=preference, tag="email_preference")

@tool
def store_contact(name: str, info: str) -> str:
    """
    ALWAYS call this immediately when the user mentions or describes any person —
    their role, relationship, personality, contact info, or any detail about them.
    Do NOT wait to be asked. Store first, then respond.
    Example triggers: "John is my manager", "Sara prefers Slack over email", "my client Ahmed is in Dubai".
    """
    return store_memory(content=info, tag="contact", name=name)

@tool
def store_scheduling_preference(preference: str) -> str:
    """
    ALWAYS call this immediately when the user states anything about their calendar
    or meeting habits — preferred times, meeting lengths, buffer preferences, tools used,
    days they're unavailable, or any scheduling rule.
    Do NOT wait. Store first, then respond.
    Example triggers: "I don't do meetings before 10am", "keep Fridays free", "I use Calendly".
    """
    return store_memory(content=preference, tag="scheduling_preference")

@tool
def store_task(task_summary: str) -> str:
    """
    ALWAYS call this after completing any meaningful task — drafting an email,
    scheduling a meeting, summarizing something, or taking any action on the user's behalf.
    Log what was done so it can be referenced later. Store before ending your response.
    """
    return store_memory(content=task_summary, tag="task")

@tool
def store_important(content: str) -> str:
    """
    ALWAYS call this when the user says 'remember this', 'note that', 'keep in mind',
    or flags something as important. Also call proactively when critical information
    comes up that doesn't fit other categories.
    Do NOT rely on memory — store it immediately.
    """
    return store_memory(content=content, tag="important")

# ── FETCH TOOLS ────────────────────────────────────────────────────────────────

@tool
def fetch_email_preferences(query: str) -> str:
    """
    ALWAYS call this BEFORE drafting, replying to, or reviewing any email.
    Retrieve the user's stored writing and tone preferences so the email matches their style.
    Call this even if you think you already know their preferences.
    """
    return retrieve_memory(tag="email_preference", query=query)

@tool
def fetch_contact(name: str) -> str:
    """
    ALWAYS call this when any person is mentioned by name before responding about them.
    Retrieve stored context — role, relationship, preferences, notes — so your response is informed.
    Call this even for people mentioned casually or in passing.
    """
    return retrieve_memory(tag="contact", query=name, name=name)

@tool
def fetch_scheduling_preferences(query: str) -> str:
    """
    ALWAYS call this BEFORE creating, suggesting, or modifying any calendar event or meeting.
    Retrieve the user's stored scheduling rules and preferences first.
    """
    return retrieve_memory(tag="scheduling_preference", query=query)

@tool
def fetch_task_history(query: str) -> str:
    """
    ALWAYS call this when the user references past work, asks what was done before,
    or when context about prior actions would help. Retrieve before responding.
    """
    return retrieve_memory(tag="task", query=query)

@tool
def fetch_important(query: str) -> str:
    """
    ALWAYS call this when the user references something they asked you to remember,
    or when recalled context might be relevant. Retrieve before responding.
    """
    return retrieve_memory(tag="important", query=query)