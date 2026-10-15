from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data' / 'raw'
RAW.mkdir(parents=True, exist_ok=True)


def generate_customers(n_customers: int = 10_000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    customer_types = ['individual', 'business', 'high_net_worth', 'student', 'retired']
    type_probs = [0.60, 0.20, 0.05, 0.10, 0.05]
    countries = ['US', 'UK', 'CA', 'DE', 'FR', 'JP', 'SG', 'AE', 'BR', 'IN']
    country_probs = [0.70, 0.08, 0.06, 0.04, 0.03, 0.03, 0.02, 0.02, 0.01, 0.01]

    types = rng.choice(customer_types, n_customers, p=type_probs)
    ctry = rng.choice(countries, n_customers, p=country_probs)
    age = np.clip(rng.exponential(1000, n_customers).astype(int) + 30, 30, 7300)

    income = np.empty(n_customers)
    masks = {
        'student': types == 'student',
        'retired': types == 'retired',
        'individual': types == 'individual',
        'business': types == 'business',
        'high_net_worth': types == 'high_net_worth',
    }
    income[masks['student']] = np.maximum(500, rng.normal(1500, 500, masks['student'].sum()))
    income[masks['retired']] = np.maximum(1000, rng.normal(3500, 1500, masks['retired'].sum()))
    income[masks['individual']] = np.maximum(2000, rng.lognormal(9.0, 0.8, masks['individual'].sum()))
    income[masks['business']] = np.maximum(5000, rng.lognormal(11.0, 1.5, masks['business'].sum()))
    income[masks['high_net_worth']] = np.maximum(50_000, rng.lognormal(12.5, 0.7, masks['high_net_worth'].sum()))

    risk = np.full(n_customers, 0.30)
    risk += np.where(age < 90, 0.20, np.where(age < 180, 0.10, 0.0))
    risk += np.where(types == 'business', 0.15, 0.0)
    risk += np.where(types == 'high_net_worth', 0.10, 0.0)
    risk += np.where(np.isin(ctry, ['AE', 'BR']), 0.15, 0.0)
    risk = np.clip(risk + rng.normal(0, 0.10, n_customers), 0, 1)
    risk_profile = np.where(risk < 0.3, 'low', np.where(risk < 0.6, 'medium', 'high'))

    # Hidden ground truth used only to generate realistic alert outcomes.
    is_suspicious = rng.random(n_customers) < 0.045
    typologies = np.array(['none'] * n_customers, dtype=object)
    suspicious_types = ['structuring', 'velocity', 'rapid_movement', 'geographic', 'new_counterparties', 'circular']
    idx = np.flatnonzero(is_suspicious)
    typologies[idx] = rng.choice(suspicious_types, len(idx))

    df = pd.DataFrame({
        'customer_id': [f'C{i:05d}' for i in range(1, n_customers + 1)],
        'customer_type': types,
        'country': ctry,
        'account_age_days': age,
        'monthly_income': income.astype(int),
        'risk_profile': risk_profile,
        'monthly_tx_rate': 0,
        'is_suspicious': is_suspicious.astype(int),
        'typology': typologies,
    })
    return df


if __name__ == '__main__':
    customers = generate_customers()
    customers.to_csv(RAW / 'customers.csv', index=False)
    print(f'Saved {len(customers):,} customers -> {RAW / "customers.csv"}')
    print(customers['customer_type'].value_counts())
    print('\nGround-truth suspicious customers:', int(customers['is_suspicious'].sum()))
