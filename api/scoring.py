"""
scoring.py
----------
Turns an incoming transaction into a risk score plus an explanation.

The critical requirement here is that the features computed at scoring time
must match *exactly* what the model saw during training — same names, same
order, same definitions. A mismatch is the classic "works in the notebook,
silently wrong in production" bug, because the model will happily accept a
misaligned vector and return a confident, meaningless number.

That's why the feature order is loaded from models/feature_columns.json
(written by train.py) rather than hard-coded here, and why the rolling-window
definitions below mirror src/features.py.
"""

import json
import math
import joblib
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

import shap

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"

HIGH_RISK_LOCATIONS = {"KY", "PA", "AE", "NG"}
REPORTING_THRESHOLD = 10_000
PAYMENT_TYPES = ["ACH", "Cash Deposit", "Cash Withdrawal", "Cheque", "Credit card", "Cross-border"]

# Human-readable descriptions, so the dashboard can explain an alert in
# language a compliance analyst (not a data scientist) understands.
FEATURE_LABELS = {
    "amount": "Transaction amount",
    "log_amount": "Transaction amount (log scale)",
    "near_threshold": "Amount just below the $10k reporting threshold",
    "hour_of_day": "Hour of day",
    "is_weekend": "Weekend transaction",
    "is_cross_border": "Cross-border transfer",
    "sender_high_risk_loc": "Sender in high-risk jurisdiction",
    "receiver_high_risk_loc": "Receiver in high-risk jurisdiction",
    "sender_txn_count_24h": "Sender's transaction count (24h)",
    "sender_total_amount_24h": "Sender's total volume (24h)",
    "sender_avg_amount_24h": "Sender's average amount (24h)",
    "sender_unique_receivers_24h": "Distinct receivers paid by sender (24h)",
    "receiver_unique_senders_24h": "Distinct senders paying this receiver (24h)",
    "amount_zscore_vs_sender_history": "How unusual this amount is for this sender",
}
for _pt in PAYMENT_TYPES:
    FEATURE_LABELS[f"ptype_{_pt}"] = f"Payment type: {_pt}"


class Scorer:
    """Loads the trained model once and scores transactions against it."""

    def __init__(self):
        self.model = joblib.load(MODELS_DIR / "xgboost_model.joblib")
        with open(MODELS_DIR / "feature_columns.json") as f:
            self.feature_columns = json.load(f)
        # TreeExplainer is fast enough to explain every single alert in real
        # time, which is what makes per-alert explanations practical here.
        self.explainer = shap.TreeExplainer(self.model)

    def build_features(self, txn, sender_hist, receiver_hist):
        """Recreate the training-time feature vector for one transaction.

        sender_hist / receiver_hist are that account's prior transactions,
        which is what the rolling 24-hour windows are computed from.
        """
        ts = datetime.fromisoformat(txn["timestamp"])
        window_start = ts - timedelta(hours=24)
        amount = float(txn["amount"])

        # --- rolling 24h window over the sender's activity (inclusive of this txn) ---
        recent_sender = [
            h for h in sender_hist
            if window_start <= datetime.fromisoformat(h["timestamp"]) <= ts
        ]
        amounts_24h = [float(h["amount"]) for h in recent_sender]
        sender_txn_count_24h = float(len(recent_sender))
        sender_total_amount_24h = float(sum(amounts_24h))
        sender_avg_amount_24h = float(np.mean(amounts_24h)) if amounts_24h else 0.0
        sender_unique_receivers_24h = float(len({h["receiver_account"] for h in recent_sender}))

        recent_receiver = [
            h for h in receiver_hist
            if window_start <= datetime.fromisoformat(h["timestamp"]) <= ts
        ]
        receiver_unique_senders_24h = float(len({h["sender_account"] for h in recent_receiver}))

        # --- z-score against the sender's PRIOR history only (never this txn) ---
        prior_amounts = [
            float(h["amount"]) for h in sender_hist
            if datetime.fromisoformat(h["timestamp"]) < ts
        ]
        if len(prior_amounts) >= 2:
            mean, std = float(np.mean(prior_amounts)), float(np.std(prior_amounts, ddof=1))
            zscore = (amount - mean) / std if std > 0 else 0.0
        else:
            zscore = 0.0  # cold-start account: no baseline to compare against

        payment_type = txn.get("payment_type") or ""
        sender_loc = txn.get("sender_bank_location") or ""
        receiver_loc = txn.get("receiver_bank_location") or ""

        values = {
            "amount": amount,
            "log_amount": math.log1p(amount),
            "near_threshold": float(REPORTING_THRESHOLD * 0.85 <= amount < REPORTING_THRESHOLD),
            "hour_of_day": float(ts.hour),
            "is_weekend": float(ts.weekday() >= 5),
            "is_cross_border": float(sender_loc != receiver_loc),
            "sender_high_risk_loc": float(sender_loc in HIGH_RISK_LOCATIONS),
            "receiver_high_risk_loc": float(receiver_loc in HIGH_RISK_LOCATIONS),
            "sender_txn_count_24h": sender_txn_count_24h,
            "sender_total_amount_24h": sender_total_amount_24h,
            "sender_avg_amount_24h": sender_avg_amount_24h,
            "sender_unique_receivers_24h": sender_unique_receivers_24h,
            "receiver_unique_senders_24h": receiver_unique_senders_24h,
            "amount_zscore_vs_sender_history": zscore,
        }
        for pt in PAYMENT_TYPES:
            values[f"ptype_{pt}"] = float(payment_type == pt)

        # Order must match training exactly — this is the guard against the
        # silent misalignment bug described in the module docstring.
        missing = [c for c in self.feature_columns if c not in values]
        if missing:
            raise ValueError(f"Feature vector is missing columns the model expects: {missing}")

        return values

    def score(self, features: dict):
        """Return (risk_score, explanation) for one feature dict."""
        x = np.array([[features[c] for c in self.feature_columns]], dtype=float)
        risk_score = float(self.model.predict_proba(x)[0, 1])

        shap_values = self.explainer.shap_values(x)[0]
        contributions = [
            {
                "feature": col,
                "label": FEATURE_LABELS.get(col, col),
                "value": features[col],
                "shap": float(sv),
                "direction": "increases risk" if sv > 0 else "decreases risk",
            }
            for col, sv in zip(self.feature_columns, shap_values)
        ]
        # Biggest absolute contributors first — that's what an analyst needs
        # to see to decide whether the alert is worth investigating.
        contributions.sort(key=lambda c: abs(c["shap"]), reverse=True)

        return risk_score, contributions[:6]
