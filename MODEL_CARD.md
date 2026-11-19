# Model card: AML Alert Triage Engine

## Intended use

Demonstrate how a synthetic AML alert queue can be organized for human review. Risk scores, priorities, and explanations support triage only. They do not establish suspicious conduct, guilt, or a filing decision.

## Data

The pipeline generates synthetic customer profiles, transactions, rule-based alerts, and investigation outcomes. No real customer or transaction records are used. The seeded full run contains 10,000 customers, 200,000 base transactions, and 155,927 alerts.

## Models and features

The pipeline trains Logistic Regression and Random Forest classifiers. Input features describe the triggering transaction, customer profile, and prior activity. Customer aggregates use only transactions strictly earlier than the alert timestamp. `investigation_outcome` determines the synthetic training target and `is_suspicious` is reserved for generation and evaluation; neither enters the feature matrix. Training and test groups are disjoint by customer.

## Evaluation

Results below are from one seeded customer-grouped holdout after removing full-history aggregate leakage.

| Model | PR-AUC | ROC-AUC |
|---|---:|---:|
| Logistic Regression | 0.271 | 0.589 |
| Random Forest | 0.325 | 0.620 |

For the Random Forest score tiers, the held-out P1/P2/P3/P4 precision was 100.0% / 56.0% / 3.0% / 0.0%, and recall was 13.7% / 50.1% / 36.2% / 0.0%. Counts were 326 / 2,134 / 29,021 / 5 alerts. Precision is the fraction of alerts in a tier with synthetic `is_suspicious=1`; recall is the fraction of all truly suspicious held-out alerts in that tier.

The calibrated thresholds are 73 for P1, 47 for P2, and 25 for P3. On the full 155,927-alert queue, tier distribution was P1 1.16%, P2 6.31%, P3 92.49%, P4 0.03%.

## Limitations

- Synthetic generation patterns are simplified and may not resemble real financial behavior or current typologies.
- Metrics are seed-specific, depend on synthetic labels, and do not predict deployment performance.
- The held-out P4 sample is very small; its precision estimate is not informative.
- SHAP is a description of model contributions, not a causal explanation.
- No calibration, fairness, privacy, regulatory, or operational validation is claimed.

## Ethical and operational notes

Use the queue to help allocate investigator attention. A person must review the underlying evidence, context, and applicable procedures. Do not take adverse action or make a filing decision from a score alone. Keep synthetic ground-truth fields out of model features and investigator-facing queue outputs.
