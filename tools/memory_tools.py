from langchain_core.tools import tool

from memory import retrieve_memory, store_memory


@tool
def store_email_preference(preference: str) -> str:
    """Call when user states email tone, style, or writing preferences"""
    return store_memory(content=preference, tag="email_preference")


@tool
def store_contact(name: str, info: str) -> str:
    """Call when user introduces or describes a person"""
    return store_memory(content=info, tag="contact", name=name)


@tool
def store_scheduling_preference(preference: str) -> str:
    """Call when user states calendar or meeting preferences"""
    return store_memory(content=preference, tag="scheduling_preference")


@tool
def store_task(task_summary: str) -> str:
    """Call after completing any significant task to log what was done"""
    return store_memory(content=task_summary, tag="task")


@tool
def store_important(content: str) -> str:
    """Call when user says remember this or something important comes up"""
    return store_memory(content=content, tag="important")


@tool
def fetch_email_preferences(query: str) -> str:
    """Call before writing or replying to any email"""
    return retrieve_memory(tag="email_preference", query=query)


@tool
def fetch_contact(name: str) -> str:
    """Call when a person is mentioned and you need context about them"""
    return retrieve_memory(tag="contact", query=name, name=name)


@tool
def fetch_scheduling_preferences(query: str) -> str:
    """Call before creating events or scheduling anything"""
    return retrieve_memory(tag="scheduling_preference", query=query)


@tool
def fetch_task_history(query: str) -> str:
    """Call when user references past work or asks what was done before"""
    return retrieve_memory(tag="task", query=query)


@tool
def fetch_important(query: str) -> str:
    """Call when user references something they asked you to remember"""
    return retrieve_memory(tag="important", query=query)
