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
    alerts['alert_timestamp'] = pd.to_datetime(alerts['alert_timestamp'], errors='coerce')
    alerts = alerts.dropna(subset=['alert_timestamp','customer_id']).copy()
    alerts['_alert_ts'] = alerts['alert_timestamp']

    # Transaction-level aggregates by customer: fast vectorized groupby, no row-wise DataFrame filtering.
    print('Building customer behavioral features...')
    g = tx.groupby('customer_id', sort=False)
    agg = g['amount'].agg(
        customer_transaction_count='count',
        customer_avg_transaction_amount='mean',
        customer_std_transaction_amount='std',
        customer_max_transaction_amount='max',
        customer_min_transaction_amount='min',
        customer_total_transaction_amount='sum',
    ).reset_index()
    cp = g['counterparty_id'].nunique().rename('unique_counterparties').reset_index()
    countries = g['country'].nunique().rename('unique_countries').reset_index()
    outgoing = tx.assign(_out=(tx['direction'].eq('outgoing')).astype(int)).groupby('customer_id')['_out'].mean().rename('outgoing_ratio').reset_index()
    last_date = tx.groupby('customer_id')['timestamp'].max().rename('last_transaction_timestamp').reset_index()

    behavior = agg.merge(cp, on='customer_id', how='left').merge(countries, on='customer_id', how='left').merge(outgoing, on='customer_id', how='left').merge(last_date, on='customer_id', how='left')
    alerts = alerts.merge(behavior, on='customer_id', how='left')

    # Features around each alert using the alert timestamp.
    # Per-customer NumPy searchsorted keeps this fast even for large datasets.
    tx_groups = {cid: grp.sort_values('timestamp') for cid, grp in tx.groupby('customer_id', sort=False)}
    last7_counts, last7_avg, prior_avg, prior_count = [], [], [], []
    for cid, ts_value in zip(alerts['customer_id'].to_numpy(), alerts['_alert_ts'].to_numpy()):
        grp = tx_groups.get(cid)
        if grp is None or grp.empty:
            last7_counts.append(0); last7_avg.append(0.0); prior_avg.append(0.0); prior_count.append(0); continue
        t = grp['timestamp'].to_numpy(dtype='datetime64[ns]')
        amounts = grp['amount'].to_numpy(float)
        ts_np = np.datetime64(ts_value, 'ns')
        i = int(np.searchsorted(t, ts_np, side='right'))
        s7 = int(np.searchsorted(t, ts_np - np.timedelta64(7, 'D'), side='left'))
        prior_vals = amounts[:i]
        vals7 = amounts[s7:i]
        last7_counts.append(i - s7)
        last7_avg.append(float(vals7.mean()) if len(vals7) else 0.0)
        prior_avg.append(float(prior_vals.mean()) if len(prior_vals) else float(amounts.mean()))
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
