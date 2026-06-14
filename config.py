import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM (Groq) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = os.getenv("TELEGRAM_ALLOWED_USER_ID")  # restrict bot to only you

# --- Google (Gmail / Calendar / Tasks) ---
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/google_credentials.json")
GOOGLE_TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "credentials/google_token.json")

# --- Attendance portal ---
ATTENDANCE_PORTAL_URL = os.getenv("ATTENDANCE_PORTAL_URL")
ATTENDANCE_USERNAME = os.getenv("ATTENDANCE_USERNAME")
ATTENDANCE_PASSWORD = os.getenv("ATTENDANCE_PASSWORD")

# --- General ---
TIMEZONE = os.getenv("TIMEZONE", "Asia/Karachi")
USER_NAME = os.getenv("USER_NAME", "Boss")

# --- Paths ---
DATA_DIR = "data"
DOWNLOADS_DIR = os.path.join(DATA_DIR, "downloads")
VOICE_DIR = os.path.join(DATA_DIR, "voice")
DB_PATH = os.path.join(DATA_DIR, "jerry_memory.sqlite")
CHATS_PATH = os.path.join(DATA_DIR, "chats.json")

# --- Voice file cleanup ---
# Generated TTS replies in data/voice/ older than this are deleted by a
# background sweep. Recorded input clips are deleted immediately after
# transcription, regardless of this setting.
VOICE_FILE_TTL_SECONDS = int(os.getenv("VOICE_FILE_TTL_MINUTES", "10")) * 60
VOICE_CLEANUP_INTERVAL_SECONDS = int(os.getenv("VOICE_CLEANUP_INTERVAL_MINUTES", "5")) * 60

os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(VOICE_DIR, exist_ok=True)
os.makedirs("credentials", exist_ok=True)
