"""Train AML alert-triage baseline classifiers.

Run from the project root or any directory:
    python src/models/train_model.py
"""
from pathlib import Path
import json
import warnings
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformerpython
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT/'data'/'processed'/'ml_alert_dataset.csv'
MODELS = ROOT/'models'; MODELS.mkdir(parents=True, exist_ok=True)
DROP = ['alert_id','customer_id','transaction_id','alert_timestamp','investigation_outcome']

def metrics(name, y, pred, prob):
    out = {'precision':precision_score(y,pred,zero_division=0),'recall':recall_score(y,pred,zero_division=0),'f1':f1_score(y,pred,zero_division=0),'roc_auc':roc_auc_score(y,prob),'pr_auc':average_precision_score(y,prob),'confusion_matrix':confusion_matrix(y,pred).tolist()}
    print(f'\n{name}\n' + '='*55)
    for k in ['precision','recall','f1','roc_auc','pr_auc']: print(f'{k.upper():10s}: {out[k]:.4f}')
    print('\nConfusion matrix:\n', confusion_matrix(y,pred))
    return {k: float(v) if isinstance(v,(np.floating,float)) else v for k,v in out.items()}

if not DATA.exists():
    raise FileNotFoundError(f'{DATA} not found. Run: python src/data/build_ml_dataset.py')

df = pd.read_csv(DATA)
if 'target' not in df: raise ValueError('target column missing')
df['target'] = pd.to_numeric(df['target'], errors='coerce'); df = df.dropna(subset=['target']).copy(); df['target'] = df['target'].astype(int)
if set(df['target'].unique()) != {0,1}: raise ValueError(f'Expected both target classes 0 and 1; found {sorted(df.target.unique())}')
print(f'Dataset shape: {df.shape}')
print('\nTarget distribution:\n', df.target.value_counts().sort_index())

y = df.pop('target')
# Remove ground truth and raw identifiers to prevent leakage.
for c in ['is_suspicious']:
    if c in df: df = df.drop(columns=c)
X = df.drop(columns=[c for c in DROP if c in df], errors='ignore')
cat = X.select_dtypes(include=['object','category','bool']).columns.tolist()
num = X.select_dtypes(include=[np.number]).columns.tolist()
pre = ColumnTransformer([
    ('num', Pipeline([('imputer',SimpleImputer(strategy='median')),('scale',StandardScaler())]), num),
    ('cat', Pipeline([('imputer',SimpleImputer(strategy='most_frequent')),('onehot',OneHotEncoder(handle_unknown='ignore'))]), cat),
], remainder='drop')
Xtr,Xte,ytr,yte = train_test_split(X,y,test_size=.20,random_state=42,stratify=y)
print(f'\nTrain: {len(Xtr):,} | Test: {len(Xte):,}')

models = {
    'logistic_regression': LogisticRegression(class_weight='balanced',max_iter=2000,random_state=42),
    'random_forest': RandomForestClassifier(n_estimators=250,max_depth=12,min_samples_leaf=3,class_weight='balanced',random_state=42,n_jobs=-1),
}
results = {}
for name, model in models.items():
    pipe = Pipeline([('preprocessor',pre),('model',model)])
    print(f'\nTraining {name}...')
    pipe.fit(Xtr,ytr)
    pred = pipe.predict(Xte); prob = pipe.predict_proba(Xte)[:,1]
    results[name] = metrics(name,yte,pred,prob)
    joblib.dump(pipe, MODELS/f'aml_{name}.joblib')

preds = Xte.copy(); preds['actual_target']=yte.to_numpy()
for name, model in models.items():
    pipe = joblib.load(MODELS/f'aml_{name}.joblib'); preds[f'{name}_probability']=pipe.predict_proba(Xte)[:,1]; preds[f'{name}_prediction']=pipe.predict(Xte)
preds.to_csv(MODELS/'test_predictions.csv',index=False)
with open(MODELS/'metrics.json','w') as f: json.dump({'dataset_rows':len(y),'target_distribution':y.value_counts().sort_index().to_dict(),'numeric_features':num,'categorical_features':cat,'results':results},f,indent=2)
print('\nBASELINE TRAINING COMPLETE')
print(f'Models -> {MODELS}')
