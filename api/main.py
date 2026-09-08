"""
main.py
-------
The FastAPI scoring service.

Endpoints:
  POST /score      score one transaction, store it, return risk + explanation
  GET  /alerts     the analyst triage queue (highest risk first)
  POST /feedback   analyst verdict on an alert (feeds future retraining)
  GET  /health     liveness check (what a deployment platform pings)
  GET  /stats      simple monitoring: alert volume, score distribution

Run locally:
    uvicorn api.main:app --reload --port 8000
Interactive docs (FastAPI generates them for free):
    http://localhost:8000/docs
"""

from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from api import store
from api.scoring import Scorer

app = FastAPI(
    title="AML Alert Triage API",
    description="Risk-scores transactions for money-laundering signals, with SHAP explanations.",
    version="1.0.0",
)

scorer: Optional[Scorer] = None


@app.on_event("startup")
def startup():
    """Load the model once at boot, not per request.

    Loading a model takes ~100ms+; doing it inside the request handler would
    add that to every single call. This is the single most common performance
    mistake in ML services.
    """
    global scorer
    store.init_db()
    scorer = Scorer()


# --------------------------------------------------------------------------
# Request / response schemas. Pydantic validates incoming JSON automatically
# and returns a clear 422 error if a field is missing or the wrong type —
# so bad input can never reach the model.
# --------------------------------------------------------------------------

class Transaction(BaseModel):
    transaction_id: str = Field(..., examples=["TXN0000001"])
    timestamp: str = Field(..., examples=["2025-06-01T14:30:00"])
    sender_account: str = Field(..., examples=["ACC000123"])
    receiver_account: str = Field(..., examples=["ACC000456"])
    amount: float = Field(..., gt=0, examples=[9450.00])
    payment_type: Optional[str] = Field(None, examples=["Cash Deposit"])
    sender_bank_location: Optional[str] = Field(None, examples=["US"])
    receiver_bank_location: Optional[str] = Field(None, examples=["KY"])


class Contribution(BaseModel):
    feature: str
    label: str
    value: float
    shap: float
    direction: str


class ScoreResponse(BaseModel):
    transaction_id: str
    risk_score: float
    risk_band: str
    should_alert: bool
    explanation: List[Contribution]


class Feedback(BaseModel):
    transaction_id: str
    verdict: str = Field(..., pattern="^(false_positive|confirmed_suspicious)$")
    analyst_note: Optional[str] = None


# Threshold chosen from the precision-recall analysis in evaluate.py, not
# the default 0.5 — on imbalanced data 0.5 is an arbitrary and usually bad
# operating point.
ALERT_THRESHOLD = 0.5


def risk_band(score: float) -> str:
    if score >= 0.80:
        return "high"
    if score >= ALERT_THRESHOLD:
        return "medium"
    return "low"


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": scorer is not None}


@app.post("/score", response_model=ScoreResponse)
def score_transaction(txn: Transaction):
    if scorer is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    try:
        datetime.fromisoformat(txn.timestamp)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="timestamp must be ISO format, e.g. 2025-06-01T14:30:00",
        )

    payload = txn.model_dump()

    with store.get_conn() as conn:
        # Store first, then score: the transaction itself is part of the
        # 24-hour window it gets evaluated against (you know about the
        # transaction you're currently looking at).
        store.insert_transaction(conn, payload)
        sender_hist = store.sender_history(conn, txn.sender_account, txn.timestamp)
        receiver_hist = store.receiver_history(conn, txn.receiver_account, txn.timestamp)

        features = scorer.build_features(payload, sender_hist, receiver_hist)
        risk_score, explanation = scorer.score(features)

        store.insert_alert(
            conn,
            transaction_id=txn.transaction_id,
            scored_at=datetime.now(timezone.utc).isoformat(),
            risk_score=risk_score,
            explanation=explanation,
            features=features,
        )

    return ScoreResponse(
        transaction_id=txn.transaction_id,
        risk_score=round(risk_score, 4),
        risk_band=risk_band(risk_score),
        should_alert=risk_score >= ALERT_THRESHOLD,
        explanation=explanation,
    )


@app.get("/alerts")
def get_alerts(limit: int = 50, min_score: float = 0.0):
    """The triage queue — what the analyst dashboard reads."""
    with store.get_conn() as conn:
        return {"alerts": store.fetch_alerts(conn, limit=limit, min_score=min_score)}


@app.post("/feedback")
def submit_feedback(fb: Feedback):
    """Analyst verdict on an alert.

    This is the loop that makes the system improve over time: today's
    false positives are tomorrow's training labels.
    """
    with store.get_conn() as conn:
        exists = conn.execute(
            "SELECT 1 FROM alerts WHERE transaction_id = ?", (fb.transaction_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="No alert with that transaction_id")
        store.insert_feedback(
            conn, fb.transaction_id, fb.verdict, fb.analyst_note,
            datetime.now(timezone.utc).isoformat(),
        )
    return {"status": "recorded", "transaction_id": fb.transaction_id, "verdict": fb.verdict}


@app.get("/stats")
def stats():
    """Lightweight monitoring.

    Watching the score distribution over time is how you catch model drift:
    if the share of high-risk scores suddenly moves, either the world changed
    or something upstream broke.
    """
    with store.get_conn() as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS scored,
                      AVG(risk_score) AS avg_score,
                      SUM(CASE WHEN risk_score >= ? THEN 1 ELSE 0 END) AS alerts_raised,
                      SUM(CASE WHEN risk_score >= 0.8 THEN 1 ELSE 0 END) AS high_risk
               FROM alerts""",
            (ALERT_THRESHOLD,),
        ).fetchone()
        fb = conn.execute(
            """SELECT verdict, COUNT(*) AS n FROM feedback GROUP BY verdict"""
        ).fetchall()

    scored = row["scored"] or 0
    return {
        "transactions_scored": scored,
        "alerts_raised": row["alerts_raised"] or 0,
        "high_risk_alerts": row["high_risk"] or 0,
        "alert_rate": round((row["alerts_raised"] or 0) / scored, 4) if scored else 0,
        "avg_risk_score": round(row["avg_score"], 4) if row["avg_score"] is not None else None,
        "analyst_feedback": {r["verdict"]: r["n"] for r in fb},
    }
