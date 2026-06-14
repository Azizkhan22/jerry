import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import config

# Scopes cover everything Jerry needs across Gmail, Calendar and Tasks.
# If you add a new tool that needs another Google API, add its scope here
# and delete credentials/google_token.json so it re-runs the consent flow.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
]

_creds = None


def get_credentials() -> Credentials:
    """Load cached credentials, refresh if expired, or run the OAuth
    consent flow (opens a browser) the first time."""
    global _creds
    if _creds and _creds.valid:
        return _creds

    creds = None
    if os.path.exists(config.GOOGLE_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(config.GOOGLE_TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(config.GOOGLE_CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(config.GOOGLE_TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    _creds = creds
    return creds


def get_service(api_name: str, version: str):
    """Build an authenticated Google API client, e.g. get_service('gmail', 'v1')."""
    return build(api_name, version, credentials=get_credentials())
