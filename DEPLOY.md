# Deployment preparation

This project is prepared for a demo deployment only; nothing here deploys or publishes it. All generated data and model binaries are created at runtime and remain outside Git.

## One-command demo data setup

From a fresh clone with Python 3.12 and the requirements installed:

```bash
python ensure_demo_data.py
```

The command exits without work when the configured queue already exists. Otherwise it runs the seeded demo pipeline and creates the dashboard/API queue. The dashboard also builds the demo queue automatically on first launch, once per server process, behind a progress screen. Set `AML_AUTO_BUILD_DEMO=0` to show a manual **Generate demo dataset** button instead.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `AML_ALERTS_DATA_PATH` | `data/processed/aml_prioritized_alerts.csv` | Queue file for the API and dashboard; `.parquet` is supported |
| `AML_CORS_ORIGINS` | `http://localhost:8501` | Comma-separated API origins allowed by CORS |
| `AML_AUTO_BUILD_DEMO` | `1` | Dashboard builds the demo queue automatically when it is missing |
| `AML_SHAP_MAX_ROWS` | `5000` (`1500` with `--demo`) | Maximum rows receiving local SHAP values; top-risk rows are included with a seeded sample |
| `AML_N_CUSTOMERS` | `10000` | Generator size when stages are run directly |
| `AML_N_TRANSACTIONS` | `200000` | Number of base transactions when stages are run directly |
| `AML_SEED` | `42` | Random seed shared by generators, split, and model training |
| `AML_QUEUE_FORMAT` | `csv` | `csv`, `trimmed-csv`, or `parquet` for the prioritization stage |
| `SERVICE` | `dashboard` | Docker service command: `dashboard` or `api` |
| `PORT` | `8501` dashboard / `8000` API | Listening port supplied by the hosting service |

Set `AML_ALERTS_DATA_PATH` in both services when using Parquet or a custom queue location. The dashboard and API should point at the same artifact.

## Docker Compose

Docker Compose builds one small demo dataset in a setup service, then starts the API and dashboard with the generated data and model artifacts on shared named volumes:

```bash
docker compose up --build
```

Open `http://localhost:8501` for Streamlit and `http://localhost:8000/docs` for the API. `docker compose down` stops services while preserving the demo volumes. Use `docker compose down -v` to remove them and regenerate on the next start.

## Streamlit Community Cloud

1. Connect the repository and select `src/dashboard/app.py` as the app entry point.
2. Use Python 3.12 and install from `requirements.txt`.
3. Leave `AML_ALERTS_DATA_PATH` unset for the default CSV location, or set it to the location of a mounted queue.
4. On first launch the app builds the demo data itself (about 50 seconds). Streamlit Community Cloud's file system is ephemeral, so this repeats after each restart or redeploy.
5. Keep `.streamlit/config.toml` in the repository: `enableStaticServing = true` serves the vendored three.js and GSAP files the 3D views load.

Streamlit Community Cloud hosts the dashboard; it does not expose the FastAPI service. If the API is needed, host it separately and set `AML_CORS_ORIGINS` to the dashboard origin.

## Render or Railway

Create two services from this Dockerfile and repository:

- Dashboard: set `SERVICE=dashboard`; use the provider's `PORT` environment variable.
- API: set `SERVICE=api`; use the provider's `PORT` and set `AML_CORS_ORIGINS` to the dashboard URL.
- Set `AML_ALERTS_DATA_PATH` to the same queue location in both services. If the platform does not share files between services, each service can deterministically generate the same demo data at startup. For persistent shared data, attach a shared disk or use the Docker Compose volume pattern.

Each container runs `ensure_demo_data.py` before starting its service. The API endpoint is `/docs`; the dashboard listens on the port provided by the host.

## Free-tier resource check

The measured demo contains 1,500 customers and 23,367 alerts. It completed the full generation, training, scoring, SHAP (bounded to 1,500 rows), and queue pipeline in about 48 seconds with a measured peak child-process RSS of 326 MB. The 155,927-alert full run completed in 138.75 seconds with a measured peak RSS of 753.8 MB. The full-run SHAP bottleneck is bounded to 5,000 local explanations by default; remaining alerts retain behavioral context and the global SHAP importance artifact. Both measured runs fit below a roughly 1 GB RAM budget on this environment; verify provider-specific limits after selecting a host.
