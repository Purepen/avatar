"""Environment configuration for the Avatar backend.

All secrets live in the project-root .env. Paths are resolved relative to this
file so the same layout works locally and inside the Docker image.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL = os.getenv("MODEL", "openai/gpt-5.4-nano")
OWNER_NAME = os.getenv("OWNER_NAME", "The Owner")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
PUSHOVER_USER = os.getenv("PUSHOVER_USER", "")
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SESSION_SECRET = os.getenv("SESSION_SECRET") or f"avatar::{ADMIN_PASSWORD}"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "0") == "1"

KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

# Abuse guards (fixed by SPEC, not configurable)
MAX_MESSAGE_CHARS = 20_000
TRUNCATION_NOTE = (
    "[...message truncated as it's too long; ask the visitor to send something more concise]"
)
RATE_LIMIT = "20/minute"

SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60  # 30 days
SESSION_COOKIE_NAME = "avatar_admin"
