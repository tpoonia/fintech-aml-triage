from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data' / 'raw'
RAW.mkdir(parents=True, exist_ok=True)

COUNTRY_CURRENCY = {'US':'USD','UK':'GBP','CA':'CAD','DE':'EUR','FR':'EUR','JP':'JPY','SG':'SGD','AE':'AED','BR':'BRL','IN':'INR'}
TX_TYPES = ['debit_card','credit_card','ach','wire_transfer','cash_deposit','cash_withdrawal','internal_transfer','check']
TX_PROBS = [0.25,0.20,0.15,0.07,0.10,0.08,0.10,0.05]


def generate_transactions(customers: pd.DataFrame, n_transactions: int = 200_000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    c = customers.copy().reset_index(drop=True)
    rate_map = {'student':7,'retired':10,'individual':20,'business':85,'high_net_worth':17}
    base_rate = c['customer_type'].map(rate_map).to_numpy(float)
    base_rate *= np.where(rng.random(len(c)) < 0.15, 0.15, 1.0)
    c['monthly_tx_rate'] = np.maximum(0, base_rate.round().astype(int))

    # Give suspicious customers stronger transaction-generation tendencies.
    weights = base_rate.copy()
    weights *= np.where(c['is_suspicious'].to_numpy() == 1, 1.35, 1.0)
    weights = weights / weights.sum()
    customer_idx = rng.choice(len(c), size=n_transactions, p=weights)

    dates = pd.to_datetime('2025-09-14') + pd.to_timedelta(rng.integers(0, 365*24*3600, n_transactions), unit='s')
    types = rng.choice(TX_TYPES, n_transactions, p=TX_PROBS)
    direction = rng.choice(['incoming','outgoing'], n_transactions, p=[0.45,0.55])
    country = c.loc[customer_idx, 'country'].to_numpy()
    ctype = c.loc[customer_idx, 'customer_type'].to_numpy()
    income = c.loc[customer_idx, 'monthly_income'].to_numpy(float)
    suspicious = c.loc[customer_idx, 'is_suspicious'].to_numpy(int)
    typology = c.loc[customer_idx, 'typology'].to_numpy()

    base = income * rng.lognormal(-1.5, 0.9, n_transactions)
    base = np.where(ctype == 'business', income * rng.lognormal(0, 1.0, n_transactions), base)
    base = np.where(ctype == 'high_net_worth', income * rng.lognormal(-0.5, 0.9, n_transactions), base)
    mult = dict(zip(TX_TYPES, [0.005,0.008,0.05,0.15,0.04,0.03,0.10,0.06]))
    amounts = np.maximum(1.0, base * np.array([mult[x] for x in types]))

    # Inject unmistakable but synthetic typology signals into a subset of rows.
    for t, mask in [('structuring', (suspicious == 1) & (typology == 'structuring')),
                    ('velocity', (suspicious == 1) & (typology == 'velocity')),
                    ('rapid_movement', (suspicious == 1) & (typology == 'rapid_movement'))]:
        idx = np.flatnonzero(mask)
        if t == 'structuring':
            amounts[idx[: max(1, len(idx)//2)]] = rng.uniform(8500, 9999, max(1, len(idx)//2))
        elif t == 'velocity':
            amounts[idx] = rng.uniform(10, 500, len(idx))
        else:
            amounts[idx] = np.maximum(amounts[idx], income[idx] * rng.uniform(1.5, 4.0, len(idx)))

    cp_pool = np.array([f'CP{i:05d}' for i in range(1, 5001)])
    cp = rng.choice(cp_pool, n_transactions)
    # Suspicious new-counterparty/circular patterns get more varied counterparties.
    new_cp = (suspicious == 1) & np.isin(typology, ['new_counterparties','circular'])
    cp[new_cp] = rng.choice(cp_pool, new_cp.sum())

    df = pd.DataFrame({
        'transaction_id': [f'T{i:07d}' for i in range(1, n_transactions + 1)],
        'customer_id': c.loc[customer_idx, 'customer_id'].to_numpy(),
        'timestamp': dates,
        'amount': np.round(amounts, 2),
        'transaction_type': types,
        'currency': [COUNTRY_CURRENCY.get(x, 'USD') for x in country],
        'country': country,
        'counterparty_id': cp,
        'direction': direction,
    }).sort_values('timestamp').reset_index(drop=True)

    # Add a compact suspicious burst: this makes velocity/rapid movement visible to rule logic.
    suspicious_customers = c.loc[c['is_suspicious'].eq(1), 'customer_id'].to_numpy()
    extras = []
    tx_id_start = n_transactions + 1
    for cid in suspicious_customers:
        row = c[c['customer_id'].eq(cid)].iloc[0]
        typ = row['typology']
        if typ not in ['velocity','rapid_movement','structuring']:
            continue
        base_ts = pd.Timestamp('2026-08-15') + pd.to_timedelta(int(rng.integers(0, 20)), unit='D')
        if typ == 'velocity':
            for j in range(12):
                extras.append((cid, base_ts + pd.to_timedelta(j*20, unit='m'), float(rng.uniform(20,450)), 'ach', row['country'], f'CP{rng.integers(1,5000):05d}', 'outgoing'))
        elif typ == 'rapid_movement':
            amt = float(max(row['monthly_income']*2, 15000))
            extras.append((cid, base_ts, amt, 'wire_transfer', row['country'], f'CP{rng.integers(1,5000):05d}', 'incoming'))
            extras.append((cid, base_ts + pd.Timedelta(hours=2), amt*0.9, 'wire_transfer', row['country'], f'CP{rng.integers(1,5000):05d}', 'outgoing'))
        else:
            for j in range(3):
                extras.append((cid, base_ts + pd.to_timedelta(j*2, unit='h'), float(rng.uniform(8500,9999)), 'cash_deposit', row['country'], f'CP{rng.integers(1,5000):05d}', 'incoming'))
    if extras:
        ex = pd.DataFrame(extras, columns=['customer_id','timestamp','amount','transaction_type','country','counterparty_id','direction'])
        ex.insert(0, 'transaction_id', [f'T{tx_id_start+i:07d}' for i in range(len(ex))])
        ex['currency'] = ex['country'].map(COUNTRY_CURRENCY).fillna('USD')
        ex = ex[['transaction_id','customer_id','timestamp','amount','transaction_type','currency','country','counterparty_id','direction']]
        df = pd.concat([df, ex], ignore_index=True).sort_values('timestamp').reset_index(drop=True)
    return df


if __name__ == '__main__':
    customers_path = RAW / 'customers.csv'
    if not customers_path.exists():
        raise FileNotFoundError(f'Missing {customers_path}. Run generate_customers.py first.')
    customers = pd.read_csv(customers_path)
    tx = generate_transactions(customers)
    # Save updated customer rates as part of the raw dataset.
    customers[['customer_id','customer_type','country','account_age_days','monthly_income','risk_profile','monthly_tx_rate','is_suspicious','typology']].to_csv(customers_path, index=False)
    tx.to_csv(RAW / 'transactions.csv', index=False)
    print(f'Saved {len(tx):,} transactions -> {RAW / "transactions.csv"}')
