"""
app.py
------
The analyst triage dashboard.

This is the part that makes the project a *system* rather than a model: it's
the interface a compliance analyst would actually work in. The queue is
sorted by risk score, so the analyst's attention goes to the alerts most
likely to be real — which is the entire point of the project.

Every alert shows why it was flagged, in plain language, because "the model
said 0.99" is not something an analyst can act on or a regulator will accept.

Run:
    streamlit run dashboard/app.py
Requires the API to be running (see api/main.py).
"""

import os
import requests
import pandas as pd
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="AML Alert Triage", page_icon="🔍", layout="wide")


def api_get(path, **params):
    try:
        r = requests.get(f"{API_URL}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        st.error(f"Cannot reach the scoring API at {API_URL} — is it running? ({e})")
        return None


def api_post(path, payload):
    try:
        r = requests.post(f"{API_URL}{path}", json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        st.error(f"Request failed: {e}")
        return None


st.title("🔍 AML Alert Triage")
st.caption(
    "Alerts ranked by predicted risk, so review time goes to the alerts that matter. "
    "Every score is explained."
)

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Filters")
    min_score = st.slider(
        "Minimum risk score", 0.0, 1.0, 0.5, 0.05,
        help="The operating threshold. Raising it means fewer alerts to review, "
             "at the cost of potentially missing borderline cases.",
    )
    limit = st.number_input("Max alerts shown", 10, 500, 50, 10)
    if st.button("↻ Refresh"):
        st.rerun()

    st.divider()
    stats = api_get("/stats")
    if stats:
        st.header("System stats")
        st.metric("Transactions scored", f"{stats['transactions_scored']:,}")
        st.metric("Alerts raised", f"{stats['alerts_raised']:,}")
        st.metric("Alert rate", f"{stats['alert_rate']*100:.1f}%")
        if stats.get("avg_risk_score") is not None:
            st.metric("Avg risk score", f"{stats['avg_risk_score']:.3f}")
        if stats.get("analyst_feedback"):
            st.caption("Analyst verdicts logged:")
            for verdict, n in stats["analyst_feedback"].items():
                st.caption(f"• {verdict.replace('_', ' ')}: {n}")

# ---------------------------------------------------------------- queue
data = api_get("/alerts", limit=limit, min_score=min_score)
if not data:
    st.stop()

alerts = data["alerts"]
if not alerts:
    st.info("No alerts above the current threshold. Lower the minimum risk score, "
            "or POST transactions to /score to populate the queue.")
    st.stop()

df = pd.DataFrame(alerts)

col1, col2, col3 = st.columns(3)
col1.metric("Alerts in queue", len(df))
col2.metric("High risk (≥0.80)", int((df["risk_score"] >= 0.80).sum()))
col3.metric("Already reviewed", int(df["verdict"].notna().sum()) if "verdict" in df else 0)

st.subheader("Triage queue")
display = df[[
    "transaction_id", "risk_score", "amount", "sender_account",
    "receiver_account", "payment_type", "timestamp", "verdict",
]].copy()
display["risk_score"] = display["risk_score"].round(4)
display = display.rename(columns={
    "transaction_id": "Transaction", "risk_score": "Risk", "amount": "Amount",
    "sender_account": "Sender", "receiver_account": "Receiver",
    "payment_type": "Type", "timestamp": "Time", "verdict": "Verdict",
})
st.dataframe(display, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------- detail
st.subheader("Alert detail")
selected_id = st.selectbox(
    "Select an alert to investigate",
    df["transaction_id"].tolist(),
    format_func=lambda t: f"{t} — risk {df.loc[df.transaction_id == t, 'risk_score'].iloc[0]:.3f}",
)
alert = df[df["transaction_id"] == selected_id].iloc[0]

left, right = st.columns([1, 1.4])

with left:
    st.markdown("**Transaction**")
    details = {
        "Amount": f"${alert['amount']:,.2f}",
        "Sender": f"{alert['sender_account']} ({alert['sender_bank_location']})",
        "Receiver": f"{alert['receiver_account']} ({alert['receiver_bank_location']})",
        "Payment type": alert["payment_type"] or "—",
        "Timestamp": alert["timestamp"],
    }
    st.table(pd.DataFrame({"": list(details.values())}, index=list(details.keys())))
    score = float(alert["risk_score"])
    st.metric("Risk score", f"{score:.4f}")
    st.progress(min(score, 1.0))

with right:
    st.markdown("**Why this was flagged**")
    st.caption(
        "SHAP contributions — how much each factor pushed the score up or down. "
        "This is the audit trail a regulator would ask for."
    )
    contrib = pd.DataFrame(alert["explanation"])
    if not contrib.empty:
        contrib["Impact"] = contrib["shap"].round(3)
        chart_df = contrib.set_index("label")[["Impact"]]
        st.bar_chart(chart_df, horizontal=True)
        for _, c in contrib.iterrows():
            arrow = "🔺" if c["shap"] > 0 else "🔻"
            st.write(f"{arrow} **{c['label']}** = `{c['value']:,.2f}` — {c['direction']}")

# ---------------------------------------------------------------- feedback
st.divider()
st.markdown("**Analyst verdict**")
st.caption(
    "Recorded verdicts become training labels — today's false positives are "
    "what makes the next model version better."
)
fb1, fb2 = st.columns([2, 1])
note = fb1.text_input("Note (optional)", key=f"note_{selected_id}")
verdict = fb2.radio("Verdict", ["confirmed_suspicious", "false_positive"], key=f"v_{selected_id}")
if st.button("Submit verdict", type="primary"):
    result = api_post("/feedback", {
        "transaction_id": selected_id, "verdict": verdict, "analyst_note": note or None,
    })
    if result:
        st.success(f"Recorded: {verdict.replace('_', ' ')} for {selected_id}")
        st.rerun()
