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
sudo -u menfessbot /opt/menfessbot/venv/bin/pip install -r /opt/menfessbot/app/requirements.txt
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
ADMIN_IDS=123456789,987654321
DATABASE_PATH=/var/lib/menfessbot/menfessbot.db
LOG_LEVEL=INFO
SUBMISSION_COOLDOWN_SECONDS=60
SUBMISSION_HOURLY_LIMIT=5
RETENTION_DAYS=30
```

Use numeric Telegram IDs, not usernames. Restrict access to the environment file and never commit it.

## 3. Check Telegram permissions

- Add the bot to the destination channel as an administrator.
- Grant only the permission needed to post messages.
- Add moderator accounts to `ADMIN_IDS`; verify each numeric ID independently.
- Test in a private test channel before using a public channel.

## 4. Install the systemd service

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

## 5. Backups and upgrades

Stop the service before taking a consistent SQLite file copy:

```bash
sudo systemctl stop menfessbot
sudo cp /var/lib/menfessbot/menfessbot.db /var/lib/menfessbot/menfessbot.db.backup
sudo chown menfessbot:menfessbot /var/lib/menfessbot/menfessbot.db.backup
sudo systemctl start menfessbot
```

Keep backups encrypted and access-restricted. Test restoring a backup periodically.

For an upgrade, fetch reviewed code first, then:

```bash
sudo systemctl stop menfessbot
sudo -u menfessbot git -C /opt/menfessbot/app pull --ff-only
sudo -u menfessbot /opt/menfessbot/venv/bin/pip install -r /opt/menfessbot/app/requirements.txt
sudo systemctl start menfessbot
sudo journalctl -u menfessbot -n 100 --no-pager
```

Do not deploy directly from an unreviewed feature branch.

## 6. Operational and privacy notes

- `/privacy` tells users which identifiers are stored and that moderators can view pending submissions.
- `RETENTION_DAYS` cleanup currently runs at application startup and deletes only reviewed rows. Pending submissions are preserved. Restart the service periodically if you need cleanup to run periodically; a scheduled cleanup job is a future enhancement.
- Rate limiting defaults to one submission per 60 seconds and five submissions per rolling hour per Telegram user ID.
- Restrict SSH, keep the OS and Python dependencies updated, and monitor service logs.
- Do not log bot tokens or message contents. Define a user-contact and data-request process appropriate to your jurisdiction.
- The bot is an MVP; test permissions, backups, and failure recovery in a private channel before production.
