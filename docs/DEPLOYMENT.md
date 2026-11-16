# Deployment and Telegram configuration

Submissions are accepted only in the bot private chat. The sender must belong to both required Telegram chats. Approved posts are copied to the publication channel, never to the required group.

## Telegram setup
1. Create the required group and channel.
2. Add the bot to both required chats. Ensure the bot can call getChatMember for each sender; administrator status is recommended, especially for channels.
3. Add the bot as administrator in the publication channel with post permission.
4. Create a separate private audit channel. Add only the Owner and bot. It contains sender Telegram IDs, usernames, display names and timestamps. Do not add ordinary moderators or publish this channel.
5. Obtain numeric chat IDs (including a leading minus sign where applicable) and numeric user IDs.

## Environment
Set BOT_TOKEN, CHANNEL_ID, REQUIRED_GROUP_ID, REQUIRED_CHANNEL_ID, AUDIT_CHANNEL_ID, DEV_IDS and ADMIN_IDS in .env. GROUP_JOIN_URL and CHANNEL_JOIN_URL are optional invite links. SUBMISSION_COIN_COST defaults to 1. Never commit .env or database files.

## Roles and coins
- Developer: highest role; submission coins are unlimited.
- Admin: can moderate and grant coins; has a normal wallet.
- Member: can submit, view balance and transaction history, and transfer coins.
- Submission cost is deducted atomically when a submission is queued. Rejected submissions receive a one-time refund.
- Transfers cannot overdraw a wallet. Grants, charges, refunds and transfers are ledgered.
- No payment gateway is included; coins are granted by Admin/Developer.

## Install
Run python -m venv .venv, activate it, run python -m pip install ., copy .env.example to .env, configure it, then run python -m menfessbot.

## Privacy
The audit channel contains personal data. Restrict it to Owner, disclose the collection in /privacy, and define a suitable retention policy. Reviewed submission rows are pruned at startup; audit and coin ledger records remain for accounting. Securely back up SQLite.
