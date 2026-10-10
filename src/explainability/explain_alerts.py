"""
Stage 3 - Explainable AML Alert Triage

Purpose:
    Add human-readable explanations to the scored AML alerts and, when SHAP
    is installed, calculate local SHAP explanations for the Random Forest.

Run from the project root:
    python src/explainability/explain_alerts.py

Inputs:
    data/processed/aml_risk_scored_alerts.csv
    models/aml_random_forest.joblib

Outputs:
    data/processed/aml_explained_alerts.csv
    models/xai_feature_importance.csv
"""

from pathlib import Path
import json
import warnings

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCORED_PATH = PROJECT_ROOT / "data" / "processed" / "aml_risk_scored_alerts.csv"
MODEL_PATH = PROJECT_ROOT / "models" / "aml_random_forest.joblib"

OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "aml_explained_alerts.csv"
IMPORTANCE_PATH = PROJECT_ROOT / "models" / "xai_feature_importance.csv"


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

TARGET_COLUMN = "target"

# These are columns that identify the alert/customer or are descriptive
# rather than model features.
NON_FEATURE_COLUMNS = {
    "alert_id",
    "customer_id",
    "alert_timestamp",
    "alert_type",
    "triggered_rule",
    "transaction_id",
    "investigation_outcome",
    "risk_level",
    "priority",
    "priority_order",
    "risk_score",
    "ml_probability",
    "behavioral_risk",
    "risk_reasons",
    TARGET_COLUMN,
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def find_feature_columns(df: pd.DataFrame, model) -> list[str]:
    """Return the columns expected by the trained model."""

    if hasattr(model, "feature_names_in_"):
        expected = list(model.feature_names_in_)
        missing = [c for c in expected if c not in df.columns]

        if missing:
            raise ValueError(
                "The scored dataset is missing model features: "
                + ", ".join(missing)
            )

        return expected

    # Fallback for models trained without feature_names_in_.
    candidates = [
        c for c in df.columns
        if c not in NON_FEATURE_COLUMNS
        and pd.api.types.is_numeric_dtype(df[c])
    ]

    if not candidates:
        raise ValueError("Could not determine model feature columns.")

    return candidates


def safe_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Convert model features to numeric values safely."""

    X = df[columns].copy()

    for col in columns:
        X[col] = pd.to_numeric(X[col], errors="coerce")

    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(0)

    return X


def percentile_thresholds(series: pd.Series) -> tuple[float, float]:
    """Return robust low/high thresholds."""

    values = pd.to_numeric(series, errors="coerce").dropna()

    if values.empty:
        return 0.0, 0.0

    return (
        float(values.quantile(0.90)),
        float(values.quantile(0.99)),
    )


def add_behavioral_reasons(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create concise investigator-friendly reasons using the behavioral
    features already present in the scored dataset.
    """

    result = []

    amount_high, amount_very_high = percentile_thresholds(
        df["amount_deviation_ratio"]
        if "amount_deviation_ratio" in df.columns
        else pd.Series(dtype=float)
    )

    velocity_high, velocity_very_high = percentile_thresholds(
        df["transactions_last_7_days"]
        if "transactions_last_7_days" in df.columns
        else pd.Series(dtype=float)
    )

    counterparties_high, counterparties_very_high = percentile_thresholds(
        df["unique_counterparties"]
        if "unique_counterparties" in df.columns
        else pd.Series(dtype=float)
    )

    countries_high, countries_very_high = percentile_thresholds(
        df["unique_countries"]
        if "unique_countries" in df.columns
        else pd.Series(dtype=float)
    )

    for _, row in df.iterrows():
        reasons = []

        # Amount deviation
        if "amount_deviation_ratio" in row.index:
            value = pd.to_numeric(
                row["amount_deviation_ratio"], errors="coerce"
            )
            if pd.notna(value):
                if value >= amount_very_high and amount_very_high > 0:
                    reasons.append(
                        "transaction amount is extremely high relative to "
                        "the customer's historical behavior"
                    )
                elif value >= amount_high and amount_high > 0:
                    reasons.append(
                        "transaction amount is unusually high relative to "
                        "the customer's historical behavior"
                    )

        # Velocity
        if "transactions_last_7_days" in row.index:
            value = pd.to_numeric(
                row["transactions_last_7_days"], errors="coerce"
            )
            if pd.notna(value):
                if value >= velocity_very_high and velocity_very_high > 0:
                    reasons.append(
                        "very high transaction velocity detected in the "
                        "last 7 days"
                    )
                elif value >= velocity_high and velocity_high > 0:
                    reasons.append(
                        "elevated transaction velocity detected in the "
                        "last 7 days"
                    )

        # Counterparties
        if "unique_counterparties" in row.index:
            value = pd.to_numeric(
                row["unique_counterparties"], errors="coerce"
            )
            if pd.notna(value):
                if value >= counterparties_very_high and counterparties_very_high > 0:
                    reasons.append(
                        "activity involves an unusually large number of "
                        "unique counterparties"
                    )
                elif value >= counterparties_high and counterparties_high > 0:
                    reasons.append(
                        "activity involves an elevated number of unique "
                        "counterparties"
                    )

        # Countries
        if "unique_countries" in row.index:
            value = pd.to_numeric(
                row["unique_countries"], errors="coerce"
            )
            if pd.notna(value):
                if value >= countries_very_high and countries_very_high > 0:
                    reasons.append(
                        "activity spans an unusually large number of countries"
                    )
                elif value >= countries_high and countries_high > 0:
                    reasons.append(
                        "activity spans multiple countries"
                    )

        # Cross-border
        if "is_cross_border" in row.index:
            try:
                if int(float(row["is_cross_border"])) == 1:
                    reasons.append("cross-border transaction detected")
            except (TypeError, ValueError):
                pass

        # Outgoing ratio
        if "outgoing_ratio" in row.index:
            value = pd.to_numeric(row["outgoing_ratio"], errors="coerce")
            if pd.notna(value) and value >= 0.90:
                reasons.append(
                    "high proportion of the customer's transaction activity "
                    "is outgoing"
                )

        # ML probability
        if "ml_probability" in row.index:
            value = pd.to_numeric(row["ml_probability"], errors="coerce")
            if pd.notna(value):
                if value >= 0.80:
                    reasons.append(
                        "ML model assigns a high suspicious-activity probability"
                    )
                elif value >= 0.60:
                    reasons.append(
                        "ML model assigns an elevated suspicious-activity probability"
                    )

        if not reasons:
            reasons.append(
                "no single dominant behavioral signal; risk is driven by "
                "the combined feature pattern"
            )

        result.append("; ".join(reasons[:6]))

    df["behavioral_explanation"] = result
    return df


def unwrap_tree_model(model):
    """
    Extract the actual tree-based estimator from an sklearn Pipeline.

    SHAP TreeExplainer cannot explain the Pipeline object itself. It needs
    the underlying RandomForest/XGBoost-style tree estimator.
    """
    from sklearn.pipeline import Pipeline

    if isinstance(model, Pipeline):
        if not model.steps:
            raise ValueError("The saved sklearn Pipeline contains no steps.")

        estimator = model.steps[-1][1]
        preprocessor = model[:-1] if len(model.steps) > 1 else None
        return estimator, preprocessor

    return model, None


def transform_for_shap(
    X: pd.DataFrame,
    preprocessor,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Apply any preprocessing stored before the tree estimator.

    Returns the exact feature matrix seen by the tree model and matching
    feature names.
    """
    if preprocessor is None:
        return X.copy(), list(X.columns)

    print("Applying saved model preprocessing for SHAP...")

    try:
        transformed = preprocessor.transform(X)
    except Exception as exc:
        raise ValueError(
            "The saved model contains preprocessing that could not transform "
            "the current feature dataframe. This usually means the training "
            "feature columns do not match the scored dataset."
        ) from exc

    # Some sklearn preprocessors return sparse matrices. SHAP's tree
    # explainer is safest with a dense numeric matrix.
    if hasattr(transformed, "toarray"):
        transformed = transformed.toarray()

    # Recover transformed feature names when sklearn provides them.
    try:
        feature_names = list(preprocessor.get_feature_names_out())
    except Exception:
        feature_names = [f"feature_{i}" for i in range(transformed.shape[1])]

    if transformed.shape[1] != len(feature_names):
        feature_names = [f"feature_{i}" for i in range(transformed.shape[1])]

    transformed_df = pd.DataFrame(
        transformed,
        index=X.index,
        columns=feature_names,
    )

    return transformed_df, feature_names


def _normalize_shap_values(shap_values) -> np.ndarray:
    """
    Normalize SHAP outputs across SHAP versions into:
        rows x features

    For binary classification, the suspicious/positive class is selected.
    """
    if hasattr(shap_values, "values"):
        shap_values = shap_values.values

    if isinstance(shap_values, list):
        # Older SHAP versions commonly return one array per class.
        if len(shap_values) == 0:
            raise ValueError("SHAP returned an empty list.")

        values = np.asarray(shap_values[-1])
    else:
        values = np.asarray(shap_values)

    # Newer SHAP versions may return:
    # rows x features x classes
    if values.ndim == 3:
        values = values[:, :, -1]

    if values.ndim != 2:
        raise ValueError(
            f"Unexpected SHAP output shape: {values.shape}. "
            "Expected rows x features."
        )

    return values


def shap_explanations(
    df: pd.DataFrame,
    model,
    X: pd.DataFrame,
) -> tuple[pd.Series, pd.Series]:
    """
    Calculate local SHAP explanations for the actual tree estimator.

    If the saved model is an sklearn Pipeline, the preprocessing steps are
    applied first and TreeExplainer receives only the final tree estimator.

    Returns:
        shap_reason: human-readable top positive contributors
        importance: global mean absolute SHAP importance
    """

    try:
        import shap
    except ImportError as exc:
        raise ImportError(
            "\nSHAP is not installed in this Python environment.\n"
            "Install it with:\n\n"
            "    pip install shap\n\n"
            "Then run this script again."
        ) from exc

    print("Calculating SHAP explanations...")

    tree_model, preprocessor = unwrap_tree_model(model)

    print(f"SHAP model type: {type(tree_model).__name__}")

    # TreeExplainer is intended for tree-based estimators.
    supported_tree_names = {
        "DecisionTreeClassifier",
        "DecisionTreeRegressor",
        "RandomForestClassifier",
        "RandomForestRegressor",
        "ExtraTreesClassifier",
        "ExtraTreesRegressor",
        "GradientBoostingClassifier",
        "GradientBoostingRegressor",
        "HistGradientBoostingClassifier",
        "HistGradientBoostingRegressor",
        "XGBClassifier",
        "XGBRegressor",
        "LGBMClassifier",
        "LGBMRegressor",
        "CatBoostClassifier",
        "CatBoostRegressor",
    }

    model_name = type(tree_model).__name__

    if model_name not in supported_tree_names:
        raise TypeError(
            f"TreeExplainer received unsupported estimator type: "
            f"{model_name}. The saved model must end with a tree-based "
            "classifier/regressor."
        )

    shap_X, shap_feature_names = transform_for_shap(X, preprocessor)

    print(f"SHAP feature matrix shape: {shap_X.shape}")

    explainer = shap.TreeExplainer(tree_model)

    # Calculate in batches so a large AML dataset does not require the
    # complete SHAP tensor to remain in memory at once.
    batch_size = 5000
    value_batches = []

    total_rows = len(shap_X)

    for start in range(0, total_rows, batch_size):
        end = min(start + batch_size, total_rows)

        print(
            f"  SHAP rows {start + 1:,}-{end:,} "
            f"of {total_rows:,}"
        )

        batch = shap_X.iloc[start:end]
        batch_values = explainer.shap_values(batch)
        value_batches.append(_normalize_shap_values(batch_values))

    values = np.vstack(value_batches)

    if values.shape[1] != len(shap_feature_names):
        raise ValueError(
            "SHAP feature count does not match transformed model feature count: "
            f"{values.shape[1]} vs {len(shap_feature_names)}."
        )

    # Global feature importance.
    mean_abs = np.abs(values).mean(axis=0)

    importance = pd.DataFrame(
        {
            "feature": shap_feature_names,
            "mean_abs_shap": mean_abs,
        }
    ).sort_values(
        "mean_abs_shap",
        ascending=False,
    ).reset_index(drop=True)

    # Top positive contributors for each alert.
    explanations = []

    for i in range(values.shape[0]):
        row_values = values[i]

        positive_indices = np.where(row_values > 0)[0]

        if len(positive_indices) == 0:
            selected = np.argsort(np.abs(row_values))[-3:][::-1]
        else:
            selected = positive_indices[
                np.argsort(row_values[positive_indices])[-3:][::-1]
            ]

        parts = []

        for idx in selected:
            feature = shap_feature_names[idx]
            contribution = row_values[idx]
            value = shap_X.iloc[i, idx]

            if isinstance(value, (float, np.floating)):
                value_text = f"{value:.3g}"
            else:
                value_text = str(value)

            parts.append(
                f"{feature}={value_text} "
                f"(SHAP {contribution:+.3f})"
            )

        explanations.append("; ".join(parts))

    return (
        pd.Series(explanations, index=df.index),
        importance,
    )


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    print("=" * 70)
    print("STAGE 3 - EXPLAINABLE AML ALERT TRIAGE")
    print("=" * 70)

    if not SCORED_PATH.exists():
        raise FileNotFoundError(
            f"\nScored dataset not found:\n{SCORED_PATH}\n\n"
            "Run Stage 2 risk scoring first."
        )

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"\nRandom Forest model not found:\n{MODEL_PATH}\n\n"
            "Run train_model.py first."
        )

    print("\nLoading scored alerts...")
    df = pd.read_csv(SCORED_PATH)

    print(f"Scored dataset shape: {df.shape}")

    print("\nLoading trained Random Forest...")
    model = joblib.load(MODEL_PATH)

    feature_columns = find_feature_columns(df, model)

    print(f"\nModel features: {len(feature_columns)}")
    print(feature_columns)

    X = safe_numeric(df, feature_columns)

    # Add rule-based explanations first.
    print("\nBuilding behavioral explanations...")
    df = add_behavioral_reasons(df)

    # SHAP explanation.
    shap_reason, importance = shap_explanations(
        df,
        model,
        X,
    )

    df["shap_top_features"] = shap_reason

    # Combine the two explanation layers.
    df["explanation"] = (
        df["behavioral_explanation"]
        + " | Top ML contributors: "
        + df["shap_top_features"]
    )

    # Save global feature importance.
    IMPORTANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    importance.to_csv(IMPORTANCE_PATH, index=False)

    # Put important investigation columns first.
    preferred = [
        "alert_id",
        "customer_id",
        "alert_timestamp",
        "alert_type",
        "triggered_rule",
        "transaction_id",
        "transaction_amount",
        "risk_score",
        "risk_level",
        "priority",
        "ml_probability",
        "behavioral_risk",
        "behavioral_explanation",
        "shap_top_features",
        "explanation",
        "target",
    ]

    ordered = [c for c in preferred if c in df.columns]
    remaining = [c for c in df.columns if c not in ordered]

    df = df[ordered + remaining]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    # Console summary.
    print("\n" + "=" * 70)
    print("XAI COMPLETE")
    print("=" * 70)

    print(f"\nExplained alerts: {len(df):,}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Feature importance: {IMPORTANCE_PATH}")

    print("\nTop model features by mean absolute SHAP:")
    print(importance.head(10).to_string(index=False))

    print("\nExample explanation:")
    example_columns = [
        c for c in [
            "alert_id",
            "risk_score",
            "risk_level",
            "priority",
            "explanation",
        ]
        if c in df.columns
    ]

    if len(df) > 0:
        print(df.iloc[0][example_columns].to_string())

    summary = {
        "stage": "explainable_ai",
        "alerts_explained": int(len(df)),
        "feature_count": int(len(feature_columns)),
        "output_file": str(OUTPUT_PATH),
        "feature_importance_file": str(IMPORTANCE_PATH),
    }

    summary_path = PROJECT_ROOT / "models" / "xai_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nXAI summary: {summary_path}")
    print("\nStage 3 finished successfully.")


if __name__ == "__main__":
    main()
