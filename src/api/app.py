"""Cached investigator API for the synthetic AML triage queue."""

from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import sys
from datetime import datetime
from typing import Any, Literal

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.triage_config import LEVEL_TO_PRIORITY, PRIORITY_DEFINITIONS, SCORE_THRESHOLDS


def configured_path(variable: str, default: Path) -> Path:
    raw = os.environ.get(variable)
    path = Path(raw).expanduser() if raw else default
    return path if path.is_absolute() else PROJECT_ROOT / path


DATA_PATH = configured_path(
    "AML_ALERTS_DATA_PATH", PROJECT_ROOT / "data" / "processed" / "aml_prioritized_alerts.csv"
)
METRICS_PATH = PROJECT_ROOT / "models" / "metrics.json"
RISK_SUMMARY_PATH = PROJECT_ROOT / "models" / "risk_scoring_summary.json"
IMPORTANCE_PATH = PROJECT_ROOT / "models" / "xai_feature_importance.csv"


class RootResponse(BaseModel):
    service: str
    status: str
    docs: str


class HealthResponse(BaseModel):
    status: str
    dataset_available: bool
    total_alerts: int = 0


class AlertRecord(BaseModel):
    model_config = ConfigDict(extra="allow")
    alert_id: str
    priority: str | None = None
    risk_level: str | None = None
    risk_score: float | None = None


class AlertsPage(BaseModel):
    page: int
    page_size: int
    total_matching_alerts: int
    returned: int
    alerts: list[AlertRecord]


class ModelResponse(BaseModel):
    metrics: dict[str, Any]
    heldout_tier_metrics: dict[str, Any]
    feature_importance: list[dict[str, Any]]
    score_thresholds: dict[str, int]
    level_to_priority: dict[str, str]
    priority_definitions: dict[str, str]


def read_alerts(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Prioritized alert data not found: {path}. Run `python run_pipeline.py --demo`.")
    data = pd.read_parquet(path) if path.suffix.lower() == ".parquet" else pd.read_csv(path)
    if "alert_id" not in data.columns:
        raise ValueError(f"Alert data is missing required alert_id column: {path}")
    return data


def clean_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, AttributeError):
            pass
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def row_to_dict(row: pd.Series) -> dict[str, Any]:
    return {key: clean_value(value) for key, value in row.to_dict().items()}


def read_json_or_empty(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@asynccontextmanager
async def lifespan(application: FastAPI):
    try:
        application.state.alerts = read_alerts(DATA_PATH)
    except (FileNotFoundError, ValueError) as exc:
        application.state.alerts = None
        application.state.data_error = str(exc)
    metrics = read_json_or_empty(METRICS_PATH)
    risk_summary = read_json_or_empty(RISK_SUMMARY_PATH)
    if IMPORTANCE_PATH.exists():
        importance = pd.read_csv(IMPORTANCE_PATH).to_dict(orient="records")
    else:
        importance = []
    application.state.model_info = {
        "metrics": metrics,
        "heldout_tier_metrics": risk_summary.get("heldout_tier_metrics", {}),
        "feature_importance": importance,
    }
    yield


app = FastAPI(
    title="AML Alert Triage Engine API",
    description="Synthetic investigator queue API. Scores support human review and do not prove wrongdoing.",
    version="2.0.0",
    lifespan=lifespan,
)
cors_origins = [item.strip() for item in os.environ.get("AML_CORS_ORIGINS", "http://localhost:8501").split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials="*" not in cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def get_dataset() -> pd.DataFrame:
    dataset = getattr(app.state, "alerts", None)
    if dataset is None:
        detail = getattr(app.state, "data_error", "Dataset unavailable; run the demo pipeline.")
        raise HTTPException(status_code=503, detail=detail)
    return dataset


@app.get("/", response_model=RootResponse)
def root():
    return {"service": "AML Alert Triage Engine API", "status": "running", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse)
def health():
    dataset = getattr(app.state, "alerts", None)
    return {
        "status": "healthy" if dataset is not None else "degraded",
        "dataset_available": dataset is not None,
        "total_alerts": int(len(dataset)) if dataset is not None else 0,
    }


@app.get("/stats")
def stats() -> dict[str, Any]:
    df = get_dataset()
    result: dict[str, Any] = {"total_alerts": int(len(df))}
    for column in ("priority", "risk_level", "alert_type"):
        if column in df.columns:
            counts = df[column].fillna("UNKNOWN").astype(str).value_counts()
            result[f"{column}_distribution"] = {str(key): int(value) for key, value in counts.items()}
    for column in ("risk_score", "priority_score"):
        if column in df.columns:
            values = pd.to_numeric(df[column], errors="coerce")
            result[f"average_{column}"] = round(float(values.mean()), 2)
    return result


@app.get("/model", response_model=ModelResponse)
def model_info():
    cached = app.state.model_info
    return {
        **cached,
        "score_thresholds": SCORE_THRESHOLDS,
        "level_to_priority": LEVEL_TO_PRIORITY,
        "priority_definitions": PRIORITY_DEFINITIONS,
    }


@app.get("/alerts", response_model=AlertsPage)
def get_alerts(
    priority: str | None = None,
    risk_level: str | None = None,
    alert_type: str | None = None,
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    sort_by: str = "queue_position",
    sort_order: Literal["asc", "desc"] = "asc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
):
    df = get_dataset()
    filtered = df
    for column, value in (("priority", priority), ("risk_level", risk_level), ("alert_type", alert_type)):
        if value is not None:
            if column not in filtered.columns:
                filtered = filtered.iloc[0:0]
            else:
                filtered = filtered[filtered[column].fillna("").astype(str).str.casefold() == value.casefold()]
    if date_from is not None or date_to is not None:
        if "alert_timestamp" not in filtered.columns:
            filtered = filtered.iloc[0:0]
        else:
            timestamps = pd.to_datetime(filtered["alert_timestamp"], errors="coerce")
            if date_from is not None:
                filtered = filtered[timestamps >= date_from]
                timestamps = timestamps.loc[filtered.index]
            if date_to is not None:
                filtered = filtered[timestamps <= date_to]
    sortable = {"queue_position", "priority_score", "risk_score", "alert_timestamp", "transaction_amount"}
    if sort_by not in sortable or sort_by not in filtered.columns:
        raise HTTPException(status_code=422, detail=f"sort_by must be one of {sorted(sortable)} and present in the dataset")
    filtered = filtered.sort_values(sort_by, ascending=(sort_order == "asc"), kind="mergesort")
    total = len(filtered)
    page_df = filtered.iloc[(page - 1) * page_size : page * page_size]
    alerts = [row_to_dict(row) for _, row in page_df.iterrows()]
    return {
        "page": page,
        "page_size": page_size,
        "total_matching_alerts": int(total),
        "returned": len(alerts),
        "alerts": alerts,
    }


@app.get("/alerts/{alert_id}", response_model=AlertRecord)
def get_alert(alert_id: str):
    df = get_dataset()
    match = df[df["alert_id"].astype(str) == alert_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return row_to_dict(match.iloc[0])


@app.get("/alerts/{alert_id}/explanation")
def get_explanation(alert_id: str) -> dict[str, Any]:
    row = get_alert(alert_id)
    return {
        key: row.get(key)
        for key in (
            "alert_id", "risk_score", "risk_level", "priority_score", "priority",
            "priority_reason", "investigator_explanation", "explanation",
        )
    }
