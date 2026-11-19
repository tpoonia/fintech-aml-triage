"""Build the AML alert-level ML dataset.

Run from anywhere:
    python src/data/build_ml_dataset.py

The script creates missing raw/processed prerequisites when possible and writes:
    data/processed/ml_alert_dataset.csv
"""
from pathlib import Path
import subprocess
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data' / 'raw'
PROCESSED = ROOT / 'data' / 'processed'
RAW.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)
CUSTOMERS = RAW / 'customers.csv'
TRANSACTIONS = RAW / 'transactions.csv'
ALERTS = PROCESSED / 'alerts.csv'
OUTPUT = PROCESSED / 'ml_alert_dataset.csv'


def run_script(name: str):
    path = ROOT / 'src' / 'data' / name
    if not path.exists():
        raise FileNotFoundError(f'Missing required script: {path}')
    subprocess.run([sys.executable, str(path)], cwd=str(ROOT), check=True)


def ensure_inputs():
    if not CUSTOMERS.exists():
        print('customers.csv missing -> generating customers...')
        run_script('generate_customers.py')
    if not TRANSACTIONS.exists():
        print('transactions.csv missing -> generating transactions...')
        run_script('generate_transactions.py')
    if not ALERTS.exists():
        print('alerts.csv missing -> generating alerts...')
        run_script('generate_alerts.py')


def derive_target(alerts: pd.DataFrame) -> pd.Series:
    """Map investigation outcomes to binary triage labels.

    1 = escalated/filed; 0 = dismissed/closed/legitimate.
    """
    s = alerts['investigation_outcome'].astype(str).str.strip().str.lower()
    positive = s.str.contains(r'escalat|filed|sar|suspicious|confirmed|true', regex=True)
    negative = s.str.contains(r'dismiss|legitimate|normal|closed|false', regex=True)
    target = pd.Series(np.nan, index=alerts.index, dtype='float64')
    target.loc[positive] = 1
    target.loc[negative & ~positive] = 0
    if target.isna().any():
        print('Dropping unmapped outcomes:', sorted(s[target.isna()].unique().tolist()))
    if target.notna().sum() == 0:
        raise ValueError('Could not derive target from investigation_outcome.')
    return target


def add_prior_customer_features(alerts: pd.DataFrame, transactions: pd.DataFrame) -> pd.DataFrame:
    """Attach customer aggregates using only transactions before each alert."""
    required = {"customer_id", "timestamp", "amount", "counterparty_id", "country", "direction"}
    missing = required - set(transactions.columns)
    if missing:
        raise ValueError(f"transactions are missing columns: {sorted(missing)}")

    tx = transactions.copy()
    tx["timestamp"] = pd.to_datetime(tx["timestamp"], errors="coerce")
    tx = tx.dropna(subset=["timestamp"]).sort_values(["customer_id", "timestamp"], kind="mergesort")
    groups = {}
    for customer_id, group in tx.groupby("customer_id", sort=False):
        amounts = pd.to_numeric(group["amount"], errors="coerce").fillna(0).to_numpy(float)
        timestamps = group["timestamp"].to_numpy(dtype="datetime64[ns]")

        def first_seen_positions(values):
            seen = set()
            positions = []
            for position, value in enumerate(values):
                if pd.notna(value) and value not in seen:
                    seen.add(value)
                    positions.append(position)
            return np.asarray(positions, dtype=int)

        groups[customer_id] = {
            "timestamps": timestamps,
            "amounts": amounts,
            "prefix_sum": np.cumsum(amounts),
            "prefix_sum_sq": np.cumsum(amounts * amounts),
            "prefix_min": np.minimum.accumulate(amounts),
            "prefix_max": np.maximum.accumulate(amounts),
            "counterparty_first": first_seen_positions(group["counterparty_id"].to_numpy()),
            "country_first": first_seen_positions(group["country"].to_numpy()),
            "outgoing_prefix": np.cumsum(group["direction"].eq("outgoing").to_numpy(int)),
        }

    feature_rows = []
    for customer_id, alert_time in zip(alerts["customer_id"], alerts["alert_timestamp"]):
        features = {
            "customer_transaction_count": 0,
            "customer_avg_transaction_amount": np.nan,
            "customer_std_transaction_amount": np.nan,
            "customer_max_transaction_amount": np.nan,
            "customer_min_transaction_amount": np.nan,
            "customer_total_transaction_amount": 0.0,
            "unique_counterparties": 0,
            "unique_countries": 0,
            "outgoing_ratio": np.nan,
        }
        group = groups.get(customer_id)
        if group is not None and pd.notna(alert_time):
            cutoff = np.datetime64(pd.Timestamp(alert_time), "ns")
            count = int(np.searchsorted(group["timestamps"], cutoff, side="left"))
            features["customer_transaction_count"] = count
            if count:
                total = float(group["prefix_sum"][count - 1])
                features["customer_total_transaction_amount"] = total
                features["customer_avg_transaction_amount"] = total / count
                features["customer_min_transaction_amount"] = float(group["prefix_min"][count - 1])
                features["customer_max_transaction_amount"] = float(group["prefix_max"][count - 1])
                if count > 1:
                    variance = (group["prefix_sum_sq"][count - 1] - total * total / count) / (count - 1)
                    features["customer_std_transaction_amount"] = float(np.sqrt(max(variance, 0.0)))
                features["outgoing_ratio"] = float(group["outgoing_prefix"][count - 1] / count)
            features["unique_counterparties"] = int(np.searchsorted(group["counterparty_first"], count))
            features["unique_countries"] = int(np.searchsorted(group["country_first"], count))
        feature_rows.append(features)

    features = pd.DataFrame(feature_rows, index=alerts.index)
    return pd.concat([alerts.copy(), features], axis=1)


def build_dataset():
    ensure_inputs()
    print('Loading datasets...')
    alerts = pd.read_csv(ALERTS)
    tx = pd.read_csv(TRANSACTIONS)
    customers = pd.read_csv(CUSTOMERS)
    print(f'Alerts shape: {alerts.shape}')
    print(f'Transactions shape: {tx.shape}')
    print(f'Customers shape: {customers.shape}')

    required_alert = {'alert_id','customer_id','alert_timestamp','transaction_id','transaction_amount','investigation_outcome'}
    missing = required_alert - set(alerts.columns)
    if missing:
        raise ValueError(f'alerts.csv is missing columns: {sorted(missing)}')

    tx['timestamp'] = pd.to_datetime(tx['timestamp'], errors='coerce')
    tx = tx.dropna(subset=['timestamp']).copy()
    alerts['alert_timestamp'] = pd.to_datetime(alerts['alert_timestamp'], errors='coerce')
    alerts = alerts.dropna(subset=['alert_timestamp','customer_id']).copy()
    alerts['_alert_ts'] = alerts['alert_timestamp']

    # Customer aggregates are calculated as of each alert, excluding same-time and future transactions.
    print('Building customer behavioral features...')
    alerts = add_prior_customer_features(alerts, tx)

    # Features around each alert using the alert timestamp.
    # Per-customer NumPy searchsorted keeps this fast even for large datasets.
    tx_groups = {cid: grp.sort_values('timestamp', kind='mergesort') for cid, grp in tx.groupby('customer_id', sort=False)}
    last7_counts, last7_avg, prior_avg, prior_count = [], [], [], []
    for cid, ts_value in zip(alerts['customer_id'].to_numpy(), alerts['_alert_ts'].to_numpy()):
        grp = tx_groups.get(cid)
        if grp is None or grp.empty:
            last7_counts.append(0); last7_avg.append(0.0); prior_avg.append(0.0); prior_count.append(0); continue
        t = grp['timestamp'].to_numpy(dtype='datetime64[ns]')
        amounts = grp['amount'].to_numpy(float)
        ts_np = np.datetime64(ts_value, 'ns')
        i = int(np.searchsorted(t, ts_np, side='left'))
        s7 = int(np.searchsorted(t, ts_np - np.timedelta64(7, 'D'), side='left'))
        prior_vals = amounts[:i]
        vals7 = amounts[s7:i]
        last7_counts.append(i - s7)
        last7_avg.append(float(vals7.mean()) if len(vals7) else 0.0)
        prior_avg.append(float(prior_vals.mean()) if len(prior_vals) else 0.0)
        prior_count.append(i)
    alerts['transactions_last_7_days'] = last7_counts
    alerts['avg_amount_last_7_days'] = last7_avg
    alerts['prior_transaction_count'] = prior_count
    alerts['prior_avg_transaction_amount'] = prior_avg

    # Add transaction country first, then customer profile country.
    tx_country = tx[['transaction_id','country']].drop_duplicates('transaction_id')
    alerts = alerts.merge(tx_country, on='transaction_id', how='left')

    customer_cols = ['customer_id','customer_type','country','account_age_days','monthly_income','risk_profile']
    alerts = alerts.merge(customers[customer_cols], on='customer_id', how='left', suffixes=('','_customer'))
    alerts['customer_country'] = alerts['country_customer'].fillna('UNKNOWN')
    alerts['amount_deviation_ratio'] = alerts['transaction_amount'] / alerts['prior_avg_transaction_amount'].replace(0, np.nan)
    alerts['amount_deviation_ratio'] = alerts['amount_deviation_ratio'].replace([np.inf,-np.inf], np.nan).fillna(0)
    alerts['income_ratio'] = alerts['transaction_amount'] / alerts['monthly_income'].replace(0, np.nan)
    alerts['income_ratio'] = alerts['income_ratio'].replace([np.inf,-np.inf], np.nan).fillna(0)
    alerts['is_cross_border'] = (alerts['country'].fillna('UNKNOWN') != alerts['customer_country']).astype(int)
    alerts.drop(columns=['_alert_ts','country_customer'], errors='ignore', inplace=True)

    target = derive_target(alerts)
    alerts['target'] = target
    alerts = alerts.dropna(subset=['target']).copy()
    alerts['target'] = alerts['target'].astype(int)

    # Keep a clear alert-level feature set. Ground truth is deliberately excluded.
    keep = [
        'alert_id','customer_id','alert_timestamp','alert_type','triggered_rule','transaction_id',
        'transaction_amount','investigation_outcome',
        'customer_transaction_count','customer_avg_transaction_amount','customer_std_transaction_amount',
        'customer_max_transaction_amount','customer_min_transaction_amount','customer_total_transaction_amount',
        'unique_counterparties','unique_countries','outgoing_ratio','transactions_last_7_days',
        'avg_amount_last_7_days','prior_transaction_count','prior_avg_transaction_amount',
        'customer_type','customer_country','account_age_days','monthly_income','risk_profile',
        'income_ratio','amount_deviation_ratio','is_cross_border','target'
    ]
    for col in keep:
        if col not in alerts.columns:
            alerts[col] = 0 if col in ['is_cross_border'] else np.nan
    dataset = alerts[keep].copy()

    # Clean numeric values.
    numeric = dataset.select_dtypes(include=[np.number]).columns
    dataset[numeric] = dataset[numeric].replace([np.inf,-np.inf], np.nan)

    print('\nTarget distribution:')
    print(dataset['target'].value_counts().sort_index())
    print('\nTarget percentage:')
    print((dataset['target'].value_counts(normalize=True).sort_index() * 100).round(2))
    print('\nMissing values:')
    print(dataset.isna().sum().to_string())
    print('\nFinal columns:', dataset.columns.tolist())
    print('Final shape:', dataset.shape)

    if dataset['target'].nunique() < 2:
        raise ValueError('Target contains only one class. Alert generation/label mapping must be fixed before training.')

    dataset.to_csv(OUTPUT, index=False)
    print(f'\nSaved to: {OUTPUT}')
    return dataset


if __name__ == '__main__':
    build_dataset()
