# AML Alert Triage & False-Positive Reduction Engine

## Problem

Rules-based AML transaction monitoring at banks and fintechs generates roughly a
95% false-positive rate on alerts — most flagged transactions are legitimate.
Analysts spend hours reviewing each one, and global AML compliance spend exceeds
$274B/year, most of it chasing noise instead of catching real financial crime.

This project builds a machine-learning model that re-scores AML alerts by
predicted true risk, so analysts can focus review time on the alerts most
likely to be genuine — with an explanation attached to every score, since an
AML decision that can't be explained to a regulator is unusable.

## Status

Build in progress. See `docs/PROGRESS.md` (created as we go) for what's done.

## Project layout

```
fintech-aml-triage/
├── data/
│   ├── raw/            # generated / downloaded transaction data
│   └── processed/       # feature-engineered datasets
├── src/
│   ├── generate_data.py # synthetic AML transaction generator
│   ├── features.py      # feature engineering
│   ├── train.py         # baseline + XGBoost training
│   └── evaluate.py       # metrics, false-positive reduction analysis
├── models/               # saved trained models
├── reports/              # evaluation output (metrics, plots)
├── notebooks/             # exploration notebooks
└── requirements.txt
```

## Step 1: Data

We start from a **synthetic dataset generated locally** (`src/generate_data.py`),
built to mirror the structure and typologies of the public
[SAML-D](https://www.kaggle.com/datasets/berkanoztas/synthetic-transaction-monitoring-dataset-aml)
dataset (structuring, smurfing, layering), so you can start training immediately
without needing a Kaggle account. Swapping in the real SAML-D dataset later is a
one-line change (see the docstring in `generate_data.py`).

## Running it

```bash
pip install -r requirements.txt
python src/generate_data.py       # writes data/raw/transactions.csv
python src/features.py            # writes data/processed/features.csv
python src/train.py               # trains baseline + XGBoost, saves to models/
python src/evaluate.py            # prints/saves metrics to reports/
```
