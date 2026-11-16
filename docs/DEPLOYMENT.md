# Deployment guide (Linux VPS)

This guide deploys MenfessBot as a dedicated, unprivileged systemd service. The bot uses long polling, so no public inbound port is required.

## 1. Create a dedicated account and install the project

Run as a sudo-capable administrator:

```bash
sudo useradd --system --create-home --home-dir /opt/menfessbot --shell /usr/sbin/nologin menfessbot
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
sudo -u menfessbot git clone https://github.com/katsucodeid/menfessbot.git /opt/menfessbot/app
sudo -u menfessbot python3 -m venv /opt/menfessbot/venv
sudo -u menfessbot /opt/menfessbot/venv/bin/pip install /opt/menfessbot/app
sudo install -d -o menfessbot -g menfessbot -m 0750 /var/lib/menfessbot
```

If the repository is private, configure a deploy key or another least-privilege read-only clone method. Do not put a personal access token in the clone URL or shell history.

## 2. Configure secrets

Create the environment file outside the repository:

```bash
sudo install -o root -g menfessbot -m 0640 /dev/null /etc/menfessbot.env
sudoedit /etc/menfessbot.env
```

Add the following values (replace placeholders locally):

```dotenv
BOT_TOKEN=your_botfather_token
CHANNEL_ID=-1001234567890
REQUIRED_GROUP_ID=-1001234567891
REQUIRED_CHANNEL_ID=-1001234567892
AUDIT_CHANNEL_ID=-1001234567893
DEV_IDS=123456789
ADMIN_IDS=987654321
DATABASE_PATH=/var/lib/menfessbot/menfessbot.db
LOG_LEVEL=INFO
SUBMISSION_COOLDOWN_SECONDS=60
SUBMISSION_HOURLY_LIMIT=5
RETENTION_DAYS=0
SUBMISSION_COIN_COST=1
ALLOWED_HASHTAGS=#katsuboy,#katsugirl,#katsuask
GROUP_JOIN_URL=
CHANNEL_JOIN_URL=
```

Use numeric Telegram IDs, not usernames. DEV_IDS must contain at least one Developer ID. Add bot permissions for membership lookup and publication. Restrict access to the environment file and never commit it.

## 3. Roles, submissions and coins

- Developer is the highest role and has unlimited submission coins.
- Admin can moderate and grant coins; Member can submit, check balance/history and transfer coins.
- Submissions are accepted only in private chat after membership checks in both required chats.
- Each text or media caption must contain exactly one configured hashtag. Default: #katsuboy, #katsugirl, #katsuask.
- Submission cost is charged when queued; rejected submissions receive a one-time refund. Transfers cannot overdraw wallets. All coin changes are ledgered.
- No payment gateway is included; Admin/Developer grant coins manually.

## 4. Check Telegram permissions

- Add the bot to the destination channel as an administrator.
- Grant only the permission needed to post messages.
- Add moderator accounts to `ADMIN_IDS`; verify each numeric ID independently.
- Test in a private test channel before using a public channel.

## 5. Install the systemd service

Create `/etc/systemd/system/menfessbot.service`:

```ini
[Unit]
Description=MenfessBot Telegram service
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=menfessbot
Group=menfessbot
WorkingDirectory=/opt/menfessbot/app
EnvironmentFile=/etc/menfessbot.env
ExecStart=/opt/menfessbot/venv/bin/python -m menfessbot
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/menfessbot

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now menfessbot
sudo systemctl status menfessbot
sudo journalctl -u menfessbot -f
```

## 6. Backups, restore and upgrades

Stop the service before taking a consistent SQLite file copy:

```bash
sudo systemctl stop menfessbot
sudo cp /var/lib/menfessbot/menfessbot.db /var/lib/menfessbot/menfessbot.db.backup
sudo chown menfessbot:menfessbot /var/lib/menfessbot/menfessbot.db.backup
sudo systemctl start menfessbot
```

Keep backups encrypted and access-restricted. Test restoring a backup periodically.

To restore, stop the service, preserve the failed database for investigation, replace it with a validated backup, restore ownership/permissions, and start the service again:

```bash
sudo systemctl stop menfessbot
sudo cp /var/lib/menfessbot/menfessbot.db /var/lib/menfessbot/menfessbot.db.failed
sudo cp /var/lib/menfessbot/menfessbot.db.backup /var/lib/menfessbot/menfessbot.db
sudo chown menfessbot:menfessbot /var/lib/menfessbot/menfessbot.db
sudo chmod 0600 /var/lib/menfessbot/menfessbot.db
sudo systemctl start menfessbot
sudo journalctl -u menfessbot -n 100 --no-pager
```

Test restores periodically and keep backups encrypted and access-restricted.

For an upgrade, fetch reviewed code first, then:

```bash
sudo systemctl stop menfessbot
sudo -u menfessbot git -C /opt/menfessbot/app pull --ff-only
sudo -u menfessbot /opt/menfessbot/venv/bin/pip install /opt/menfessbot/app
sudo systemctl start menfessbot
sudo journalctl -u menfessbot -n 100 --no-pager
```

Do not deploy directly from an unreviewed feature branch.

## 7. Operational and privacy notes

- `/privacy` tells users which identifiers are stored and that moderators can view pending submissions.
- `RETENTION_DAYS=0` (default) disables automatic cleanup. Positive values delete reviewed submission rows after N days; cleanup runs at startup and every six hours. Pending rows are never deleted. Coin ledger and audit records remain for accounting.
- Rate limiting defaults to one submission per 60 seconds and five submissions per rolling hour per Telegram user ID.
- Restrict SSH, keep the OS and Python dependencies updated, and monitor service logs.
- Do not log bot tokens or message contents. Define a user-contact and data-request process appropriate to your jurisdiction.
- The bot is an MVP; test permissions, backups, restore, and failure recovery in a private channel before production. The audit channel contains personal data and must remain Owner-only.
