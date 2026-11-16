"""SQLite storage for submissions, wallets and immutable coin ledger."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import sqlite3

def utc(value=None):
    value=value or datetime.now(timezone.utc)
    if value.tzinfo is None: value=value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

class SubmissionStore:
    def __init__(self,database_path):
        self.database_path=database_path
        if database_path!=":memory:": Path(database_path).parent.mkdir(parents=True,exist_ok=True)
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS submissions(id INTEGER PRIMARY KEY AUTOINCREMENT,source_chat_id INTEGER NOT NULL,source_message_id INTEGER NOT NULL,sender_user_id INTEGER,status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,reviewed_at TEXT,UNIQUE(source_chat_id,source_message_id));
            CREATE TABLE IF NOT EXISTS moderation_claims(submission_id INTEGER PRIMARY KEY REFERENCES submissions(id) ON DELETE CASCADE,claimed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS wallets(user_id INTEGER PRIMARY KEY,balance INTEGER NOT NULL DEFAULT 0 CHECK(balance>=0),updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS coin_transactions(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,actor_user_id INTEGER,amount INTEGER NOT NULL,transaction_type TEXT NOT NULL,description TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS submission_audit(submission_id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,username TEXT,display_name TEXT,submitted_at TEXT NOT NULL,coin_cost INTEGER NOT NULL DEFAULT 0);
            CREATE INDEX IF NOT EXISTS idx_submissions_user_created ON submissions(sender_user_id,created_at);
            CREATE INDEX IF NOT EXISTS idx_submissions_status_created ON submissions(status,created_at);
            CREATE INDEX IF NOT EXISTS idx_coin_user ON coin_transactions(user_id,id DESC);
            """)
    def _connect(self):
        db=sqlite3.connect(self.database_path,timeout=15); db.row_factory=sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON"); return db
    def add(self,chat_id,message_id,sender_user_id):
        with self._connect() as db:
            return int(db.execute("INSERT INTO submissions(source_chat_id,source_message_id,sender_user_id) VALUES(?,?,?)",(chat_id,message_id,sender_user_id)).lastrowid)
    def add_with_limits(self,chat_id,message_id,sender_user_id,*,cooldown_seconds,hourly_limit,now=None):
        sid,error=self.create_submission(chat_id,message_id,sender_user_id,cooldown_seconds=cooldown_seconds,hourly_limit=hourly_limit,coin_cost=0,unlimited=True,now=now)
        return sid
    def create_submission(self,chat_id,message_id,user_id,*,cooldown_seconds,hourly_limit,coin_cost,unlimited=False,username=None,display_name=None,now=None):
        if user_id is None or cooldown_seconds<0 or hourly_limit<1 or coin_cost<0: raise ValueError("Invalid submission settings")
        current=utc(now); stamp=current.strftime("%Y-%m-%d %H:%M:%S")
        hour=(current-timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        cooldown=(current-timedelta(seconds=cooldown_seconds)).strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            count=db.execute("SELECT COUNT(*) FROM submissions WHERE sender_user_id=? AND created_at>=?",(user_id,hour)).fetchone()[0]
            latest=db.execute("SELECT MAX(created_at) FROM submissions WHERE sender_user_id=?",(user_id,)).fetchone()[0]
            if count>=hourly_limit or (cooldown_seconds and latest and latest>=cooldown): return None,"rate_limit"
            db.execute("INSERT OR IGNORE INTO wallets(user_id,balance) VALUES(?,0)",(user_id,))
            balance=db.execute("SELECT balance FROM wallets WHERE user_id=?",(user_id,)).fetchone()[0]
            if not unlimited and balance<coin_cost: return None,"insufficient_coins"
            if not unlimited and coin_cost:
                db.execute("UPDATE wallets SET balance=balance-?,updated_at=? WHERE user_id=?",(coin_cost,stamp,user_id))
            cur=db.execute("INSERT INTO submissions(source_chat_id,source_message_id,sender_user_id,created_at) VALUES(?,?,?,?)",(chat_id,message_id,user_id,stamp)); sid=int(cur.lastrowid)
            db.execute("INSERT INTO submission_audit VALUES(?,?,?,?,?,?)",(sid,user_id,username,display_name,stamp,0 if unlimited else coin_cost))
            if not unlimited and coin_cost:
                db.execute("INSERT INTO coin_transactions(user_id,actor_user_id,amount,transaction_type,description,created_at) VALUES(?,?,?,?,?,?)",(user_id,user_id,-coin_cost,"submission",f"Biaya menfess #{sid}",stamp))
            return sid,None
    def balance(self,user_id):
        with self._connect() as db:
            row=db.execute("SELECT balance FROM wallets WHERE user_id=?",(user_id,)).fetchone()
            return int(row["balance"]) if row else 0
    def change_coins(self,user_id,amount,actor_id,description,kind="adjustment"):
        if amount==0: raise ValueError("amount cannot be zero")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE"); db.execute("INSERT OR IGNORE INTO wallets(user_id,balance) VALUES(?,0)",(user_id,))
            bal=db.execute("SELECT balance FROM wallets WHERE user_id=?",(user_id,)).fetchone()[0]
            if bal+amount<0: return False
            db.execute("UPDATE wallets SET balance=balance+?,updated_at=CURRENT_TIMESTAMP WHERE user_id=?",(amount,user_id))
            db.execute("INSERT INTO coin_transactions(user_id,actor_user_id,amount,transaction_type,description) VALUES(?,?,?,?,?)",(user_id,actor_id,amount,kind,description))
            return True
    def transfer_coins(self,sender,recipient,amount):
        if sender==recipient or amount<1: raise ValueError("Invalid transfer")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            for uid in (sender,recipient): db.execute("INSERT OR IGNORE INTO wallets(user_id,balance) VALUES(?,0)",(uid,))
            bal=db.execute("SELECT balance FROM wallets WHERE user_id=?",(sender,)).fetchone()[0]
            if bal<amount: return False
            db.execute("UPDATE wallets SET balance=balance-? WHERE user_id=?",(amount,sender))
            db.execute("UPDATE wallets SET balance=balance+? WHERE user_id=?",(amount,recipient))
            db.executemany("INSERT INTO coin_transactions(user_id,actor_user_id,amount,transaction_type,description) VALUES(?,?,?,?,?)",[(sender,sender,-amount,"transfer_out",f"Transfer ke {recipient}"),(recipient,sender,amount,"transfer_in",f"Transfer dari {sender}")])
            return True
    def transactions(self,user_id,limit=10):
        with self._connect() as db: return [dict(r) for r in db.execute("SELECT * FROM coin_transactions WHERE user_id=? ORDER BY id DESC LIMIT ?",(user_id,limit))]
    def get(self,sid):
        with self._connect() as db:
            row=db.execute("SELECT * FROM submissions WHERE id=?",(sid,)).fetchone(); return dict(row) if row else None
    def claim(self,sid):
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE"); db.execute("DELETE FROM moderation_claims WHERE claimed_at<datetime('now','-10 minutes')")
            if not db.execute("SELECT 1 FROM submissions WHERE id=? AND status='pending'",(sid,)).fetchone(): return False
            try: db.execute("INSERT INTO moderation_claims(submission_id) VALUES(?)",(sid,)); return True
            except sqlite3.IntegrityError: return False
    def release_claim(self,sid):
        with self._connect() as db: db.execute("DELETE FROM moderation_claims WHERE submission_id=?",(sid,))
    def set_status(self,sid,status):
        if status not in {"approved","rejected"}: raise ValueError("Invalid status")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cur=db.execute("UPDATE submissions SET status=?,reviewed_at=CURRENT_TIMESTAMP WHERE id=? AND status='pending'",(status,sid))
            if not cur.rowcount: return False
            if status=="rejected":
                audit=db.execute("SELECT user_id,coin_cost FROM submission_audit WHERE submission_id=?",(sid,)).fetchone()
                if audit and audit["coin_cost"]>0:
                    db.execute("INSERT OR IGNORE INTO wallets(user_id,balance) VALUES(?,0)",(audit["user_id"],))
                    db.execute("UPDATE wallets SET balance=balance+?,updated_at=CURRENT_TIMESTAMP WHERE user_id=?",(audit["coin_cost"],audit["user_id"]))
                    db.execute("INSERT INTO coin_transactions(user_id,actor_user_id,amount,transaction_type,description) VALUES(?,?,?,?,?)",(audit["user_id"],None,audit["coin_cost"],"refund",f"Pengembalian biaya menfess ditolak #{sid}"))
            db.execute("DELETE FROM moderation_claims WHERE submission_id=?",(sid,))
            return True
    def prune_reviewed(self,retention_days,*,now=None):
        if retention_days<1: raise ValueError("retention_days must be >= 1")
        cutoff=(utc(now)-timedelta(days=retention_days)).strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as db:
            return db.execute("DELETE FROM submissions WHERE status IN ('approved','rejected') AND COALESCE(reviewed_at,created_at)<?",(cutoff,)).rowcount
