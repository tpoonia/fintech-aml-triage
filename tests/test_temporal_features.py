import pandas as pd

from src.data.build_ml_dataset import add_prior_customer_features


def test_customer_aggregates_only_use_transactions_before_alert_time():
    transactions = pd.DataFrame(
        {
            "customer_id": ["C1", "C1", "C1", "C1"],
            "timestamp": pd.to_datetime(
                ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"]
            ),
            "amount": [10.0, 20.0, 50.0, 1000.0],
            "counterparty_id": ["A", "A", "B", "C"],
            "country": ["US", "US", "CA", "GB"],
            "direction": ["incoming", "outgoing", "incoming", "outgoing"],
        }
    )
    alerts = pd.DataFrame(
        {"customer_id": ["C1"], "alert_timestamp": pd.to_datetime(["2025-01-03"])}
    )

    result = add_prior_customer_features(alerts, transactions).iloc[0]

    assert result["customer_transaction_count"] == 2
    assert result["customer_total_transaction_amount"] == 30
    assert result["customer_avg_transaction_amount"] == 15
    assert round(result["customer_std_transaction_amount"], 6) == round(50**0.5, 6)
    assert result["customer_max_transaction_amount"] == 20
    assert result["customer_min_transaction_amount"] == 10
    assert result["outgoing_ratio"] == 0.5
    assert result["unique_counterparties"] == 1
    assert result["unique_countries"] == 1
