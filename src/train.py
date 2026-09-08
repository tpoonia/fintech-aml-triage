"""
train.py
--------
Trains two models on the engineered features:
  1. Logistic Regression baseline (fast, interpretable, sets a floor)
  2. XGBoost (the model we actually care about)

Two things matter a lot here, and are common interview questions for this
kind of project -- both are handled below on purpose:

  - Class imbalance: illicit transactions are ~1% of the data. We handle this
    with `scale_pos_weight` in XGBoost (and `class_weight="balanced"` in the
    baseline) rather than plain accuracy-driven training, which would happily
    predict "not laundering" for everything and still score 99% accuracy.

  - Time-based split: we split train/test by *time* (train on the first 80%
    of days, test on the most recent 20%), not a random shuffle. A random
    split would leak future account behavior into training and make the
    model look better than it would in production, where you only ever have
    the past to predict the future.

Run:
    python src/train.py
Reads:
    data/processed/features.csv
Writes:
    models/baseline_logreg.joblib
    models/xgboost_model.joblib
    models/feature_columns.json
    data/processed/test_split.csv   (kept for evaluate.py)
"""

import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

ROOT = Path(__file__).resolve().parent.parent
FEATURES_PATH = ROOT / "data" / "processed" / "features.csv"
MODELS_DIR = ROOT / "models"

NON_FEATURE_COLS = {
    "transaction_id", "timestamp", "sender_account", "receiver_account",
    "payment_currency", "received_currency", "sender_bank_location",
    "receiver_bank_location", "payment_type", "is_laundering", "laundering_type",
}

TEST_FRACTION = 0.2  # most recent 20% of days held out for testing


def load_features():
    df = pd.read_csv(FEATURES_PATH, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def time_based_split(df):
    cutoff_idx = int(len(df) * (1 - TEST_FRACTION))
    cutoff_time = df.iloc[cutoff_idx]["timestamp"]
    train_df = df[df["timestamp"] < cutoff_time].copy()
    test_df = df[df["timestamp"] >= cutoff_time].copy()
    print(f"Train: {len(train_df):,} rows (up to {cutoff_time.date()}), "
          f"illicit rate {train_df['is_laundering'].mean()*100:.2f}%")
    print(f"Test:  {len(test_df):,} rows (from {cutoff_time.date()}), "
          f"illicit rate {test_df['is_laundering'].mean()*100:.2f}%")
    return train_df, test_df


def get_feature_columns(df):
    return [c for c in df.columns if c not in NON_FEATURE_COLS]


def train_baseline(X_train, y_train):
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)
    model = LogisticRegression(class_weight="balanced", max_iter=1000)
    model.fit(X_scaled, y_train)
    return model, scaler


def train_xgboost(X_train, y_train):
    pos = y_train.sum()
    neg = len(y_train) - pos
    scale_pos_weight = neg / max(pos, 1)  # upweight the rare illicit class
    print(f"scale_pos_weight = {scale_pos_weight:.1f} (neg={neg:,}, pos={pos:,})")

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="aucpr",
        random_state=42,
    )
    model.fit(X_train, y_train)
    return model


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    df = load_features()
    train_df, test_df = time_based_split(df)

    feature_cols = get_feature_columns(df)
    X_train, y_train = train_df[feature_cols], train_df["is_laundering"]
    X_test, y_test = test_df[feature_cols], test_df["is_laundering"]

    print("\nTraining baseline logistic regression...")
    baseline_model, scaler = train_baseline(X_train, y_train)

    print("Training XGBoost...")
    xgb_model = train_xgboost(X_train, y_train)

    joblib.dump({"model": baseline_model, "scaler": scaler}, MODELS_DIR / "baseline_logreg.joblib")
    joblib.dump(xgb_model, MODELS_DIR / "xgboost_model.joblib")
    with open(MODELS_DIR / "feature_columns.json", "w") as f:
        json.dump(feature_cols, f, indent=2)

    # keep the test split (with predictions we'll need for evaluate.py)
    test_out = test_df.copy()
    test_out.to_csv(ROOT / "data" / "processed" / "test_split.csv", index=False)

    print(f"\nSaved models to {MODELS_DIR}/")
    print("Next: python src/evaluate.py")


if __name__ == "__main__":
    main()
