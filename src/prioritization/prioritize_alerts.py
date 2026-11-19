"""Stage 4 - AML Alert Prioritization."""
from pathlib import Path
import json
import os
import sys
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.triage_config import PRIORITY_ORDER, priority_for_level, risk_level_for_score
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
EXPLAINED_PATH = PROCESSED_DIR / "aml_explained_alerts.csv"
RISK_SCORED_PATH = PROCESSED_DIR / "aml_risk_scored_alerts.csv"
QUEUE_FORMAT = os.environ.get("AML_QUEUE_FORMAT", "csv")
if QUEUE_FORMAT not in {"csv", "trimmed-csv", "parquet"}:
    raise ValueError(f"Unsupported AML_QUEUE_FORMAT: {QUEUE_FORMAT}")
OUTPUT_PATH = PROCESSED_DIR / (
    "aml_prioritized_alerts.parquet" if QUEUE_FORMAT == "parquet" else "aml_prioritized_alerts.csv"
)
SUMMARY_PATH = MODELS_DIR / "prioritization_summary.json"

def first_existing_column(df, candidates):
    return next((c for c in candidates if c in df.columns), None)

def numeric_series(df, column, default=0.0):
    if column is None:
        return pd.Series(default, index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce").fillna(default)

def normalize_0_100(series):
    values = pd.to_numeric(series, errors="coerce").fillna(0.0)
    lo, hi = values.min(), values.max()
    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return pd.Series(50.0, index=values.index)
    return ((values - lo) / (hi - lo) * 100).clip(0, 100)

def build_reason(row):
    reasons = []
    score = float(row["risk_score"])
    level_reason = {
        "CRITICAL": "very high model risk score",
        "HIGH": "high model risk score",
        "MEDIUM": "moderate model risk score",
    }
    if row["risk_level"] in level_reason:
        reasons.append(level_reason[row["risk_level"]])
    checks = [
        ("amount_deviation_signal", "large transaction amount deviation"),
        ("recent_activity_signal", "elevated recent transaction activity"),
        ("velocity_signal", "high transaction velocity"),
        ("cross_border_signal", "cross-border activity"),
        ("counterparty_signal", "unusual counterparty activity"),
    ]
    for col, reason in checks:
        if float(row[col]) >= 70: reasons.append(reason)
    return "; ".join(reasons[:4]) or "risk score and available behavioral signals"

def main():
    print("=" * 72)
    print("STAGE 4 - AML ALERT PRIORITIZATION")
    print("=" * 72)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    if EXPLAINED_PATH.exists():
        input_path = EXPLAINED_PATH
    elif RISK_SCORED_PATH.exists():
        input_path = RISK_SCORED_PATH
    else:
        raise FileNotFoundError(f"No input found. Expected {EXPLAINED_PATH} or {RISK_SCORED_PATH}")

    print(f"\nLoading: {input_path}")
    df = pd.read_csv(input_path)
    if df.empty: raise ValueError("Input dataset is empty.")
    print(f"Dataset shape: {df.shape}")

    risk_col = first_existing_column(df, ["risk_score", "ml_risk_score", "risk_probability", "ml_probability", "probability"])
    if risk_col is None:
        raise ValueError("No risk/probability column found.")
    raw = numeric_series(df, risk_col)
    df["risk_score"] = ((raw * 100) if raw.max() <= 1 else raw).clip(0, 100).round(2)
    df["risk_level"] = df["risk_score"].apply(risk_level_for_score)
    df["priority"] = df["risk_level"].map(priority_for_level)

    amount_col = first_existing_column(df, ["amount_deviation_ratio", "amount_deviation", "transaction_amount_deviation"])
    recent_col = first_existing_column(df, ["transactions_last_7_days", "customer_transactions_last_7_days", "recent_transaction_count"])
    velocity_col = first_existing_column(df, ["transactions_last_7_days", "customer_transaction_count", "transaction_velocity"])
    cross_col = first_existing_column(df, ["is_cross_border", "cross_border", "cross_border_flag"])
    counter_col = first_existing_column(df, ["unique_counterparties", "customer_unique_counterparties", "counterparty_count"])

    df["amount_deviation_signal"] = normalize_0_100(numeric_series(df, amount_col))
    df["recent_activity_signal"] = normalize_0_100(numeric_series(df, recent_col))
    df["velocity_signal"] = normalize_0_100(numeric_series(df, velocity_col))
    cross = numeric_series(df, cross_col)
    df["cross_border_signal"] = cross.clip(0, 1) * 100 if cross.nunique() <= 2 else normalize_0_100(cross)
    df["counterparty_signal"] = normalize_0_100(numeric_series(df, counter_col))

    df["priority_score"] = (0.60*df["risk_score"] + 0.10*df["amount_deviation_signal"] + 0.10*df["recent_activity_signal"] + 0.10*df["velocity_signal"] + 0.05*df["cross_border_signal"] + 0.05*df["counterparty_signal"]).clip(0,100).round(2)
    df["priority_reason"] = df.apply(build_reason, axis=1)

    explanation_col = first_existing_column(df, ["explanation", "shap_explanation", "risk_explanation", "top_reason"])
    df["investigator_explanation"] = df[explanation_col].fillna("").astype(str) if explanation_col else ""

    df["_priority_order"] = df["priority"].map(PRIORITY_ORDER).fillna(9)
    df = df.sort_values(["_priority_order","priority_score","risk_score"], ascending=[True,False,False], kind="mergesort").reset_index(drop=True)
    df["queue_position"] = np.arange(1, len(df)+1)

    preferred = ["queue_position","alert_id","customer_id","alert_timestamp","alert_type","triggered_rule","transaction_id","transaction_amount","risk_score","risk_level","priority_score","priority","priority_reason","investigator_explanation","investigation_outcome"]
    cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred and c not in {"_priority_order", "target"}]
    out = df[cols]
    if QUEUE_FORMAT == "trimmed-csv":
        dashboard_api_columns = {
            "queue_position", "alert_id", "customer_id", "alert_timestamp", "alert_type",
            "triggered_rule", "transaction_id", "transaction_amount", "risk_score", "risk_level",
            "priority_score", "priority", "priority_reason", "investigator_explanation",
            "investigation_outcome", "risk_reasons",
            "ml_probability", "behavioral_risk", "amount_deviation_signal", "recent_activity_signal",
            "velocity_signal", "cross_border_signal", "counterparty_signal", "transactions_last_7_days",
            "avg_amount_last_7_days", "prior_transaction_count", "prior_avg_transaction_amount",
            "customer_transaction_count", "customer_avg_transaction_amount", "customer_std_transaction_amount",
            "customer_max_transaction_amount", "customer_min_transaction_amount", "customer_total_transaction_amount",
            "unique_counterparties", "unique_countries", "outgoing_ratio", "customer_type", "customer_country",
            "account_age_days", "monthly_income", "risk_profile", "income_ratio", "amount_deviation_ratio",
            "is_cross_border", "country",
        }
        out = out[[c for c in out.columns if c in dashboard_api_columns]]
    if QUEUE_FORMAT == "parquet":
        out.to_parquet(OUTPUT_PATH, index=False)
    else:
        out.to_csv(OUTPUT_PATH, index=False)

    pc = out["priority"].value_counts().reindex(["P1","P2","P3","P4"], fill_value=0).astype(int).to_dict()
    rc = out["risk_level"].value_counts().reindex(["CRITICAL","HIGH","MEDIUM","LOW"], fill_value=0).astype(int).to_dict()
    summary = {"stage":"Stage 4 - AML Alert Prioritization","input_file":input_path.relative_to(PROJECT_ROOT).as_posix(),"output_file":OUTPUT_PATH.relative_to(PROJECT_ROOT).as_posix(),"queue_format":QUEUE_FORMAT,"total_alerts":int(len(out)),"average_risk_score":round(float(out.risk_score.mean()),4),"average_priority_score":round(float(out.priority_score.mean()),4),"priority_distribution":pc,"risk_level_distribution":rc,"priority_weights":{"ml_risk_score":0.60,"amount_deviation":0.10,"recent_activity":0.10,"transaction_velocity":0.10,"cross_border":0.05,"counterparty_activity":0.05},"note":"Priority follows the shared risk-score tier; the weighted priority score only orders alerts within a tier. Scores support human review and are not proof of wrongdoing."}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\nTotal alerts prioritized: {len(out):,}")
    print("\nRisk distribution:")
    for k,v in rc.items(): print(f"  {k:<10} {v:,}")
    print("\nPriority distribution:")
    for k,v in pc.items(): print(f"  {k:<5} {v:,}")
    show = [c for c in ["queue_position","alert_id","risk_score","risk_level","priority_score","priority"] if c in out.columns]
    print("\nTop 10 queue:")
    print(out[show].head(10).to_string(index=False))
    print(f"\nSaved: {OUTPUT_PATH}")
    print(f"Saved: {SUMMARY_PATH}")
    print("\nStage 4 finished successfully.")

if __name__ == "__main__":
    main()
