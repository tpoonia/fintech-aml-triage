"""
store.py
--------
SQLite persistence for the scoring service.

Why a database at all? Because the model's most important features are
*behavioral* — "how many transactions has this sender made in the last 24
hours," "how many different accounts have paid into this receiver." You
cannot compute those from a single incoming transaction in isolation; you
need that account's recent history. So the service stores every transaction
it sees and derives the rolling features from that history at scoring time.

That's also the honest version of how a real AML system works: the feature
store is part of the system, not a CSV you prepared earlier.

Three tables:
  transactions — every transaction the service has seen (the feature store)
  alerts       — scored transactions, with risk score + SHAP explanation
  feedback     — analyst verdicts ("this was a false positive"), which is
                 the raw material for retraining the model later
"""

import json
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "aml.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id        TEXT PRIMARY KEY,
    timestamp             TEXT NOT NULL,
    sender_account        TEXT NOT NULL,
    receiver_account      TEXT NOT NULL,
    amount                REAL NOT NULL,
    payment_type          TEXT,
    sender_bank_location  TEXT,
    receiver_bank_location TEXT
);
CREATE INDEX IF NOT EXISTS idx_txn_sender ON transactions(sender_account, timestamp);
CREATE INDEX IF NOT EXISTS idx_txn_receiver ON transactions(receiver_account, timestamp);

CREATE TABLE IF NOT EXISTS alerts (
    transaction_id  TEXT PRIMARY KEY,
    scored_at       TEXT NOT NULL,
    risk_score      REAL NOT NULL,
    explanation     TEXT NOT NULL,   -- JSON: top SHAP contributions
    features        TEXT NOT NULL,   -- JSON: the feature vector used
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
);
CREATE INDEX IF NOT EXISTS idx_alert_score ON alerts(risk_score DESC);

CREATE TABLE IF NOT EXISTS feedback (
    transaction_id  TEXT PRIMARY KEY,
    verdict         TEXT NOT NULL,   -- 'false_positive' | 'confirmed_suspicious'
    analyst_note    TEXT,
    submitted_at    TEXT NOT NULL,
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
);
"""


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def insert_transaction(conn, txn: dict):
    conn.execute(
        """INSERT OR REPLACE INTO transactions
           (transaction_id, timestamp, sender_account, receiver_account, amount,
            payment_type, sender_bank_location, receiver_bank_location)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (txn["transaction_id"], txn["timestamp"], txn["sender_account"],
         txn["receiver_account"], txn["amount"], txn.get("payment_type"),
         txn.get("sender_bank_location"), txn.get("receiver_bank_location")),
    )


def insert_alert(conn, transaction_id, scored_at, risk_score, explanation, features):
    conn.execute(
        """INSERT OR REPLACE INTO alerts
           (transaction_id, scored_at, risk_score, explanation, features)
           VALUES (?, ?, ?, ?, ?)""",
        (transaction_id, scored_at, risk_score,
         json.dumps(explanation), json.dumps(features)),
    )


def insert_feedback(conn, transaction_id, verdict, note, submitted_at):
    conn.execute(
        """INSERT OR REPLACE INTO feedback
           (transaction_id, verdict, analyst_note, submitted_at)
           VALUES (?, ?, ?, ?)""",
        (transaction_id, verdict, note, submitted_at),
    )


def fetch_alerts(conn, limit=100, min_score=0.0):
    """The analyst triage queue: highest-risk alerts first."""
    rows = conn.execute(
        """SELECT a.transaction_id, a.scored_at, a.risk_score, a.explanation,
                  t.timestamp, t.sender_account, t.receiver_account, t.amount,
                  t.payment_type, t.sender_bank_location, t.receiver_bank_location,
                  f.verdict
           FROM alerts a
           JOIN transactions t ON t.transaction_id = a.transaction_id
           LEFT JOIN feedback f ON f.transaction_id = a.transaction_id
           WHERE a.risk_score >= ?
           ORDER BY a.risk_score DESC
           LIMIT ?""",
        (min_score, limit),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["explanation"] = json.loads(d["explanation"])
        out.append(d)
    return out


def sender_history(conn, sender_account, before_timestamp):
    """All prior transactions by this sender, oldest first."""
    rows = conn.execute(
        """SELECT timestamp, amount, receiver_account FROM transactions
           WHERE sender_account = ? AND timestamp <= ?
           ORDER BY timestamp""",
        (sender_account, before_timestamp),
    ).fetchall()
    return [dict(r) for r in rows]


def receiver_history(conn, receiver_account, before_timestamp):
    rows = conn.execute(
        """SELECT timestamp, sender_account FROM transactions
           WHERE receiver_account = ? AND timestamp <= ?
           ORDER BY timestamp""",
        (receiver_account, before_timestamp),
    ).fetchall()
    return [dict(r) for r in rows]
