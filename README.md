# MenfessBot

Telegram menfess bot with private-chat submissions, mandatory group and channel membership, moderation, Owner audit logging, role-based access and coin wallets.

## Features
- Accepts submissions only through the bot private chat.
- Requires exactly one configured category hashtag per submission (default: `#katsuboy`, `#katsugirl`, or `#katsuask`); applies to text and media captions.
- Requires membership in both configured group and channel.
- Approved posts are copied to the configured publication channel; the required group is never used for publishing.
- Private Owner audit channel records sender Telegram ID, username, display name, role and submission time.
- Developer has unlimited submission coins; Admin can moderate and grant coins; Member can submit and use wallet commands.
- Coin balances, transaction ledger, transfers, submission fee and automatic refund when a submission is rejected.
- SQLite persistence, per-user cooldown and rolling hourly limit.
- Reviewed submissions are pruned at startup and every six hours only when `RETENTION_DAYS` is greater than zero; `0` disables automatic cleanup and pending items are always retained.

## Setup
Requires Python 3.11+ and a Telegram bot token from @BotFather. Add the bot to both required chats so it can check membership. Give it post permission in the publication channel, and send-message permission in the private Owner audit channel.

Run: python -m venv .venv; activate the environment; python -m pip install .; copy .env.example to .env and fill the values; then python -m menfessbot.

## Environment variables
- BOT_TOKEN: bot token (secret).
- CHANNEL_ID: publication channel ID.
- REQUIRED_GROUP_ID and REQUIRED_CHANNEL_ID: mandatory membership destinations.
- GROUP_JOIN_URL and CHANNEL_JOIN_URL: optional join links.
- AUDIT_CHANNEL_ID: private Owner-only audit channel.
- DEV_IDS: Developer/Owner Telegram user IDs.
- ADMIN_IDS: Admin Telegram user IDs.
- SUBMISSION_COIN_COST: coin fee per submission (default 1).
- ALLOWED_HASHTAGS: comma-separated allowed category hashtags; defaults to `#katsuboy,#katsugirl,#katsuask`. Each submission must include exactly one.
- SUBMISSION_COOLDOWN_SECONDS: cooldown (default 60).
- SUBMISSION_HOURLY_LIMIT: max submissions per rolling hour (default 5).
- RETENTION_DAYS: retention for reviewed submission rows; set to `0` to disable automatic cleanup (default).

Telegram chat IDs may be negative. Never commit .env, bot tokens, or database files. The audit channel contains personal data and must remain private.

## Commands
/start, /help, /privacy, /balance, /transactions, /transfer USER_ID AMOUNT, /grant USER_ID AMOUNT [reason] (Admin/Developer only).

## Tests
Install development requirements and run: PYTHONPATH=src python -m unittest discover -s tests -v.
See docs/DEPLOYMENT.md for Telegram permissions and privacy setup.

## License
MIT.
