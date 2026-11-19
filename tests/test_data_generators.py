import pandas as pd

from src.data.generate_alerts import generate_alerts
from src.data.generate_customers import generate_customers
from src.data.generate_transactions import generate_transactions


def test_customer_and_transaction_generators_are_deterministic():
    first = generate_customers(60, seed=17)
    second = generate_customers(60, seed=17)
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 60
    assert {"customer_id", "is_suspicious", "customer_type"}.issubset(first.columns)

    tx1 = generate_transactions(first, n_transactions=300, seed=17)
    tx2 = generate_transactions(first, n_transactions=300, seed=17)
    pd.testing.assert_frame_equal(tx1, tx2)
    assert len(tx1) >= 300
    assert {"transaction_id", "customer_id", "timestamp", "amount"}.issubset(tx1.columns)


def test_alert_generator_returns_expected_schema_and_is_seeded():
    customers = pd.DataFrame(
        {
            "customer_id": ["C1"],
            "is_suspicious": [0],
            "typology": ["none"],
        }
    )
    transactions = pd.DataFrame(
        {
            "transaction_id": [f"T{i}" for i in range(12)],
            "customer_id": ["C1"] * 12,
            "timestamp": pd.date_range("2025-01-01", periods=12, freq="h"),
            "amount": [100.0] * 12,
            "country": ["US"] * 12,
            "counterparty_id": ["CP1"] * 12,
            "direction": ["outgoing"] * 12,
        }
    )

    first = generate_alerts(transactions, customers, seed=3)
    second = generate_alerts(transactions, customers, seed=3)

    pd.testing.assert_frame_equal(first, second)
    assert len(first) > 0
    assert {"alert_id", "investigation_outcome", "is_suspicious"}.issubset(first.columns)
