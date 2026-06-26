import io

from langchain_core.tools import tool

from tools._coerce import coerce_int
from tools.google_auth import get_service


def _drive_service():
    return get_service("drive", "v3")


@tool
def search_drive_files(query: str, max_results: int | str = 10) -> str:
    """Search Google Drive for files by name, content, or type.
    The query uses Google Drive search syntax — examples:
      'name contains "report"'
      'mimeType = "application/pdf"'
      'fullText contains "quarterly revenue"'
      '"folder_id" in parents'
    Returns each file's ID, name, type, and last-modified date.

    Args:
        query: Google Drive search query string.
        max_results: maximum number of files to return (default 10).
    """
    max_results = coerce_int(max_results, 10)
    service = _drive_service()
    results = (
        service.files()
        .list(
            q=query,
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime, parents)",
            orderBy="modifiedTime desc",
        )
        .execute()
    )
    files = results.get("files", [])
    if not files:
        return "No files found matching that query."

    lines = []
    for f in files:
        lines.append(
            f"ID: {f['id']}\n"
            f"Name: {f['name']}\n"
            f"Type: {f['mimeType']}\n"
            f"Modified: {f.get('modifiedTime', '?')}"
        )
    return "\n\n".join(lines)


@tool
def read_drive_file(file_id: str) -> str:
    """Read the text content of a Google Drive file. Works with Google Docs
    (exported as plain text), Google Sheets (exported as CSV), and plain
    text files. For binary files like PDFs, returns the file metadata
    instead. Use this to summarize or draft replies based on a document.

    Args:
        file_id: the Google Drive file ID (from search_drive_files).
    """
    service = _drive_service()
    meta = service.files().get(fileId=file_id, fields="name, mimeType").execute()
    mime = meta["mimeType"]
    name = meta["name"]

    export_map = {
        "application/vnd.google-apps.document": ("text/plain", "txt"),
        "application/vnd.google-apps.spreadsheet": ("text/csv", "csv"),
        "application/vnd.google-apps.presentation": ("text/plain", "txt"),
    }

    if mime in export_map:
        export_mime, _ = export_map[mime]
        content = (
            service.files()
            .export(fileId=file_id, mimeType=export_mime)
            .execute()
        )
        text = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else str(content)
        if len(text) > 8000:
            text = text[:8000] + "\n\n... [truncated — document is very long]"
        return f"=== {name} ===\n\n{text}"

    text_types = ("text/plain", "text/csv", "text/html", "application/json", "text/markdown")
    if any(mime.startswith(t) for t in text_types):
        content = service.files().get_media(fileId=file_id).execute()
        text = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else str(content)
        if len(text) > 8000:
            text = text[:8000] + "\n\n... [truncated]"
        return f"=== {name} ===\n\n{text}"

    return (
        f"File: {name}\nType: {mime}\n\n"
        f"This is a binary file and cannot be displayed as text. "
        f"You can share a Google Drive link with the user instead."
    )


@tool
def move_drive_file(file_id: str, destination_folder_id: str) -> str:
    """Move a file to a different folder in Google Drive. Use this to
    auto-organize files — for example, moving invoices into a 'Finance'
    folder or meeting notes into a 'Meetings' folder.

    Args:
        file_id: the Google Drive file ID to move.
        destination_folder_id: the ID of the target folder.
    """
    service = _drive_service()

    file_meta = service.files().get(fileId=file_id, fields="name, parents").execute()
    name = file_meta["name"]
    old_parents = ",".join(file_meta.get("parents", []))

    service.files().update(
        fileId=file_id,
        addParents=destination_folder_id,
        removeParents=old_parents,
        fields="id, parents",
    ).execute()

    return f"Moved '{name}' to the specified folder."


@tool
def list_drive_folders(max_results: int | str = 20) -> str:
    """List folders in Google Drive. Useful for finding the right
    destination before moving a file with move_drive_file.

    Args:
        max_results: maximum number of folders to return (default 20).
    """
    max_results = coerce_int(max_results, 20)
    service = _drive_service()
    results = (
        service.files()
        .list(
            q="mimeType = 'application/vnd.google-apps.folder' and trashed = false",
            pageSize=max_results,
            fields="files(id, name, modifiedTime)",
            orderBy="modifiedTime desc",
        )
        .execute()
    )
    folders = results.get("files", [])
    if not folders:
        return "No folders found in Drive."

    lines = [f"ID: {f['id']} | {f['name']}" for f in folders]
    return "DRIVE FOLDERS:\n" + "\n".join(lines)
