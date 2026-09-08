# Evaluation Report

## Model quality (held-out, time-based test set, 40,508 transactions, 509 illicit)

| Model | PR-AUC | ROC-AUC |
|---|---|---|
| Logistic Regression (baseline) | 0.948 | 0.999 |
| XGBoost | 0.971 | 0.998 |

## Headline comparison: naive rule engine vs. XGBoost

Naive rule = flag if amount >= $10,000 OR in the classic
$8,500-$10,000 structuring band
(a stand-in for a typical threshold-based AML system).

### Scenario A -- same catch rate as the naive rule (apples-to-apples)

| | Naive rule | XGBoost (matched to 57.0% recall) |
|---|---|---|
| Alerts raised | 397 | 290 |
| True positives caught | 290 | 290 |
| False positives | 107 | 0 |
| Recall | 57.0% | 57.0% |
| Precision | 73.05% | 100.00% |
| Share of alerts that are false positives | 27.0% | 0.0% |

**At the same recall as today's rule engine, XGBoost cuts total alert volume by
27.0% and false-positive alerts by 100.0%.**
This is the number to lead with: same crimes caught, far fewer analyst-hours
burned on noise.

### Scenario B -- push recall to 90% (catch more, not just fewer false alarms)

| | Naive rule | XGBoost (>= 90% recall) |
|---|---|---|
| Alerts raised | 397 | 470 |
| True positives caught | 290 | 459 |
| False positives | 107 | 11 |
| Recall | 57.0% | 90.2% |
| Precision | 73.05% | 97.66% |

**At 90% recall (catching 459 of 509 illicit transactions vs. just 290 today),
false positives still drop 89.7% vs. the naive rule.**
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
