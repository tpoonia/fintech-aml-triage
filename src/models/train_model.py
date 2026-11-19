"""Train AML alert-triage baseline classifiers.

Run from the project root or any directory:
    python src/models/train_model.py
"""
from pathlib import Path
import json
import sys
import warnings
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.models.model_utils import SEED, grouped_train_test_indices, prepare_training_data
DATA = ROOT/'data'/'processed'/'ml_alert_dataset.csv'
MODELS = ROOT/'models'; MODELS.mkdir(parents=True, exist_ok=True)

def metrics(name, y, pred, prob):
    out = {'precision':precision_score(y,pred,zero_division=0),'recall':recall_score(y,pred,zero_division=0),'f1':f1_score(y,pred,zero_division=0),'roc_auc':roc_auc_score(y,prob),'pr_auc':average_precision_score(y,prob),'confusion_matrix':confusion_matrix(y,pred).tolist()}
    print(f'\n{name}\n' + '='*55)
    for k in ['precision','recall','f1','roc_auc','pr_auc']: print(f'{k.upper():10s}: {out[k]:.4f}')
    print('\nConfusion matrix:\n', confusion_matrix(y,pred))
    return {k: float(v) if isinstance(v,(np.floating,float)) else v for k,v in out.items()}

def main():
    if not DATA.exists():
        raise FileNotFoundError(f'{DATA} not found. Run: python src/data/build_ml_dataset.py')

    df = pd.read_csv(DATA)
    if set(pd.to_numeric(df['target'], errors='coerce').dropna().unique()) != {0, 1}:
        raise ValueError('Expected both target classes 0 and 1.')
    X, y, groups = prepare_training_data(df)
    cat = X.select_dtypes(include=['object','category','bool']).columns.tolist()
    num = X.select_dtypes(include=[np.number]).columns.tolist()
    pre = ColumnTransformer([
        ('num', Pipeline([('imputer',SimpleImputer(strategy='median')),('scale',StandardScaler())]), num),
        ('cat', Pipeline([('imputer',SimpleImputer(strategy='most_frequent')),('onehot',OneHotEncoder(handle_unknown='ignore'))]), cat),
    ], remainder='drop')
    train_idx, test_idx = grouped_train_test_indices(groups)
    Xtr, Xte = X.iloc[train_idx], X.iloc[test_idx]
    ytr, yte = y.iloc[train_idx], y.iloc[test_idx]
    train_customers = set(groups.iloc[train_idx])
    test_customers = set(groups.iloc[test_idx])
    if train_customers & test_customers:
        raise RuntimeError('Customer overlap detected in grouped train/test split.')
    print(f'Dataset shape: {df.shape}')
    print(f'Train: {len(Xtr):,} | Test: {len(Xte):,} | Customers: {len(train_customers):,}/{len(test_customers):,}')

    models = {
        'logistic_regression': LogisticRegression(class_weight='balanced',max_iter=2000,random_state=SEED),
        'random_forest': RandomForestClassifier(n_estimators=250,max_depth=12,min_samples_leaf=3,class_weight='balanced',random_state=SEED,n_jobs=1),
    }
    results = {}
    for name, model in models.items():
        pipe = Pipeline([('preprocessor',pre),('model',model)])
        print(f'\nTraining {name}...')
        pipe.fit(Xtr,ytr)
        pred = pipe.predict(Xte); prob = pipe.predict_proba(Xte)[:,1]
        results[name] = metrics(name,yte,pred,prob)
        joblib.dump(pipe, MODELS/f'aml_{name}.joblib')

    predictions = df.iloc[test_idx][['alert_id','customer_id']].copy()
    predictions['actual_target'] = yte.to_numpy()
    for name in models:
        pipe = joblib.load(MODELS/f'aml_{name}.joblib')
        predictions[f'{name}_probability'] = pipe.predict_proba(Xte)[:,1]
        predictions[f'{name}_prediction'] = pipe.predict(Xte)
    truth_path = ROOT/'data'/'processed'/'alerts.csv'
    if truth_path.exists():
        truth = pd.read_csv(truth_path, usecols=['alert_id','is_suspicious'])
        predictions = predictions.merge(truth, on='alert_id', how='left')
    predictions.to_csv(MODELS/'test_predictions.csv',index=False)
    report = {
        'dataset_rows': int(len(y)),
        'target_distribution': {str(k): int(v) for k,v in y.value_counts().sort_index().items()},
        'numeric_features': num,
        'categorical_features': cat,
        'excluded_from_features': sorted(['is_suspicious','investigation_outcome']),
        'split': 'GroupShuffleSplit by customer_id',
        'train_rows': int(len(train_idx)),
        'test_rows': int(len(test_idx)),
        'train_customers': len(train_customers),
        'test_customers': len(test_customers),
        'customer_overlap': len(train_customers & test_customers),
        'results': results,
    }
    with open(MODELS/'metrics.json','w') as f:
        json.dump(report,f,indent=2)
    print('\nTRAINING COMPLETE')
    print(f'Models -> {MODELS}')


if __name__ == '__main__':
    main()
