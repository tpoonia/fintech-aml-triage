"""
features.py
------------
Turns raw transactions into the behavioral features an AML model actually
needs. Static rules ("flag anything over $10k") only look at a single
transaction in isolation — the whole point of using ML here is to look at
*behavior over time*: how does this transaction compare to what this account
normally does, and what's happening around it?

Features built:
  Transaction-level
    - log_amount, near_threshold (classic structuring signal)
    - hour_of_day, is_weekend
    - is_cross_border, sender_high_risk_loc, receiver_high_risk_loc
    - payment_type one-hot encoding
  Sender behavior (rolling windows, time-based -> no lookahead into the future
  beyond the window itself)
    - sender_txn_count_24h, sender_total_amount_24h, sender_avg_amount_24h
    - sender_unique_receivers_24h  (fan-out -> smurfing signal)
    - amount_zscore_vs_sender_history (uses only *prior* transactions, via
      shift(1), so today's transaction can't inflate its own baseline)
  Receiver behavior
    - receiver_unique_senders_24h (fan-in -> smurfing/consolidation signal)

Run:
    python src/features.py
Reads:
    data/raw/transactions.csv
Writes:
    data/processed/features.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path

HIGH_RISK_LOCATIONS = {"KY", "PA", "AE", "NG"}
REPORTING_THRESHOLD = 10_000

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "raw" / "transactions.csv"
OUT_PATH = ROOT / "data" / "processed" / "features.csv"


def load_raw():
    df = pd.read_csv(RAW_PATH, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def add_transaction_level_features(df):
    df["log_amount"] = np.log1p(df["amount"])
    df["near_threshold"] = (
        (df["amount"] >= REPORTING_THRESHOLD * 0.85) & (df["amount"] < REPORTING_THRESHOLD)
    ).astype(int)
    df["hour_of_day"] = df["timestamp"].dt.hour
    df["is_weekend"] = df["timestamp"].dt.dayofweek.isin([5, 6]).astype(int)
    df["is_cross_border"] = (df["sender_bank_location"] != df["receiver_bank_location"]).astype(int)
    df["sender_high_risk_loc"] = df["sender_bank_location"].isin(HIGH_RISK_LOCATIONS).astype(int)
    df["receiver_high_risk_loc"] = df["receiver_bank_location"].isin(HIGH_RISK_LOCATIONS).astype(int)

    payment_dummies = pd.get_dummies(df["payment_type"], prefix="ptype")
    df = pd.concat([df, payment_dummies], axis=1)
    return df


def add_rolling_account_features(df):
    """Rolling, time-window behavioral features per account.

    We use pandas' time-based rolling window (`.rolling("24h", on="timestamp")`)
    *within each account group*, which only looks backward from each
    transaction -- this is what makes it safe to use at scoring time (you'd
    never accidentally use information from the future). Keeping df's own
    unique integer index (instead of indexing by timestamp, which has many
    duplicate values across 200k rows) is what lets us assign the results
    back safely.
    """
    df = df.reset_index(drop=True)  # guarantee a unique, stable row index (row_id == position)

    # NOTE: pandas' groupby(...).rolling("24h", on=...) returns a result indexed
    # by (group, timestamp) -- and timestamp has many duplicate values across
    # 200k rows, which makes it unsafe to assign straight back onto df. Instead
    # we loop over each account's own rows (still vectorized *within* each
    # account, just not across accounts) and assign back using each row's
    # original, always-unique row_id.
    def _rolling(group_col, value_col, agg):
        result = pd.Series(index=df.index, dtype=float)
        for _, row_ids in df.groupby(group_col).groups.items():
            sub = df.loc[row_ids].set_index("timestamp")[value_col]
            r = getattr(sub.rolling("24h"), agg)()
            result.loc[row_ids] = r.values
        return result

    def _rolling_nunique(group_col, code_col):
        # pandas' rolling machinery only works on numeric data, so we roll
        # over integer "codes" (see pd.factorize below) instead of the raw
        # account-id strings -- counting unique codes is equivalent.
        result = pd.Series(index=df.index, dtype=float)
        for _, row_ids in df.groupby(group_col).groups.items():
            sub = df.loc[row_ids].set_index("timestamp")[code_col]
            r = sub.rolling("24h").apply(lambda w: len(set(w)), raw=True)
            result.loc[row_ids] = r.values
        return result

    # --- Sender-side rolling stats ---
    df["sender_txn_count_24h"] = _rolling("sender_account", "amount", "count")
    df["sender_total_amount_24h"] = _rolling("sender_account", "amount", "sum")
    df["sender_avg_amount_24h"] = _rolling("sender_account", "amount", "mean")

    # unique receivers touched by this sender in the last 24h (fan-out / smurfing)
    df["_receiver_code"] = pd.factorize(df["receiver_account"])[0]
    df["sender_unique_receivers_24h"] = _rolling_nunique("sender_account", "_receiver_code")

    # unique senders touching this receiver in the last 24h (fan-in / consolidation)
    df["_sender_code"] = pd.factorize(df["sender_account"])[0]
    df["receiver_unique_senders_24h"] = _rolling_nunique("receiver_account", "_sender_code")
    df = df.drop(columns=["_receiver_code", "_sender_code"])

    # amount z-score vs the sender's *prior* history only (shift(1) excludes
    # the current transaction so a large transaction can't normalize itself)
    prior_mean = (
        df.groupby("sender_account")["amount"]
        .apply(lambda s: s.shift(1).expanding().mean())
        .reset_index(level=0, drop=True).sort_index()
    )
    prior_std = (
        df.groupby("sender_account")["amount"]
        .apply(lambda s: s.shift(1).expanding().std())
        .reset_index(level=0, drop=True).sort_index()
    )
    df["amount_zscore_vs_sender_history"] = (df["amount"] - prior_mean) / prior_std.replace(0, np.nan)

    return df


def finalize(df):
    # first transaction(s) for a fresh account have no prior history -> fill sensibly
    fill_zero_cols = [
        "sender_txn_count_24h", "sender_total_amount_24h", "sender_avg_amount_24h",
        "sender_unique_receivers_24h", "receiver_unique_senders_24h",
    ]
    for c in fill_zero_cols:
        df[c] = df[c].fillna(0)
    df["amount_zscore_vs_sender_history"] = df["amount_zscore_vs_sender_history"].fillna(0)
    return df


def main():
    df = load_raw()
    df = add_transaction_level_features(df)
    df = add_rolling_account_features(df)
    df = finalize(df)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(df):,} rows x {df.shape[1]} columns to {OUT_PATH}")
    print("New feature columns:")
    feature_cols = [c for c in df.columns if c not in (
        "transaction_id", "timestamp", "sender_account", "receiver_account",
        "payment_currency", "received_currency", "sender_bank_location",
        "receiver_bank_location", "payment_type", "is_laundering", "laundering_type",
    )]
    print(feature_cols)


if __name__ == "__main__":
    main()
