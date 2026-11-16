# MenfessBot

Telegram menfess bot with a private moderation queue and channel publishing.

## Features
- Receive text and Telegram media.
- Store pending submissions in SQLite.
- Admin-only moderation callbacks and channel publishing.
- Per-user submission cooldown and hourly rate limit.
- `/privacy` command describing stored data and moderator access.
- Automatic retention cleanup for reviewed submissions; pending submissions are never auto-deleted.
- Automated database and handler tests.

## Requirements
- Python 3.11+
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- Bot is administrator in the destination channel with permission to post
- Numeric Telegram user IDs for moderators

## Local setup
1. Create a virtual environment: `python -m venv .venv`
2. Activate it and install the package: `python -m pip install .`
3. Copy `.env.example` to `.env` and fill in the values.
4. Run: `python -m menfessbot`

## Configuration
| Variable | Required | Default | Description |
|---|---|---|---|
| BOT_TOKEN | Yes | — | Telegram bot token; keep secret |
| CHANNEL_ID | Yes | — | Destination channel ID |
| ADMIN_IDS | Yes | — | Comma-separated numeric moderator IDs |
| DATABASE_PATH | No | data/menfessbot.db | SQLite database path |
| LOG_LEVEL | No | INFO | Python logging level |
| SUBMISSION_COOLDOWN_SECONDS | No | 60 | Minimum seconds between a user's submissions; 0 disables cooldown |
| SUBMISSION_HOURLY_LIMIT | No | 5 | Maximum submissions per user in a rolling hour |
| RETENTION_DAYS | No | 30 | Age after which reviewed rows are removed; must be at least 1 |

## Tests
Install development dependencies and run:
```bash
python -m pip install -r requirements-dev.txt
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Deployment
See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for a systemd VPS deployment guide, service hardening, backups, and upgrade steps.

## Privacy and operations
The bot stores source chat/message IDs and sender user IDs to support moderation, publishing, and rate limiting. Moderators can view submissions before publication. Reviewed submissions are pruned at startup after the configured retention period; pending submissions are preserved. The privacy command is an operational notice, not a substitute for a privacy policy tailored to your jurisdiction. Restrict database access, back it up securely, and never commit `.env` or real tokens.

## Contributing
Read [CONTRIBUTING.md](CONTRIBUTING.md). Use pull requests and include tests for behavior changes.

## License
MIT. See [LICENSE](LICENSE).
