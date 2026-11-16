"""Environment-based configuration."""
from dataclasses import dataclass
import os
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    channel_id: int
    admin_ids: frozenset[int]
    database_path: str
    log_level: str
    submission_cooldown_seconds: int
    submission_hourly_limit: int
    retention_days: int


def _positive_int(name: str, default: int, *, allow_zero: bool = False) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < (0 if allow_zero else 1):
        qualifier = "zero or greater" if allow_zero else "greater than zero"
        raise ValueError(f"{name} must be {qualifier}")
    return value


def load_settings() -> Settings:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    channel = os.getenv("CHANNEL_ID", "").strip()
    admins = os.getenv("ADMIN_IDS", "").strip()
    if not token or not channel or not admins:
        raise ValueError("BOT_TOKEN, CHANNEL_ID, and ADMIN_IDS are required")
    try:
        channel_id = int(channel)
        admin_ids = frozenset(int(value.strip()) for value in admins.split(",") if value.strip())
    except ValueError as exc:
        raise ValueError("CHANNEL_ID and ADMIN_IDS must be numeric") from exc
    if not admin_ids:
        raise ValueError("At least one numeric ADMIN_IDS value is required")
    return Settings(
        token, channel_id, admin_ids,
        os.getenv("DATABASE_PATH", "data/menfessbot.db"),
        os.getenv("LOG_LEVEL", "INFO").upper(),
        _positive_int("SUBMISSION_COOLDOWN_SECONDS", 60, allow_zero=True),
        _positive_int("SUBMISSION_HOURLY_LIMIT", 5),
        _positive_int("RETENTION_DAYS", 30),
    )
