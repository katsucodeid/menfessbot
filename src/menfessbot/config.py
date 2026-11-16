"""Environment-based configuration."""
from dataclasses import dataclass
import os
from dotenv import load_dotenv

@dataclass(frozen=True)
class Settings:
    bot_token:str
    channel_id:int
    admin_ids:frozenset[int]
    developer_ids:frozenset[int]
    required_group_id:int
    required_channel_id:int
    audit_channel_id:int
    database_path:str
    log_level:str
    submission_cooldown_seconds:int
    submission_hourly_limit:int
    retention_days:int
    submission_coin_cost:int
    group_join_url:str
    channel_join_url:str
    allowed_hashtags:tuple[str, ...]

def number(name, default=0, minimum=0):
    try:
        value=int(os.getenv(name,str(default)).strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value<minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value

def chat_id(name):
    raw=os.getenv(name,"").strip()
    try:
        value=int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a numeric Telegram chat ID") from exc
    if value==0:
        raise ValueError(f"{name} must be a non-zero Telegram chat ID")
    return value

def ids(name, required=False):
    raw=os.getenv(name,"").strip()
    if required and not raw:
        raise ValueError(f"{name} is required")
    try:
        return frozenset(int(x.strip()) for x in raw.split(",") if x.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must contain numeric IDs") from exc

def hashtags(name="ALLOWED_HASHTAGS", default="#katsuboy,#katsugirl,#katsuask"):
    raw=os.getenv(name,default)
    values=tuple(dict.fromkeys(x.strip().lower() for x in raw.split(",") if x.strip()))
    if not values:
        raise ValueError(f"{name} must contain at least one hashtag")
    import re
    if any(not re.fullmatch(r"#[a-z0-9_]+", tag) for tag in values):
        raise ValueError(f"{name} must be comma-separated hashtags such as #katsuboy,#katsugirl")
    return values

def load_settings():
    load_dotenv()
    token=os.getenv("BOT_TOKEN","").strip()
    if not token:
        raise ValueError("BOT_TOKEN is required")
    developers=ids("DEV_IDS",True)
    if not developers:
        raise ValueError("DEV_IDS must include at least one Developer/Owner ID")
    return Settings(
        token,chat_id("CHANNEL_ID"),ids("ADMIN_IDS",True),developers,
        chat_id("REQUIRED_GROUP_ID"),chat_id("REQUIRED_CHANNEL_ID"),chat_id("AUDIT_CHANNEL_ID"),
        os.getenv("DATABASE_PATH","data/menfessbot.db"),os.getenv("LOG_LEVEL","INFO").upper(),
        number("SUBMISSION_COOLDOWN_SECONDS",60),number("SUBMISSION_HOURLY_LIMIT",5,1),
        number("RETENTION_DAYS",30,1),number("SUBMISSION_COIN_COST",1),
        os.getenv("GROUP_JOIN_URL","").strip(),os.getenv("CHANNEL_JOIN_URL","").strip(),hashtags()
    )
