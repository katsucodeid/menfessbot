"""Environment-based configuration."""
from dataclasses import dataclass
import os
from dotenv import load_dotenv

@dataclass(frozen=True)
class Settings:
    bot_token:str; channel_id:int; admin_ids:frozenset[int]; developer_ids:frozenset[int]
    required_group_id:int; required_channel_id:int; audit_channel_id:int
    database_path:str; log_level:str; submission_cooldown_seconds:int
    submission_hourly_limit:int; retention_days:int; submission_coin_cost:int
    group_join_url:str; channel_join_url:str

def number(name, default=0, minimum=0):
    try: value=int(os.getenv(name,str(default)).strip())
    except ValueError as exc: raise ValueError(f"{name} must be an integer") from exc
    if value<minimum: raise ValueError(f"{name} must be at least {minimum}")
    return value

def ids(name, required=False):
    raw=os.getenv(name,"").strip()
    if required and not raw: raise ValueError(f"{name} is required")
    try: return frozenset(int(x.strip()) for x in raw.split(",") if x.strip())
    except ValueError as exc: raise ValueError(f"{name} must contain numeric IDs") from exc

def load_settings():
    load_dotenv()
    token=os.getenv("BOT_TOKEN","").strip()
    if not token: raise ValueError("BOT_TOKEN is required")
    developers=ids("DEV_IDS",True)
    if not developers: raise ValueError("DEV_IDS must include the owner/developer ID")
    return Settings(token,number("CHANNEL_ID",minimum=1),ids("ADMIN_IDS",True),developers,
        number("REQUIRED_GROUP_ID",minimum=1),number("REQUIRED_CHANNEL_ID",minimum=1),
        number("AUDIT_CHANNEL_ID",minimum=1),os.getenv("DATABASE_PATH","data/menfessbot.db"),
        os.getenv("LOG_LEVEL","INFO").upper(),number("SUBMISSION_COOLDOWN_SECONDS",60),
        number("SUBMISSION_HOURLY_LIMIT",5,1),number("RETENTION_DAYS",30,1),
        number("SUBMISSION_COIN_COST",1),os.getenv("GROUP_JOIN_URL","").strip(),
        os.getenv("CHANNEL_JOIN_URL","").strip())
