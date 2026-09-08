"""
generate_data.py
-----------------
Generates a synthetic bank-transaction dataset that mirrors the structure and
money-laundering typologies of the public SAML-D dataset:
https://www.kaggle.com/datasets/berkanoztas/synthetic-transaction-monitoring-dataset-aml

Why synthetic data first?
  - SAML-D requires a Kaggle account + API token to download.
  - Generating our own lets you start coding *today* and understand exactly
    how the "illicit" patterns were created (useful when you explain the
    project in an interview).
  - Once you have a Kaggle account, download the real SAML-D CSV, put it in
    data/raw/transactions.csv with the same column names used below, and
    every downstream script (features.py, train.py, evaluate.py) works
    unchanged.

Typologies simulated (all real AML patterns):
  - NORMAL:      everyday legitimate transactions.
  - STRUCTURING: many transactions just under a reporting threshold
                 (e.g. $9,000-$9,999 to dodge a $10,000 reporting rule).
  - SMURFING:    one source splits money across many receiving accounts
                 in a short time window.
  - LAYERING:    money moves rapidly through a chain of accounts to
                 obscure its origin.

Run:
    python src/generate_data.py
Output:
    data/raw/transactions.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

RNG = np.random.default_rng(42)

N_ACCOUNTS = 5000
N_NORMAL_TXNS = 200_000
REPORTING_THRESHOLD = 10_000
START_DATE = datetime(2025, 1, 1)
DAYS = 180

PAYMENT_TYPES = ["Credit card", "Cross-border", "Cash Deposit", "ACH", "Cheque", "Cash Withdrawal"]
LOCATIONS = ["US", "UK", "DE", "AE", "SG", "CH", "KY", "PA", "NG", "IN"]
# a few locations flagged as higher-risk jurisdictions, used to bias illicit patterns
HIGH_RISK_LOCATIONS = ["KY", "PA", "AE", "NG"]
CURRENCIES = ["USD", "EUR", "GBP", "AED", "SGD"]


def random_timestamps(n, start=START_DATE, days=DAYS):
    offsets = RNG.integers(0, days * 24 * 60, size=n)  # minutes into the window
    return [start + timedelta(minutes=int(m)) for m in offsets]


def make_accounts(n):
    return [f"ACC{i:06d}" for i in range(n)]


def generate_normal_transactions(accounts, n):
    """Everyday legitimate activity: amounts roughly log-normal, mostly
    domestic, sender/receiver picked independently."""
    senders = RNG.choice(accounts, size=n)
    receivers = RNG.choice(accounts, size=n)
    same = senders == receivers
    # avoid self-transfers
    receivers[same] = RNG.choice(accounts, size=same.sum())

    amounts = np.round(RNG.lognormal(mean=6.0, sigma=1.1, size=n), 2)  # skews low, occasional large txns
    amounts = np.clip(amounts, 5, 50_000)

    sender_loc = RNG.choice(LOCATIONS, size=n, p=_loc_probs(low_risk_heavy=True))
    receiver_loc = RNG.choice(LOCATIONS, size=n, p=_loc_probs(low_risk_heavy=True))
    currency = RNG.choice(CURRENCIES, size=n)
    payment_type = RNG.choice(PAYMENT_TYPES, size=n)
    ts = random_timestamps(n)

    df = pd.DataFrame({
        "timestamp": ts,
        "sender_account": senders,
        "receiver_account": receivers,
        "amount": amounts,
        "payment_currency": currency,
        "received_currency": currency,
        "sender_bank_location": sender_loc,
        "receiver_bank_location": receiver_loc,
        "payment_type": payment_type,
        "is_laundering": 0,
        "laundering_type": "none",
    })
    return df


def _loc_probs(low_risk_heavy=True):
    probs = np.array([0.30, 0.15, 0.12, 0.06, 0.08, 0.05, 0.04, 0.04, 0.08, 0.08])
    if not low_risk_heavy:
        # bias toward high-risk jurisdictions
        boost = np.array([loc in HIGH_RISK_LOCATIONS for loc in LOCATIONS]) * 0.15
        probs = probs + boost
    return probs / probs.sum()


def generate_structuring(accounts, n_rings=120, txns_per_ring=(4, 9)):
    """One account makes several deposits just under the reporting threshold
    within a short window -> classic structuring / "smurfing the threshold"."""
    rows = []
    for _ in range(n_rings):
        acct = RNG.choice(accounts)
        k = RNG.integers(*txns_per_ring)
        base_time = START_DATE + timedelta(minutes=int(RNG.integers(0, DAYS * 24 * 60)))
        for i in range(k):
            amt = RNG.uniform(REPORTING_THRESHOLD * 0.90, REPORTING_THRESHOLD * 0.999)
            ts = base_time + timedelta(hours=int(RNG.integers(0, 72)))
            rows.append({
                "timestamp": ts,
                "sender_account": acct,
                "receiver_account": RNG.choice(accounts),
                "amount": round(amt, 2),
                "payment_currency": "USD",
                "received_currency": "USD",
                "sender_bank_location": RNG.choice(LOCATIONS, p=_loc_probs(False)),
                "receiver_bank_location": RNG.choice(LOCATIONS, p=_loc_probs(False)),
                "payment_type": "Cash Deposit",
                "is_laundering": 1,
                "laundering_type": "structuring",
            })
    return pd.DataFrame(rows)


def generate_smurfing(accounts, n_rings=100, fan_out=(8, 25)):
    """A single source account fans money out to many receiving accounts in a
    tight time window, then (implicitly) those accounts consolidate elsewhere."""
    rows = []
    for _ in range(n_rings):
        source = RNG.choice(accounts)
        k = RNG.integers(*fan_out)
        receivers = RNG.choice(accounts, size=k, replace=False)
        base_time = START_DATE + timedelta(minutes=int(RNG.integers(0, DAYS * 24 * 60)))
        total = RNG.uniform(20_000, 150_000)
        splits = RNG.dirichlet(np.ones(k)) * total
        for r, amt in zip(receivers, splits):
            ts = base_time + timedelta(minutes=int(RNG.integers(0, 180)))
            rows.append({
                "timestamp": ts,
                "sender_account": source,
                "receiver_account": r,
                "amount": round(max(amt, 50), 2),
                "payment_currency": "USD",
                "received_currency": "USD",
                "sender_bank_location": RNG.choice(LOCATIONS, p=_loc_probs(False)),
                "receiver_bank_location": RNG.choice(LOCATIONS, p=_loc_probs(False)),
                "payment_type": "ACH",
                "is_laundering": 1,
                "laundering_type": "smurfing",
            })
    return pd.DataFrame(rows)


def generate_layering(accounts, n_chains=90, chain_len=(3, 6)):
    """Money hops rapidly through a chain of intermediary accounts to obscure
    its origin -> A -> B -> C -> D within minutes/hours of each other."""
    rows = []
    for _ in range(n_chains):
        chain = RNG.choice(accounts, size=RNG.integers(*chain_len), replace=False)
        amt = RNG.uniform(15_000, 200_000)
        base_time = START_DATE + timedelta(minutes=int(RNG.integers(0, DAYS * 24 * 60)))
        t = base_time
        for i in range(len(chain) - 1):
            # small skim at each hop, like real layering
            amt *= RNG.uniform(0.92, 0.99)
            t = t + timedelta(minutes=int(RNG.integers(5, 240)))
            rows.append({
                "timestamp": t,
                "sender_account": chain[i],
                "receiver_account": chain[i + 1],
                "amount": round(amt, 2),
                "payment_currency": "USD",
                "received_currency": "USD",
                "sender_bank_location": RNG.choice(LOCATIONS, p=_loc_probs(False)),
                "receiver_bank_location": RNG.choice(LOCATIONS, p=_loc_probs(False)),
                "payment_type": "Cross-border",
                "is_laundering": 1,
                "laundering_type": "layering",
            })
    return pd.DataFrame(rows)


def main():
    accounts = make_accounts(N_ACCOUNTS)

    normal = generate_normal_transactions(accounts, N_NORMAL_TXNS)
    structuring = generate_structuring(accounts)
    smurfing = generate_smurfing(accounts)
    layering = generate_layering(accounts)

    df = pd.concat([normal, structuring, smurfing, layering], ignore_index=True)
    df = df.sort_values("timestamp").reset_index(drop=True)
    df.insert(0, "transaction_id", [f"TXN{i:07d}" for i in range(len(df))])

    out_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "transactions.csv"
    df.to_csv(out_path, index=False)

    illicit_rate = df["is_laundering"].mean() * 100
    print(f"Wrote {len(df):,} transactions to {out_path}")
    print(f"Illicit rate: {illicit_rate:.2f}%  (real-world AML datasets are typically 0.5-3%)")
    print(df["laundering_type"].value_counts())


if __name__ == "__main__":
    main()
