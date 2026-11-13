import sqlite3
import os

def get_db_path() -> str:
    return os.getenv("FRAUDSHIELD_DB_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "fraudshield.db")))

def get_db_connection(db_path: str = None):
    target_path = db_path or get_db_path()
    is_uri = target_path.startswith("file:") or "mode=memory" in target_path
    if is_uri or target_path == ":memory:":
        conn = sqlite3.connect(target_path, check_same_thread=False, uri=is_uri)
    else:
        conn = sqlite3.connect(target_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: str = None):
    conn = get_db_connection(db_path)
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                card_last4 TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                merchant_name TEXT NOT NULL,
                merchant_category TEXT NOT NULL,
                ip_address TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                device_id TEXT,
                timestamp_epoch REAL NOT NULL,
                risk_score INTEGER NOT NULL,
                decision TEXT NOT NULL,
                risk_factors TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                transaction_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                alert_reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (transaction_id) REFERENCES transactions (id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
            CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(timestamp_epoch);
            CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
        """)
    return conn
