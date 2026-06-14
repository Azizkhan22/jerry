import base64
import mimetypes
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from langchain_core.tools import tool

from tools._coerce import coerce_int
from tools.google_auth import get_service


def _extract_body(payload: dict) -> str:
    """Recursively pull plain-text content out of a Gmail message payload,
    falling back to a crude HTML-tag strip if no plain-text part exists."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    if "parts" in payload:
        parts_text = [_extract_body(part) for part in payload["parts"]]
        combined = "\n".join(t for t in parts_text if t)
        if combined.strip():
            return combined

    if payload.get("mimeType") == "text/html" and payload.get("body", {}).get("data"):
        html = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
        return re.sub(r"<[^>]+>", " ", html)

    return ""


@tool
def list_recent_emails(max_results: int | str = 10, query: str = "is:unread") -> str:
    """List recent Gmail emails. 'query' is a Gmail search query, e.g.
    'is:unread', 'from:boss@company.com', 'subject:invoice', or '' for all
    recent mail. Returns each email's ID, sender, subject, date and a short
    snippet. Use read_email with the ID to get the full body."""
    max_results = coerce_int(max_results, 10)
    service = get_service("gmail", "v1")
    results = service.users().messages().list(userId="me", maxResults=max_results, q=query).execute()
    messages = results.get("messages", [])

    if not messages:
        return "No emails found matching that query."

    lines = []
    for msg in messages:
        meta = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()
        headers = {h["name"]: h["value"] for h in meta["payload"]["headers"]}
        lines.append(
            f"ID: {msg['id']}\n"
            f"From: {headers.get('From', 'Unknown')}\n"
            f"Subject: {headers.get('Subject', '(no subject)')}\n"
            f"Date: {headers.get('Date', '')}\n"
            f"Snippet: {meta.get('snippet', '')}"
        )
    return "\n\n".join(lines)


@tool
def read_email(email_id: str) -> str:
    """Read the full content (sender, subject, date, full body) of one
    email by its ID, as returned by list_recent_emails."""
    service = get_service("gmail", "v1")
    msg = service.users().messages().get(userId="me", id=email_id, format="full").execute()

    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    body = _extract_body(msg["payload"]).strip()

    return (
        f"From: {headers.get('From', 'Unknown')}\n"
        f"Subject: {headers.get('Subject', '(no subject)')}\n"
        f"Date: {headers.get('Date', '')}\n\n"
        f"{body}"
    )


@tool
def send_email(to: str, subject: str, body: str, attachment_path: str = "") -> str:
    """Send an email via Gmail. If the user attached a file in the chat, its
    local path will be included in the message to you as
    '[Attached file available at: ...]' - pass that exact path as
    attachment_path. Leave attachment_path empty if there is no attachment."""
    service = get_service("gmail", "v1")

    message = MIMEMultipart()
    message["to"] = to
    message["subject"] = subject
    message.attach(MIMEText(body))

    if attachment_path:
        if not os.path.exists(attachment_path):
            return f"Error: attachment file not found at '{attachment_path}'."

        ctype, encoding = mimetypes.guess_type(attachment_path)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)

        with open(attachment_path, "rb") as f:
            part = MIMEBase(maintype, subtype)
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename=os.path.basename(attachment_path))
        message.attach(part)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()

    attach_note = f" with attachment '{os.path.basename(attachment_path)}'" if attachment_path else ""
    return f"Email sent to {to}, subject '{subject}'{attach_note}."
