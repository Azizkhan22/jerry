# Jerry - Personal Assistant Agent

LangGraph agent (Groq llama-3.3-70b) + tools for Gmail, Google Calendar/Tasks,
attendance-portal automation, and a local web chat UI (text + voice, female
TTS voice, file attachments).

## 1. Install

```bash
pip install -r requirements.txt
playwright install chromium
```

(No ffmpeg needed for the web UI - only required for the optional Telegram bot.)

## 2. Configure

```bash
cp .env.example .env
```

Fill in `.env`:

- **GROQ_API_KEY** - from https://console.groq.com
- **ATTENDANCE_PORTAL_URL / USERNAME / PASSWORD** - your internship portal login
- **TIMEZONE** - e.g. `Asia/Karachi`
- (TELEGRAM_* vars only needed if you also use the Telegram bot)

## 3. Google OAuth (Gmail + Calendar + Tasks)

1. Go to https://console.cloud.google.com -> create a project (free, no
   billing needed).
2. Enable **Gmail API**, **Google Calendar API**, **Google Tasks API**.
3. "OAuth consent screen" -> "External" -> add your own Google account as a
   test user (Testing mode is fine for personal use; click "Publish App" if
   refresh tokens start expiring after 7 days).
4. "Credentials" -> "Create Credentials" -> "OAuth client ID" -> **Desktop app**
   -> download the JSON.
5. Save it as `credentials/google_credentials.json`.

On first use, a browser window opens for you to log in and grant access -
this creates `credentials/google_token.json` automatically and refreshes
itself afterward.

## 4. Attendance portal selectors

Open `tools/attendance_tools.py`. Update the selectors at the top
(`LOGIN_USERNAME_SELECTOR`, `LOGIN_PASSWORD_SELECTOR`, `LOGIN_SUBMIT_SELECTOR`,
`CHECK_IN_SELECTOR`, `CHECK_OUT_SELECTOR`) to match your portal - right-click
the field/button in your browser -> Inspect -> copy a selector.

Set `DEBUG_HEADFUL = True` and ask Jerry to mark attendance once to watch it
run in a visible browser. On failure, check `data/attendance_error.png`.

## 5. Run

```bash
python main.py
```

Open **http://localhost:8000** in your browser.

- **Text**: type and press Enter ("what's on my calendar today", "summarize
  my unread emails", "send an email to X about Y").
- **Voice**: tap the mic, speak, tap again to stop - it auto-sends. Jerry
  replies with text and a spoken voice reply (plays automatically).
- **Files**: click the paperclip to attach a file, then tell Jerry what to do
  with it ("email this to manager@company.com as a leave request for
  tomorrow"). The attachment chip clears once used.
- **History**: persists across restarts (stored in `data/jerry_memory.sqlite`).

### Using it from your phone

`localhost` only works on the same machine. For phone access:

- **Same WiFi**: open `http://<your-pc-lan-ip>:8000` on your phone. Text,
  files, and voice *playback* work; voice *recording* (microphone) may be
  blocked by the phone browser because the page isn't served over HTTPS.
- **From anywhere + fixes the mic issue**: run `ngrok http 8000` (free at
  ngrok.com, no router/port-forwarding setup). It gives you a temporary
  `https://...ngrok-free.app` URL - open that on your phone for full
  functionality, including the mic, from anywhere.

The PC running `python main.py` must stay on and awake for Jerry to respond.

## Optional: Telegram bot

If you're ever able to use Telegram (e.g. via VPN), the bot still works:

```bash
pip install python-telegram-bot
python -m bot.telegram_bot
```

Requires `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USER_ID` in `.env`, and
ffmpeg installed (for voice notes).

## Adding new tasks/tools later

1. Create `tools/your_feature.py` with one or more functions decorated
   `@tool` (from `langchain_core.tools`) and a clear docstring describing
   when to use it.
2. Import and add it to `ALL_TOOLS` in `tools/__init__.py`.

No other code changes needed - Jerry picks it up automatically, in both the
web UI and the Telegram bot.
