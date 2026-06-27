# Jerry — Local-First AI Personal Assistant

Jerry is a local-first AI personal assistant that runs entirely on your machine. It manages your Google Workspace — Gmail, Calendar, Tasks, and Drive — through natural conversation, while keeping all memory, preferences, and conversation history stored locally on your device.

Your data never leaves your machine. Conversations are persisted in a local SQLite database, memories are stored in a local ChromaDB instance, and voice processing happens offline. The only external calls are to the LLM provider for reasoning and to Google's APIs to act on your behalf.

<div align="center">
<a href="https://www.youtube.com/watch?v=HHIcETplriE" target="_blank">Demo Video</a>
</div>

## Why Jerry Exists

Managing a Google Workspace account means constantly switching between Gmail, Calendar, Tasks, and Drive. You check email, copy a date, switch to Calendar, create an event, go back to email, draft a reply — all for a single meeting request.

Jerry gives you a single conversational interface for all of it. You say _"find a free slot this week and schedule a meeting with Ahmed"_ and it checks your calendar, finds open windows, lets you pick one, creates the event, and offers to email Ahmed — all in one conversation.

Everything runs locally. Your conversation history, preferences, and the things you ask Jerry to remember are stored on your machine in SQLite and ChromaDB — not on a remote server, not in someone else's cloud. Jerry connects to Google only to act on your Workspace, and to an LLM provider only for reasoning. Nothing else leaves your device.

## What Jerry Can Do

### Google Workspace

| Capability | What you can ask |
|---|---|
| **Email** | Read, search, summarize, and send emails with optional file attachments |
| **Calendar** | View upcoming events, create events and reminders with automatic popup notifications |
| **Tasks** | List, create, and manage tasks with due dates |
| **Google Drive** | Search files, read/summarize Docs and Sheets, list folders, move files between folders |

### Smart Features

| Feature | How it works |
|---|---|
| **Daily Briefing** | One command gives you today's calendar events, unread emails, and pending tasks in a structured summary |
| **Smart Scheduling** | Finds free time slots within your working hours (9 AM–6 PM), presents options, and books the meeting once you pick a time |
| **Task Prioritization** | Analyzes your tasks, calendar, and emails together — flags overdue items, due-today tasks, and important emails, then recommends what to focus on first |
| **Follow-up Tracker** | Tracks sent emails and alerts you when a reply hasn't arrived within a configurable number of days. Automatically resolves when the reply comes in |
| **Persistent Memory** | Locally stored memory that remembers your email tone preferences, contacts, scheduling preferences, completed tasks, and important notes — silently recalled whenever relevant |

### Interface

| Feature | Details |
|---|---|
| **Web Chat UI** | Dark-themed interface with markdown rendering (bold, tables, lists, headings, code blocks) |
| **Voice Input/Output** | Record voice messages → local Whisper transcription → agent processes → Edge TTS spoken reply |
| **Live Tool Watcher** | See what Jerry is doing in real-time ("Checking calendar...", "Looking through emails...") streamed via SSE |
| **File Attachments** | Upload files in chat, then tell Jerry to email them as attachments |
| **Multi-Chat** | Separate conversation threads with persistent history across restarts |
| **Telegram Bot** | Optional — use Jerry from Telegram with text, voice, and file attachments |

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Interfaces                        │
│  ┌──────────┐   ┌──────────────┐   ┌─────────────┐  │
│  │ Web UI   │   │ Telegram Bot │   │ Voice I/O   │  │
│  │ (FastAPI)│   │ (optional)   │   │ (Whisper +  │  │
│  │          │   │              │   │  Edge TTS)  │  │
│  └────┬─────┘   └──────┬──────┘   └──────┬──────┘  │
│       └────────────────┼──────────────────┘         │
│                        ▼                            │
│  ┌─────────────────────────────────────────────┐    │
│  │              Jerry Agent                    │    │
│  │         LangGraph ReAct Agent               │    │
│  │  ┌───────────────────────────────────────┐  │    │
│  │  │          Agentic Loop                 │  │    │
│  │  │  LLM reasons → tools execute →        │  │    │
│  │  │  LLM observes → repeat or respond     │  │    │
│  │  └───────────────────────────────────────┘  │    │
│  └────────────────────┬────────────────────────┘    │
│                       │                             │
│       ┌───────────────┼───────────────┐             │
│       ▼               ▼               ▼             │
│  ┌─────────┐   ┌───────────┐   ┌───────────┐       │
│  │ Google  │   │  Local    │   │  Local    │       │
│  │ APIs    │   │  Memory   │   │  Tools    │       │
│  │ Gmail   │   │ ChromaDB  │   │ Follow-up │       │
│  │ Calendar│   │ + Sentence│   │ Briefing  │       │
│  │ Tasks   │   │ Transform-│   │ Scheduling│       │
│  │ Drive   │   │ ers       │   │ Priorities│       │
│  └─────────┘   └───────────┘   └───────────┘       │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │      Local Persistence (on your machine)    │    │
│  │  SQLite — conversation history/checkpoints  │    │
│  │  ChromaDB — semantic memory vectors         │    │
│  │  JSON — chat metadata, follow-up tracking   │    │
│  └─────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

### How the Agent Works

Jerry uses a **ReAct (Reason + Act) loop** powered by LangGraph:

1. **User sends a message** → the LLM receives it along with conversation history and all available tool schemas
2. **LLM reasons** → decides which tool(s) to call, or responds directly if no tools are needed
3. **Tools execute** → results are returned to the LLM
4. **LLM observes** → decides whether to call more tools or compose the final response
5. **Loop repeats** until the LLM produces a text response

Jerry chains tools automatically. _"What's on my calendar tomorrow and do I have any tasks due?"_ triggers `get_current_datetime` → `get_calendar_events` → `list_tasks` — without you telling it the steps.

### Tool Watcher (Real-time Streaming)

The web UI streams agent execution via **Server-Sent Events (SSE)**:

- The backend captures each tool execution as it happens
- Tool names are mapped to human-readable labels (e.g., _"Checking calendar"_, _"Looking through emails"_)
- The UI shows an animated indicator with the current action, crossfading between steps

### Local Memory System

Jerry's memory is stored entirely on your machine using **ChromaDB** with **sentence-transformers** for semantic search:

- **Stored silently** — when you mention a preference, describe a person, or say "remember this", Jerry stores it without announcing it
- **Retrieved before acting** — before writing an email, Jerry recalls your tone preferences; before scheduling, it checks your scheduling habits; when someone is mentioned, it looks up stored contact info
- **Tagged by category** — memories are tagged as `email_preference`, `contact`, `scheduling_preference`, `task`, or `important` for precise retrieval
- **Fully local** — stored in `jerry_memory/chroma_db/` on your filesystem, never uploaded anywhere

### Project Structure

```
jerry/
├── main.py                      # Entry point — starts the FastAPI server
├── config.py                    # Environment variables and paths
├── memory.py                    # ChromaDB-backed semantic memory
├── requirements.txt
├── .env.example
│
├── agent/
│   └── jerry_agent.py           # LangGraph agent, system prompt, streaming
│
├── tools/
│   ├── __init__.py              # Tool registry (ALL_TOOLS)
│   ├── datetime_tools.py        # get_current_datetime
│   ├── email_tools.py           # list, read, send emails
│   ├── calendar_tools.py        # view and create events
│   ├── tasks_tools.py           # list and create tasks
│   ├── drive_tools.py           # search, read, move files, list folders
│   ├── followup_tools.py        # track, check, remove follow-ups
│   ├── briefing_tools.py        # daily briefing generator
│   ├── scheduling_tools.py      # find free calendar slots
│   ├── prioritization_tools.py  # task/email priority analysis
│   ├── memory_tools.py          # store/fetch memory wrappers
│   ├── google_auth.py           # Google OAuth2 flow
│   └── _coerce.py               # Type coercion helper
│
├── web/
│   ├── server.py                # FastAPI app, REST + SSE endpoints
│   ├── chats_store.py           # Multi-chat metadata (JSON-backed)
│   └── static/
│       └── index.html           # Chat UI (Tailwind + vanilla JS)
│
├── voice/
│   ├── stt.py                   # Speech-to-text (faster-whisper, local)
│   └── tts.py                   # Text-to-speech (edge-tts)
│
├── bot/
│   └── telegram_bot.py          # Optional Telegram interface
│
├── credentials/                 # Google OAuth files (gitignored)
├── jerry_memory/                # ChromaDB vector store (local)
└── data/                        # SQLite DB, chat metadata, voice files
```

## Setup

### Prerequisites

- Python 3.11+
- An API key from any LLM provider supported by LangChain (default config uses [Groq](https://console.groq.com), free tier works)
- A Google Cloud project with OAuth credentials

### 1. Clone the repository

```bash
git clone https://github.com/Azizkhan22/jerry.git
cd jerry
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

- **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
- **Windows (cmd):**
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** On first run, the `sentence-transformers` library will automatically download the `all-MiniLM-L6-v2` embedding model (~80 MB). This is a one-time download and is used for Jerry's local semantic memory. The model is cached locally in your HuggingFace cache directory.

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | API key from your LLM provider (default: [Groq](https://console.groq.com)) |
| `GROQ_MODEL` | No | Model ID to use. Default: `openai/gpt-oss-120b` |
| `TIMEZONE` | No | Your timezone. Default: `Asia/Karachi` |
| `USER_NAME` | No | How Jerry addresses you. Default: `Boss` |
| `TELEGRAM_BOT_TOKEN` | No | Only if using the Telegram bot |
| `TELEGRAM_ALLOWED_USER_ID` | No | Restricts Telegram bot to your account |

### 5. Set up Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com) → create a project (free, no billing needed)
2. Enable these APIs:
   - Gmail API
   - Google Calendar API
   - Google Tasks API
   - Google Drive API
3. **OAuth consent screen** → External → add your Google account as a test user
4. **Credentials** → Create Credentials → **OAuth client ID** → Desktop app → download the JSON
5. Save it as `credentials/google_credentials.json`

On first run, a browser window opens for you to log in and grant access. This creates `credentials/google_token.json` which auto-refreshes afterward.

> If you previously set up OAuth without the Drive scope, delete `credentials/google_token.json` and re-authenticate to include Drive access.

### 6. Run

```bash
python main.py
```

Open **http://localhost:8000** in your browser.

### Accessing from your phone

- **Same WiFi:** open `http://<your-pc-lan-ip>:8000` on your phone. Text and voice playback work; voice recording may be blocked because the page isn't HTTPS.
- **From anywhere:** run `ngrok http 8000` ([ngrok.com](https://ngrok.com), free) for a temporary HTTPS URL with full functionality including the microphone.

## Optional: Telegram Bot

```bash
pip install python-telegram-bot
python -m bot.telegram_bot
```

Requires `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USER_ID` in `.env`, and ffmpeg installed for voice notes.

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Framework | [LangGraph](https://github.com/langchain-ai/langgraph) (ReAct loop) |
| LLM | Any LangChain-compatible provider (default: Groq) |
| Google APIs | Gmail, Calendar, Tasks, Drive (via `google-api-python-client`) |
| Local Memory | [ChromaDB](https://www.trychroma.com/) + [sentence-transformers](https://www.sbert.net/) |
| Web Server | [FastAPI](https://fastapi.tiangolo.com/) + SSE streaming |
| Frontend | Tailwind CSS + vanilla JS + [marked.js](https://marked.js.org/) |
| Speech-to-Text | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (runs locally, offline) |
| Text-to-Speech | [edge-tts](https://github.com/rany2/edge-tts) |
| Persistence | SQLite (conversations) + ChromaDB (memory) + JSON (metadata) — all local |

## Adding New Tools

1. Create `tools/your_feature.py` with functions decorated with `@tool` (from `langchain_core.tools`). Write a clear docstring — this is how Jerry decides when to use it.
2. Import and add it to `ALL_TOOLS` in `tools/__init__.py`.
3. Add a friendly name mapping in `TOOL_FRIENDLY_NAMES` in `agent/jerry_agent.py` for the tool watcher.

No other code changes needed — Jerry picks up new tools automatically.

## Contributing

Contributions are welcome. Here's how to get started:

1. **Fork** the repository and clone your fork
2. Create a branch for your change: `git checkout -b feature/your-feature`
3. Follow the setup steps above to get Jerry running locally
4. Make your changes — keep PRs focused on a single feature or fix
5. Test that the agent still loads: `python -c "from agent.jerry_agent import agent; print('OK')"`
6. Push and open a pull request with a clear description of what changed and why

### Ideas for contributions

- **New tools** — integrations with other services (Notion, Slack, GitHub, etc.). See [Adding New Tools](#adding-new-tools) for the 3-step process.
- **UI improvements** — better mobile experience, accessibility, new themes
- **Voice** — support for additional TTS/STT engines or languages
- **Memory** — smarter retrieval strategies, memory management UI, export/import
- **LLM providers** — adapters for other providers beyond Groq (OpenAI, Ollama, etc.)
- **Bug fixes** — if something breaks, open an issue or send a fix

### Guidelines

- Don't break existing functionality — Jerry should still handle all current capabilities after your change
- Keep tool docstrings clear and descriptive — the LLM uses them to decide when to call each tool
- No credentials, API keys, or personal data in commits

## License

This project is for personal and educational use.
