# AML Alert Triage Engine

Synthetic end-to-end AML alert triage pipeline.

## One-command run

From the project root:

```bash
python run_pipeline.py
```

## Individual steps

```bash
python src/data/generate_customers.py
python src/data/generate_transactions.py
python src/data/generate_alerts.py
python src/data/build_ml_dataset.py
python src/models/train_model.py
```

## Outputs

- `data/raw/customers.csv`
- `data/raw/transactions.csv`
- `data/processed/alerts.csv`
- `data/processed/ml_alert_dataset.csv`
- `models/aml_logistic_regression.joblib`
- `models/aml_random_forest.joblib`
- `models/test_predictions.csv`
- `models/metrics.json`

The hidden `is_suspicious` ground-truth field is used only to synthesize investigation outcomes and is excluded from model training to reduce target leakage.
