# AML Alert Triage & False-Positive Reduction Engine

Machine learning that re-scores anti-money-laundering alerts by predicted risk, so compliance
analysts review the alerts that matter instead of a queue that is mostly noise — with a SHAP
explanation attached to every score, because an AML decision that can't be explained to a
regulator can't be used.

---

## The problem

Banks and fintechs are legally required to monitor transactions for money laundering, but the
rules-based systems most of them run are blunt instruments — "flag anything over $10,000."

- Roughly **95% of AML alerts are false positives** — the flagged transaction is legitimate.
- Each alert still needs human review: regulators budget ~2 hours, but real investigations
  stretch to **22 hours** once documentation and review cycles are counted.
- Global AML compliance spend exceeds **$274 billion a year**, most of it consumed by chasing
  noise rather than catching financial crime.
- Customers feel it too: frozen accounts and delayed transfers drive churn.

A static threshold can't tell a $10,000 payroll deposit from laundering, and it silently misses
a launderer who sends four transfers of $9,400 to stay under the line. The industry fix is
behavioral monitoring — scoring transactions in the context of what an account normally does.
That's what this project builds.

## Results

Evaluated on a held-out, time-based test set (40,508 transactions, 509 illicit), against a
**naive rule baseline** that mimics current practice: flag anything ≥ $10,000 or inside the
classic $8,500–$9,999 structuring band.

| | Naive rule engine | XGBoost (matched recall) |
|---|---|---|
| Alerts raised | 397 | **290** |
| True positives caught | 290 | 290 |
| False positives | 107 | **0** |
| Precision | 73.1% | **100%** |

**At the same catch rate, the model eliminates all 107 false-positive alerts — a 27% reduction
in total review volume for identical detection.**

Pushed further, to 90% recall, the model catches **459 of 509** illicit transactions (vs. 290
for the rule engine — 58% more) while still generating **89.7% fewer false positives**. The
trade-off between "catch more crime" and "stop drowning analysts" mostly disappears once the
model can use behavioral context instead of one static threshold.

| Model | PR-AUC | ROC-AUC |
|---|---|---|
| Logistic regression (baseline) | 0.948 | 0.999 |
| XGBoost | **0.971** | 0.998 |

![Precision-recall curve](reports/pr_curve.png)

## Explainability

Every risk score decomposes into the features that drove it. Transaction velocity
(`sender_total_amount_24h`), payment channel, and how unusual an amount is relative to the
sender's own history dominate the model's decisions.

![SHAP summary](reports/shap_summary.png)

## How it works

```
generate_data.py  →  features.py  →  train.py  →  evaluate.py
  transactions       behavioral      baseline +    metrics, FP
  + typologies       features        XGBoost       reduction, SHAP
```

**1. Data.** A synthetic transaction dataset (202,535 transactions, 1.25% illicit — matching
real-world AML base rates) built to mirror the structure and typologies of the public
[SAML-D](https://www.kaggle.com/datasets/berkanoztas/synthetic-transaction-monitoring-dataset-aml)
dataset. Three real laundering patterns are simulated: **structuring** (deposits just under the
reporting threshold), **smurfing** (one source fanning money out to many accounts), and
**layering** (rapid hops through intermediary accounts).

**2. Features.** Behavioral, not just transactional: rolling 24-hour velocity and volume,
counterparty fan-out and fan-in, amount z-score against the sender's own history, near-threshold
flags, cross-border and high-risk-jurisdiction indicators.

**3. Models.** Logistic regression as a baseline (to prove the added complexity earns its keep),
then XGBoost with `scale_pos_weight` to handle the ~1:79 class imbalance.

**4. Evaluation.** Compared against the naive rule baseline at matched recall, scored with
precision-recall metrics, and explained with SHAP.

## Design decisions worth noting

- **No data leakage.** `amount_zscore_vs_sender_history` uses `.shift(1)` so a transaction never
  contributes to its own baseline, and all rolling windows look strictly backward — every feature
  would be computable at the moment a live transaction needs scoring.
- **Time-based split, not random.** Trained on the earliest 80% of days, tested on the most
  recent 20%. A random shuffle would leak future account behavior into training and inflate
  results relative to production performance.
- **PR-AUC over ROC-AUC.** At 1.25% positives, ROC-AUC is flattered by the model correctly
  ignoring a vast pool of obviously-normal transactions. PR-AUC reflects performance on the rare
  class that actually matters.
- **Accuracy is never reported.** Predicting "legitimate" for everything scores 98.75%.

## Running it

```bash
pip install -r requirements.txt

python src/generate_data.py   # → data/raw/transactions.csv
python src/features.py        # → data/processed/features.csv
python src/train.py           # → models/
python src/evaluate.py        # → reports/metrics.md + plots
```

To use the real SAML-D data instead, download it from Kaggle to
`data/raw/transactions.csv` with the same column names and skip step one — everything downstream
runs unchanged.

## Limitations & next steps

- Results are from **synthetic data**, where the illicit patterns are cleaner than reality. The
  pipeline and methodology are the deliverable; the exact percentages will shift on real data.
- Next: serve the model behind a FastAPI endpoint with an analyst triage dashboard, and extend to
  a graph neural network over the
  [Elliptic dataset](https://www.kaggle.com/datasets/ellipticco/elliptic-data-set) to detect
  laundering *rings* rather than individual transactions.

## Stack

Python · pandas · scikit-learn · XGBoost · SHAP · matplotlib
