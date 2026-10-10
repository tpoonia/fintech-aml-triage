from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data' / 'raw'
PROCESSED = ROOT / 'data' / 'processed'
PROCESSED.mkdir(parents=True, exist_ok=True)


def generate_alerts(transactions: pd.DataFrame, customers: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic rule-based AML alerts efficiently.

    The implementation uses NumPy arrays and per-customer state instead of
    repeatedly filtering a pandas DataFrame for every transaction.
    """
    rng = np.random.default_rng(seed)
    tx = transactions.copy()
    tx['timestamp'] = pd.to_datetime(tx['timestamp'], errors='coerce')
    tx = tx.dropna(subset=['timestamp']).sort_values(['customer_id','timestamp']).reset_index(drop=True)
    c = customers.set_index('customer_id')
    alerts = []
    aid = 1

    for cid, g in tx.groupby('customer_id', sort=False):
        if cid not in c.index:
            continue
        cust = c.loc[cid]
        ts = g['timestamp'].to_numpy(dtype='datetime64[ns]')
        amounts = g['amount'].to_numpy(float)
        countries = g['country'].to_numpy(object)
        cps = g['counterparty_id'].to_numpy(object)
        directions = g['direction'].to_numpy(object)
        tx_ids = g['transaction_id'].to_numpy(object)
        suspicious = int(cust.get('is_suspicious', 0))
        typology = str(cust.get('typology', 'none'))

        seen_countries = set()
        seen_cps = set()
        incoming_times = []
        incoming_amounts = []

        for i in range(len(g)):
            current = pd.Timestamp(ts[i])
            cutoff24 = ts[i] - np.timedelta64(24, 'h')
            cutoff30 = ts[i] - np.timedelta64(30, 'D')
            start24 = int(np.searchsorted(ts, cutoff24, side='left'))
            start30 = int(np.searchsorted(ts, cutoff30, side='left'))
            # Exclude current row from history.
            hist_start30 = start30
            hist_end = i
            reasons = []

            if i - start24 >= 10:
                reasons.append('HIGH_VELOCITY')
            if hist_end - hist_start30 >= 5:
                prior_mean = float(np.mean(amounts[hist_start30:hist_end]))
                if amounts[i] > max(1000.0, prior_mean * 5.0):
                    reasons.append('UNUSUAL_AMOUNT')
            if countries[i] not in seen_countries and len(seen_countries) >= 3:
                reasons.append('NEW_COUNTRY')
            if cps[i] not in seen_cps and len(seen_cps) >= 5:
                reasons.append('NEW_COUNTERPARTY')

            if directions[i] == 'outgoing' and amounts[i] > 10000 and incoming_times:
                cutoff = current - pd.Timedelta(hours=24)
                rapid = any(t >= cutoff and a > 10000 for t, a in zip(incoming_times, incoming_amounts))
                if rapid:
                    reasons.append('RAPID_FUND_MOVEMENT')

            if reasons:
                aligned = (
                    (typology == 'velocity' and 'HIGH_VELOCITY' in reasons) or
                    (typology == 'structuring' and 'UNUSUAL_AMOUNT' in reasons) or
                    (typology == 'geographic' and 'NEW_COUNTRY' in reasons) or
                    (typology == 'new_counterparties' and 'NEW_COUNTERPARTY' in reasons) or
                    (typology == 'rapid_movement' and 'RAPID_FUND_MOVEMENT' in reasons) or
                    (typology == 'circular' and len(reasons) >= 2)
                )
                if suspicious and aligned:
                    outcome = str(rng.choice(['ESCALATED_TO_TIER2','FILED_SAR'], p=[0.30,0.70]))
                elif suspicious:
                    outcome = str(rng.choice(['DISMISSED','ESCALATED_TO_TIER2'], p=[0.35,0.65]))
                else:
                    outcome = str(rng.choice(['DISMISSED','ESCALATED_TO_TIER2'], p=[0.90,0.10]))
                alerts.append({
                    'alert_id': f'A{aid:06d}', 'customer_id': cid, 'alert_timestamp': current,
                    'alert_type': '+'.join(reasons), 'triggered_rule': '|'.join(reasons),
                    'transaction_id': tx_ids[i], 'transaction_amount': float(amounts[i]),
                    'investigation_outcome': outcome, 'is_suspicious': suspicious,
                })
                aid += 1

            seen_countries.add(countries[i]); seen_cps.add(cps[i])
            if directions[i] == 'incoming':
                incoming_times.append(current); incoming_amounts.append(float(amounts[i]))
                # Keep state bounded.
                cutoff = current - pd.Timedelta(days=2)
                keep = [j for j, t in enumerate(incoming_times) if t >= cutoff]
                incoming_times = [incoming_times[j] for j in keep]
                incoming_amounts = [incoming_amounts[j] for j in keep]

    out = pd.DataFrame(alerts)
    if out.empty:
        raise RuntimeError('No alerts were generated. Check transaction data and rule thresholds.')
    return out


if __name__ == '__main__':
    cp = RAW / 'customers.csv'; tp = RAW / 'transactions.csv'
    if not cp.exists() or not tp.exists():
        raise FileNotFoundError('Run generate_customers.py and generate_transactions.py first.')
    customers = pd.read_csv(cp); transactions = pd.read_csv(tp)
    alerts = generate_alerts(transactions, customers)
    alerts.to_csv(PROCESSED / 'alerts.csv', index=False)
    print(f'Saved {len(alerts):,} alerts -> {PROCESSED / "alerts.csv"}')
    print('\nInvestigation outcomes:')
    print(alerts['investigation_outcome'].value_counts())
    print('\nGround-truth suspicious flag:')
    print(alerts['is_suspicious'].value_counts())
