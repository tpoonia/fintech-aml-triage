"""
AML Risk Scoring Engine

Run from the project root:
    python src/scoring/risk_scoring.py

Purpose:
1. Load the trained Random Forest AML classifier.
2. Score every alert with a suspicious-activity probability.
3. Convert the probability into a 0-100 risk score.
4. Add a small behavioral-risk component.
5. Assign LOW / MEDIUM / HIGH / CRITICAL risk levels.
6. Prioritize alerts for investigator review.
7. Save the scored alerts to data/processed/aml_risk_scored_alerts.csv
"""

from pathlib import Path
import json
import warnings

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = ROOT / "data" / "processed" / "ml_alert_dataset.csv"
MODEL_PATH = ROOT / "models" / "aml_random_forest.joblib"
OUTPUT_PATH = ROOT / "data" / "processed" / "aml_risk_scored_alerts.csv"
SUMMARY_PATH = ROOT / "models" / "risk_scoring_summary.json"

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# Risk-level definitions
# ---------------------------------------------------------------------

def risk_level(score: int) -> str:
    """Map a 0-100 risk score to an operational risk category."""

    if score >= 75:
        return "CRITICAL"

    if score >= 50:
        return "HIGH"

    if score >= 25:
        return "MEDIUM"

    return "LOW"


def priority(level: str) -> str:
    """Map risk level to investigator priority."""

    return {
        "CRITICAL": "P1",
        "HIGH": "P2",
        "MEDIUM": "P3",
        "LOW": "P4",
    }[level]


# ---------------------------------------------------------------------
# Helper functions for behavioral signals
# ---------------------------------------------------------------------

def minmax_score(
    series: pd.Series,
    lower: float = 0.0,
    upper: float = 1.0
) -> pd.Series:
    """
    Normalize a numeric series to 0-1 using robust percentile bounds.

    Percentile bounds prevent one extreme transaction from dominating
    the entire score.
    """

    values = pd.to_numeric(series, errors="coerce").fillna(0.0)

    lo = values.quantile(0.05)
    hi = values.quantile(0.95)

    if pd.isna(lo) or pd.isna(hi) or hi <= lo:
        return pd.Series(
            np.zeros(len(values)),
            index=values.index
        )

    normalized = (values - lo) / (hi - lo)

    return normalized.clip(
        lower=lower,
        upper=upper
    )


def binary_signal(
    df: pd.DataFrame,
    column: str
) -> pd.Series:
    """Return a clean 0/1 signal for a binary feature."""

    if column not in df.columns:
        return pd.Series(
            np.zeros(len(df)),
            index=df.index
        )

    values = df[column]

    if values.dtype == bool:
        return values.astype(float)

    # Handles 0/1, True/False, and common string representations.
    return (
        values.astype(str)
        .str.strip()
        .str.lower()
        .map(
            {
                "1": 1.0,
                "true": 1.0,
                "yes": 1.0,
                "y": 1.0,
                "0": 0.0,
                "false": 0.0,
                "no": 0.0,
                "n": 0.0,
            }
        )
        .fillna(
            pd.to_numeric(
                values,
                errors="coerce"
            )
        )
        .fillna(0.0)
        .clip(0, 1)
    )


# ---------------------------------------------------------------------
# Main scoring process
# ---------------------------------------------------------------------

def main() -> None:

    print("Loading AML dataset...")

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found:\n{DATA_PATH}\n\n"
            "Run first:\n"
            "python src/data/build_ml_dataset.py"
        )

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found:\n{MODEL_PATH}\n\n"
            "Run first:\n"
            "python src/models/train_model.py"
        )

    df = pd.read_csv(DATA_PATH)

    if df.empty:
        raise ValueError("The AML dataset is empty.")

    print(f"Dataset rows: {len(df):,}")
    print(f"Dataset columns: {len(df.columns)}")


    # -------------------------------------------------------------
    # ML probability
    # -------------------------------------------------------------

    print("\nLoading Random Forest model...")

    model = joblib.load(MODEL_PATH)

    # The training script deliberately excluded these columns.
    # We reproduce that exact exclusion here so scoring uses the
    # same feature space as training.

    drop_columns = [
        "alert_id",
        "customer_id",
        "transaction_id",
        "alert_timestamp",
        "investigation_outcome",
        "target",
        "is_suspicious",
    ]

    feature_columns = [
        column
        for column in df.columns
        if column not in drop_columns
    ]

    X = df[feature_columns].copy()

    print("Generating ML probabilities...")

    ml_probability = model.predict_proba(X)[:, 1]

    df["ml_probability"] = ml_probability


    # -------------------------------------------------------------
    # Behavioral risk component
    # -------------------------------------------------------------

    print("Calculating behavioral risk signals...")

    signals = []


    # 1. Unusual transaction amount

    if "amount_deviation_ratio" in df.columns:

        amount_signal = minmax_score(
            df["amount_deviation_ratio"]
        )

        signals.append(
            (
                "amount_deviation",
                amount_signal,
                0.25
            )
        )


    # 2. Recent transaction velocity

    if "transactions_last_7_days" in df.columns:

        velocity_signal = minmax_score(
            df["transactions_last_7_days"]
        )

        signals.append(
            (
                "transaction_velocity",
                velocity_signal,
                0.20
            )
        )


    # 3. Counterparty diversity

    if "unique_counterparties" in df.columns:

        counterparty_signal = minmax_score(
            df["unique_counterparties"]
        )

        signals.append(
            (
                "counterparty_diversity",
                counterparty_signal,
                0.15
            )
        )


    # 4. Geographic diversity

    if "unique_countries" in df.columns:

        country_signal = minmax_score(
            df["unique_countries"]
        )

        signals.append(
            (
                "country_diversity",
                country_signal,
                0.15
            )
        )


    # 5. Cross-border activity

    if "is_cross_border" in df.columns:

        cross_border_signal = binary_signal(
            df,
            "is_cross_border"
        )

        signals.append(
            (
                "cross_border",
                cross_border_signal,
                0.15
            )
        )


    # 6. Outgoing transaction behavior

    if "outgoing_ratio" in df.columns:

        outgoing_signal = minmax_score(
            df["outgoing_ratio"]
        )

        signals.append(
            (
                "outgoing_ratio",
                outgoing_signal,
                0.10
            )
        )


    if signals:

        total_weight = sum(
            weight
            for _, _, weight in signals
        )

        behavioral_risk = sum(
            signal * weight
            for _, signal, weight in signals
        ) / total_weight

    else:

        behavioral_risk = pd.Series(
            np.zeros(len(df)),
            index=df.index
        )

    df["behavioral_risk"] = behavioral_risk.clip(
        0,
        1
    )


    # -------------------------------------------------------------
    # Final risk score
    # -------------------------------------------------------------
    #
    # ML receives 70% of the score.
    # Behavioral signals receive 30%.
    #
    # This keeps the trained classifier as the primary decision
    # signal while allowing operational behavioral context to
    # influence prioritization.
    #

    final_score = (
        0.70 * df["ml_probability"]
        + 0.30 * df["behavioral_risk"]
    ) * 100

    df["risk_score"] = (
        final_score
        .round()
        .clip(0, 100)
        .astype(int)
    )

    df["risk_level"] = (
        df["risk_score"]
        .apply(risk_level)
    )

    df["priority"] = (
        df["risk_level"]
        .apply(priority)
    )


    # -------------------------------------------------------------
    # Human-readable reason flags
    # -------------------------------------------------------------

    print("Generating risk indicators...")


    def build_reasons(row):

        reasons = []


        if row.get(
            "amount_deviation_ratio",
            0
        ) >= 3:

            reasons.append(
                "unusually high transaction amount"
            )


        if row.get(
            "transactions_last_7_days",
            0
        ) >= 8:

            reasons.append(
                "high recent transaction velocity"
            )


        if row.get(
            "unique_counterparties",
            0
        ) >= 5:

            reasons.append(
                "multiple counterparties"
            )


        if row.get(
            "unique_countries",
            0
        ) >= 2:

            reasons.append(
                "multi-country activity"
            )


        if row.get(
            "is_cross_border",
            0
        ) in [
            1,
            True,
            "1",
            "true",
            "True"
        ]:

            reasons.append(
                "cross-border activity"
            )


        if row.get(
            "outgoing_ratio",
            0
        ) >= 0.75:

            reasons.append(
                "high outgoing transaction ratio"
            )


        if row["ml_probability"] >= 0.75:

            reasons.append(
                "high ML suspicious-activity probability"
            )


        if not reasons:

            reasons.append(
                "no dominant high-risk behavioral indicator"
            )


        return "; ".join(reasons)


    df["risk_reasons"] = df.apply(
        build_reasons,
        axis=1
    )


    # -------------------------------------------------------------
    # Investigator queue
    # -------------------------------------------------------------

    # Highest risk and highest priority first.

    priority_order = {
        "P1": 0,
        "P2": 1,
        "P3": 2,
        "P4": 3,
    }

    df["_priority_order"] = (
        df["priority"]
        .map(priority_order)
    )

    df = df.sort_values(
        by=[
            "_priority_order",
            "risk_score"
        ],
        ascending=[
            True,
            False
        ],
    ).drop(
        columns="_priority_order"
    )


    # -------------------------------------------------------------
    # Save results
    # -------------------------------------------------------------

    df.to_csv(
        OUTPUT_PATH,
        index=False
    )


    summary = {

        "dataset_rows": int(
            len(df)
        ),

        "mean_risk_score": float(
            df["risk_score"].mean()
        ),

        "median_risk_score": float(
            df["risk_score"].median()
        ),

        "risk_level_distribution": {
            str(k): int(v)
            for k, v in (
                df["risk_level"]
                .value_counts()
                .to_dict()
                .items()
            )
        },

        "priority_distribution": {
            str(k): int(v)
            for k, v in (
                df["priority"]
                .value_counts()
                .to_dict()
                .items()
            )
        },

        "average_ml_probability": float(
            df["ml_probability"].mean()
        ),

        "average_behavioral_risk": float(
            df["behavioral_risk"].mean()
        ),

        "output_file": str(
            OUTPUT_PATH
        ),
    }


    with open(
        SUMMARY_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            summary,
            file,
            indent=2
        )


    # -------------------------------------------------------------
    # Terminal summary
    # -------------------------------------------------------------

    print(
        "\n" + "=" * 60
    )

    print(
        "AML RISK SCORING COMPLETE"
    )

    print(
        "=" * 60
    )


    print("\nOutput file:")

    print(
        OUTPUT_PATH
    )


    print("\nRisk level distribution:")

    print(
        df["risk_level"]
        .value_counts()
    )


    print("\nPriority distribution:")

    print(
        df["priority"]
        .value_counts()
        .sort_index()
    )


    print("\nTop 10 highest-risk alerts:")

    display_columns = [
        column
        for column in [
            "alert_id",
            "customer_id",
            "transaction_amount",
            "ml_probability",
            "risk_score",
            "risk_level",
            "priority",
            "risk_reasons",
        ]
        if column in df.columns
    ]

    print(
        df[display_columns]
        .head(10)
        .to_string(index=False)
    )


    print("\nSummary:")

    print(
        f"Average risk score: "
        f"{df['risk_score'].mean():.2f}"
    )

    print(
        f"Median risk score:  "
        f"{df['risk_score'].median():.2f}"
    )

    print(
        f"Average ML probability: "
        f"{df['ml_probability'].mean():.4f}"
    )


    print("\nSaved:")

    print(
        OUTPUT_PATH
    )

    print(
        SUMMARY_PATH
    )


if __name__ == "__main__":
    main()