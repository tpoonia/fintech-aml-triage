import pandas as pd

from src.models.model_utils import grouped_train_test_indices, prepare_training_data


def test_training_features_exclude_ground_truth_and_investigation_outcome():
    data = pd.DataFrame(
        {
            "customer_id": ["C1", "C1", "C2", "C3"],
            "alert_id": ["A1", "A2", "A3", "A4"],
            "investigation_outcome": ["FILED_SAR", "DISMISSED", "FILED_SAR", "DISMISSED"],
            "is_suspicious": [1, 1, 0, 0],
            "target": [1, 0, 1, 0],
            "amount_feature": [2.0, 3.0, 4.0, 5.0],
        }
    )

    features, target, groups = prepare_training_data(data)

    assert features.columns.tolist() == ["amount_feature"]
    assert target.tolist() == [1, 0, 1, 0]
    assert groups.tolist() == ["C1", "C1", "C2", "C3"]


def test_grouped_split_never_puts_a_customer_in_both_partitions():
    groups = pd.Series(["C1", "C1", "C2", "C2", "C3", "C3", "C4", "C4"])
    train, test = grouped_train_test_indices(groups, test_size=0.25, random_state=42)

    assert set(groups.iloc[train]).isdisjoint(set(groups.iloc[test]))
