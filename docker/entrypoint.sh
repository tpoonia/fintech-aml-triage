#!/usr/bin/env bash
set -euo pipefail

python ensure_demo_data.py

if [[ "${SERVICE:-dashboard}" == "api" ]]; then
  exec uvicorn src.api.app:app --host 0.0.0.0 --port "${PORT:-8000}"
fi

exec streamlit run src/dashboard/app.py \
  --server.address=0.0.0.0 \
  --server.port="${PORT:-8501}" \
  --server.headless=true
