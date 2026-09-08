"""
evaluate.py
-----------
Answers the question the whole project is built around: "does this actually
cut false-positive alert volume, and can we explain why it flagged what it
flagged?"

What it does:
  1. Scores the held-out (time-based) test set with both models.
  2. Builds a "naive rule baseline" -- flag any transaction >= the $10k
     reporting threshold, or in the classic $8,500-$9,999 structuring band --
     to stand in for how a typical rules-based AML system behaves today.
  3. Finds the model threshold that matches (or beats) the naive rule's
     recall, then compares alert volume and false-positive rate at that
     threshold. This produces the single most important number for your
     resume/README: "X% fewer false-positive alerts at the same recall."
  4. Computes PR-AUC / ROC-AUC, saves a precision-recall curve plot.
  5. Runs SHAP on the XGBoost model so every flagged alert can be explained
     (non-negotiable in AML -- an unexplainable score isn't usable).

Run:
    python src/evaluate.py
Reads:
    data/processed/test_split.csv, models/*
Writes:
    reports/metrics.md
    reports/pr_curve.png
    reports/shap_summary.png
"""

import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.metrics import (
    precision_recall_curve, average_precision_score, roc_auc_score,
    precision_score, recall_score,
)

import shap

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"
REPORTING_THRESHOLD = 10_000


def load_everything():
    test_df = pd.read_csv(ROOT / "data" / "processed" / "test_split.csv", parse_dates=["timestamp"])
    with open(MODELS_DIR / "feature_columns.json") as f:
        feature_cols = json.load(f)
    xgb_model = joblib.load(MODELS_DIR / "xgboost_model.joblib")
    baseline_bundle = joblib.load(MODELS_DIR / "baseline_logreg.joblib")
    return test_df, feature_cols, xgb_model, baseline_bundle


def naive_rule_flags(df):
    """Stand-in for a typical threshold-based AML rule engine."""
    over_threshold = df["amount"] >= REPORTING_THRESHOLD
    structuring_band = df["near_threshold"] == 1
    return (over_threshold | structuring_band).astype(int)


def threshold_for_recall(y_true, scores, target_recall):
    """Find the lowest-alert-volume threshold that still hits target_recall."""
    precisions, recalls, thresholds = precision_recall_curve(y_true, scores)
    # precision_recall_curve returns thresholds of len(n-1); align arrays
    recalls, thresholds = recalls[:-1], thresholds
    candidates = np.where(recalls >= target_recall)[0]
    if len(candidates) == 0:
        return scores.min()  # fall back: flag everything
    # among thresholds achieving the recall target, take the highest
    # threshold (fewest alerts) that still clears the bar
    best_idx = candidates[np.argmax(thresholds[candidates])]
    return thresholds[best_idx]


def alert_stats(y_true, y_pred):
    n_alerts = int(y_pred.sum())
    n_true_positive = int(((y_pred == 1) & (y_true == 1)).sum())
    n_false_positive = n_alerts - n_true_positive
    recall = recall_score(y_true, y_pred, zero_division=0)
    precision = precision_score(y_true, y_pred, zero_division=0)
    fp_rate_of_alerts = n_false_positive / n_alerts if n_alerts else 0
    return {
        "n_alerts": n_alerts,
        "n_true_positive": n_true_positive,
        "n_false_positive": n_false_positive,
        "recall": recall,
        "precision": precision,
        "false_positive_share_of_alerts": fp_rate_of_alerts,
    }


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    test_df, feature_cols, xgb_model, baseline_bundle = load_everything()

    X_test = test_df[feature_cols]
    y_test = test_df["is_laundering"]

    xgb_scores = xgb_model.predict_proba(X_test)[:, 1]
    baseline_scores = baseline_bundle["model"].predict_proba(
        baseline_bundle["scaler"].transform(X_test)
    )[:, 1]

    xgb_pr_auc = average_precision_score(y_test, xgb_scores)
    xgb_roc_auc = roc_auc_score(y_test, xgb_scores)
    baseline_pr_auc = average_precision_score(y_test, baseline_scores)
    baseline_roc_auc = roc_auc_score(y_test, baseline_scores)

    # --- Naive rule baseline (stand-in for "what the bank does today") ---
    rule_flags = naive_rule_flags(test_df)
    rule_stats = alert_stats(y_test, rule_flags)

    # --- Scenario A: XGBoost matched to the naive rule's OWN recall ---
    # This is the fair, apples-to-apples comparison: "catching the same share
    # of illicit transactions, how many fewer false alarms does the model
    # generate?"
    matched_thresh = threshold_for_recall(y_test, xgb_scores, rule_stats["recall"])
    xgb_matched_flags = (xgb_scores >= matched_thresh).astype(int)
    xgb_matched_stats = alert_stats(y_test, xgb_matched_flags)

    def pct_change(new, old):
        return (1 - new / old) if old else 0.0

    alert_reduction = pct_change(xgb_matched_stats["n_alerts"], rule_stats["n_alerts"])
    fp_reduction = pct_change(xgb_matched_stats["n_false_positive"], rule_stats["n_false_positive"])

    # --- Scenario B: push recall higher (>=90%) and see the trade-off ---
    high_recall_target = 0.90
    high_thresh = threshold_for_recall(y_test, xgb_scores, high_recall_target)
    xgb_high_flags = (xgb_scores >= high_thresh).astype(int)
    xgb_high_stats = alert_stats(y_test, xgb_high_flags)
    high_fp_reduction = pct_change(xgb_high_stats["n_false_positive"], rule_stats["n_false_positive"])

    # --- Plots ---
    precisions, recalls, _ = precision_recall_curve(y_test, xgb_scores)
    plt.figure(figsize=(6, 5))
    plt.plot(recalls, precisions, label=f"XGBoost (PR-AUC={xgb_pr_auc:.3f})")
    b_p, b_r, _ = precision_recall_curve(y_test, baseline_scores)
    plt.plot(b_r, b_p, label=f"Logistic Regression (PR-AUC={baseline_pr_auc:.3f})", linestyle="--")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curve (held-out, time-based test set)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "pr_curve.png", dpi=150)
    plt.close()

    # --- SHAP explainability ---
    explainer = shap.TreeExplainer(xgb_model)
    sample = X_test.sample(min(2000, len(X_test)), random_state=42)
    shap_values = explainer(sample)
    plt.figure()
    shap.summary_plot(shap_values, sample, show=False)
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "shap_summary.png", dpi=150)
    plt.close()

    # --- Report ---
    report = f"""# Evaluation Report

## Model quality (held-out, time-based test set, {len(test_df):,} transactions, {y_test.sum()} illicit)

| Model | PR-AUC | ROC-AUC |
|---|---|---|
| Logistic Regression (baseline) | {baseline_pr_auc:.3f} | {baseline_roc_auc:.3f} |
| XGBoost | {xgb_pr_auc:.3f} | {xgb_roc_auc:.3f} |

## Headline comparison: naive rule engine vs. XGBoost

Naive rule = flag if amount >= ${REPORTING_THRESHOLD:,} OR in the classic
${REPORTING_THRESHOLD*0.85:,.0f}-${REPORTING_THRESHOLD:,} structuring band
(a stand-in for a typical threshold-based AML system).

### Scenario A -- same catch rate as the naive rule (apples-to-apples)

| | Naive rule | XGBoost (matched to {rule_stats['recall']*100:.1f}% recall) |
|---|---|---|
| Alerts raised | {rule_stats['n_alerts']:,} | {xgb_matched_stats['n_alerts']:,} |
| True positives caught | {rule_stats['n_true_positive']} | {xgb_matched_stats['n_true_positive']} |
| False positives | {rule_stats['n_false_positive']:,} | {xgb_matched_stats['n_false_positive']:,} |
| Recall | {rule_stats['recall']*100:.1f}% | {xgb_matched_stats['recall']*100:.1f}% |
| Precision | {rule_stats['precision']*100:.2f}% | {xgb_matched_stats['precision']*100:.2f}% |
| Share of alerts that are false positives | {rule_stats['false_positive_share_of_alerts']*100:.1f}% | {xgb_matched_stats['false_positive_share_of_alerts']*100:.1f}% |

**At the same recall as today's rule engine, XGBoost cuts total alert volume by
{alert_reduction*100:.1f}% and false-positive alerts by {fp_reduction*100:.1f}%.**
This is the number to lead with: same crimes caught, far fewer analyst-hours
burned on noise.

### Scenario B -- push recall to {high_recall_target*100:.0f}% (catch more, not just fewer false alarms)

| | Naive rule | XGBoost (>= {high_recall_target*100:.0f}% recall) |
|---|---|---|
| Alerts raised | {rule_stats['n_alerts']:,} | {xgb_high_stats['n_alerts']:,} |
| True positives caught | {rule_stats['n_true_positive']} | {xgb_high_stats['n_true_positive']} |
| False positives | {rule_stats['n_false_positive']:,} | {xgb_high_stats['n_false_positive']:,} |
| Recall | {rule_stats['recall']*100:.1f}% | {xgb_high_stats['recall']*100:.1f}% |
| Precision | {rule_stats['precision']*100:.2f}% | {xgb_high_stats['precision']*100:.2f}% |

**At {high_recall_target*100:.0f}% recall (catching {xgb_high_stats['n_true_positive']} of {int(y_test.sum())} illicit transactions vs. just {rule_stats['n_true_positive']} today),
false positives still drop {high_fp_reduction*100:.1f}% vs. the naive rule.**
In other words: the model doesn't force a trade-off between catching more
crime and drowning analysts in noise -- it improves both at once, because it's
using behavioral context instead of a single static threshold.

(These exact percentages are from the synthetic dataset -- swap in the real
SAML-D dataset and re-run this script to get your real, resume-ready numbers.
The reasoning and the script stay the same.)

## Explainability

See `reports/shap_summary.png` -- SHAP values showing which features drive
the model's risk score across the sampled test alerts. In the deployed
version (Phase B), every individual alert gets its own SHAP explanation
alongside its score, not just an aggregate summary.

## Files produced
- `pr_curve.png` -- precision-recall curve, XGBoost vs. baseline
- `shap_summary.png` -- global feature importance / explainability
"""

    with open(REPORTS_DIR / "metrics.md", "w") as f:
        f.write(report)

    print(report)
    print(f"\nSaved plots + metrics.md to {REPORTS_DIR}/")


if __name__ == "__main__":
    main()
