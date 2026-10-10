"""Create monthly customer behavior features and synthetic behavior-change labels."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data' / 'raw'
PROCESSED = ROOT / 'data' / 'processed'
PROCESSED.mkdir(parents=True, exist_ok=True)


def generate_behavioral_patterns(customers: pd.DataFrame, transactions: pd.DataFrame, seed: int = 42):
    rng = np.random.default_rng(seed)
    tx = transactions.copy(); tx['timestamp'] = pd.to_datetime(tx['timestamp'])
    tx['month'] = tx['timestamp'].dt.to_period('M').astype(str)
    monthly = tx.groupby(['customer_id','month']).agg(
        tx_count=('transaction_id','count'),
        total_amount=('amount','sum'),
        avg_amount=('amount','mean'),
        max_amount=('amount','max'),
        unique_counterparties=('counterparty_id','nunique'),
        unique_countries=('country','nunique'),
    ).reset_index()
    months = pd.period_range(tx['timestamp'].min(), tx['timestamp'].max(), freq='M').astype(str)
    base = pd.MultiIndex.from_product([customers['customer_id'], months], names=['customer_id','month']).to_frame(index=False)
    monthly = base.merge(monthly, on=['customer_id','month'], how='left').fillna({
        'tx_count':0,'total_amount':0,'avg_amount':0,'max_amount':0,'unique_counterparties':0,'unique_countries':0
    })
    monthly['incoming_amount'] = tx[tx['direction'].eq('incoming')].groupby(['customer_id','month'])['amount'].sum().reindex(pd.MultiIndex.from_frame(base[['customer_id','month']])).fillna(0).to_numpy()
    monthly['outgoing_amount'] = tx[tx['direction'].eq('outgoing')].groupby(['customer_id','month'])['amount'].sum().reindex(pd.MultiIndex.from_frame(base[['customer_id','month']])).fillna(0).to_numpy()
    monthly = monthly.sort_values(['customer_id','month'])
    for col in ['tx_count','total_amount','avg_amount','unique_counterparties','unique_countries']:
        monthly[f'{col}_rolling_3m_avg'] = monthly.groupby('customer_id')[col].transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
    changes = []
    chosen = customers.sample(frac=0.05, random_state=seed)['customer_id'].tolist()
    for cid in chosen:
        idxs = monthly.index[monthly['customer_id'].eq(cid)].tolist()
        if len(idxs) < 6: continue
        change_pos = int(rng.integers(max(3, len(idxs)-3), len(idxs)))
        change_month = monthly.loc[idxs[change_pos], 'month']
        typ = rng.choice(['velocity_spike','amount_spike','new_counterparties','geographic_expansion','rapid_movement'])
        mask = monthly['customer_id'].eq(cid) & (monthly['month'] >= change_month)
        if typ == 'velocity_spike': monthly.loc[mask,'tx_count'] *= int(rng.integers(3,6))
        elif typ == 'amount_spike': monthly.loc[mask,['total_amount','avg_amount','max_amount']] *= float(rng.uniform(4,8))
        elif typ == 'new_counterparties': monthly.loc[mask,'unique_counterparties'] *= int(rng.integers(5,11))
        elif typ == 'geographic_expansion': monthly.loc[mask,'unique_countries'] *= int(rng.integers(3,7))
        else: monthly.loc[mask,['incoming_amount','outgoing_amount']] *= 5
        changes.append({'customer_id':cid,'change_month':change_month,'change_type':typ})
    return monthly, pd.DataFrame(changes)


if __name__ == '__main__':
    cp = RAW/'customers.csv'; tp = RAW/'transactions.csv'
    if not cp.exists() or not tp.exists(): raise FileNotFoundError('Generate customers and transactions first.')
    monthly, changes = generate_behavioral_patterns(pd.read_csv(cp), pd.read_csv(tp))
    monthly.to_csv(PROCESSED/'monthly_behavior.csv', index=False)
    changes.to_csv(PROCESSED/'behavioral_changes.csv', index=False)
    print(f'Saved {len(monthly):,} monthly behavior rows.')
    print(f'Saved {len(changes):,} behavioral changes.')
