# MenfessBot

Telegram menfess bot with a private moderation queue and channel publishing.

## MVP features
- Receive text and Telegram media.
- Store pending submissions in SQLite.
- Send submissions to moderators for review.
- Publish approved messages to a configured channel.
- Reject submissions without publishing.
- Admin-only moderation callbacks and automated tests.

## Requirements
- Python 3.11+
- Telegram bot token from @BotFather
- Bot is administrator in the destination channel with permission to post
- Numeric Telegram user IDs for moderators

## Setup
1. Create and activate a Python virtual environment.
2. Install: python -m pip install -r requirements.txt
3. Copy .env.example to .env and configure it.
4. Run: python -m menfessbot

## Environment
| Variable | Required | Description |
|---|---|---|
| BOT_TOKEN | Yes | Telegram bot token |
| CHANNEL_ID | Yes | Destination channel ID |
| ADMIN_IDS | Yes | Comma-separated moderator IDs |
| DATABASE_PATH | No | SQLite path; default data/menfessbot.db |
| LOG_LEVEL | No | Logging level; default INFO |

## Tests
Install requirements-dev.txt, then run:
python -m unittest discover -s tests -v

## Privacy
The bot stores source chat and message IDs for moderation. Protect the database, never commit secrets, and define a retention policy before production use. Users should be warned not to submit personal or sensitive information. Review every submission before publication.

## Roadmap
See ROADMAP.md. Contributions are welcome; read CONTRIBUTING.md first.

## License
MIT. See LICENSE.
