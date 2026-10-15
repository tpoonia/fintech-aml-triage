from pathlib import Path
import subprocess, sys
ROOT = Path(__file__).resolve().parent
steps = [
    'src/data/generate_customers.py',
    'src/data/generate_transactions.py',
    'src/data/generate_alerts.py',
    'src/data/build_ml_dataset.py',
    'src/models/train_model.py',
    'src/scoring/risk_scoring.py',
    'src/explainability/explain_alerts.py',
    'src/prioritization/prioritize_alerts.py',
]
for step in steps:
    print('\n' + '='*70 + f'\nRUNNING {step}\n' + '='*70)
    subprocess.run([sys.executable, str(ROOT/step)], cwd=ROOT, check=True)
print('\nALL PIPELINE STEPS COMPLETED SUCCESSFULLY.')
