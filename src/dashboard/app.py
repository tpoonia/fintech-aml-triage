"""
AML Alert Triage Engine - Premium Investigator Dashboard
=========================================================

Replacement for: src/dashboard/app.py

Data source:
    data/processed/aml_prioritized_alerts.csv

This version is designed to look and behave more like an internal AML
operations product rather than a basic Streamlit demo.

Run from the project root:
    streamlit run src/dashboard/app.py

Important:
    Case status / notes are intentionally session-only. They do not change
    the underlying AML CSV dataset.
"""

from pathlib import Path
from datetime import datetime
import json
import html

import pandas as pd
import streamlit as st


# =====================================================================
# CONFIGURATION
# =====================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "aml_prioritized_alerts.csv"
XAI_PATH = PROJECT_ROOT / "models" / "xai_feature_importance.csv"
XAI_SUMMARY_PATH = PROJECT_ROOT / "models" / "xai_summary.json"
RISK_PATH = PROJECT_ROOT / "data" / "processed" / "aml_risk_scored_alerts.csv"
EXPLAINED_PATH = PROJECT_ROOT / "data" / "processed" / "aml_explained_alerts.csv"

st.set_page_config(
    page_title="AML Alert Triage Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =====================================================================
# PREMIUM UI STYLE
# =====================================================================

st.markdown(
    """
    <style>
    .stApp { background: #f6f8fb; }
    .block-container { max-width: 1540px; padding-top: 1.1rem; padding-bottom: 3rem; }

    [data-testid="stSidebar"] {
        background: #101827;
    }
    [data-testid="stSidebar"] * { color: #e8edf5 !important; }
    [data-testid="stSidebar"] .stCaption { color: #aeb9ca !important; }

    .hero {
        background: linear-gradient(135deg, #111827 0%, #1d2a3f 100%);
        border-radius: 20px;
        padding: 26px 30px;
        color: white;
        margin-bottom: 18px;
        box-shadow: 0 12px 35px rgba(15,23,42,.14);
    }
    .hero-row { display:flex; justify-content:space-between; gap:20px; align-items:center; }
    .hero-title { font-size: 2.35rem; font-weight: 800; letter-spacing:-.04em; margin:0; }
    .hero-sub { color:#cbd5e1; font-size:1rem; margin-top:7px; }
    .live-pill {
        border:1px solid rgba(255,255,255,.2); background:rgba(255,255,255,.08);
        border-radius:999px; padding:8px 13px; white-space:nowrap; font-size:.82rem;
    }

    .section { font-size:1.45rem; font-weight:800; color:#172033; margin:20px 0 10px; }
    .section-sub { color:#667085; margin-top:-5px; margin-bottom:12px; }

    .kpi {
        background:white; border:1px solid #e6eaf0; border-radius:15px;
        padding:17px 18px; min-height:116px; box-shadow:0 5px 16px rgba(16,24,40,.045);
    }
    .kpi-label { color:#667085; font-size:.82rem; font-weight:650; text-transform:uppercase; letter-spacing:.04em; }
    .kpi-value { color:#172033; font-size:1.85rem; font-weight:800; margin-top:7px; }
    .kpi-note { color:#7b8494; font-size:.76rem; margin-top:5px; }

    .panel {
        background:white; border:1px solid #e6eaf0; border-radius:15px;
        padding:18px; box-shadow:0 5px 16px rgba(16,24,40,.04); margin-bottom:12px;
    }

    .risk-critical { color:#b42318; font-weight:800; }
    .risk-high { color:#d04a00; font-weight:800; }
    .risk-medium { color:#9a6700; font-weight:800; }
    .risk-low { color:#147d4e; font-weight:800; }

    .badge {
        display:inline-block; padding:4px 9px; border-radius:999px;
        font-size:.73rem; font-weight:800; letter-spacing:.02em;
        background:#eef2f7; color:#344054;
    }
    .badge-critical { background:#fee4e2; color:#b42318; }
    .badge-high { background:#fff0e6; color:#b54708; }
    .badge-medium { background:#fff7d6; color:#9a6700; }
    .badge-low { background:#e8f7ef; color:#147d4e; }
    .badge-p1 { background:#fee4e2; color:#b42318; }
    .badge-p2 { background:#fff0e6; color:#b54708; }
    .badge-p3 { background:#fff7d6; color:#9a6700; }
    .badge-p4 { background:#e8f7ef; color:#147d4e; }

    .alert-header {
        background:#ffffff; border:1px solid #e4e8ef; border-radius:16px;
        padding:18px; margin-bottom:12px;
    }
    .alert-id { font-size:1.35rem; font-weight:800; color:#172033; }
    .muted { color:#667085; }

    .signal {
        border:1px solid #e6eaf0; border-radius:12px; padding:12px;
        background:#fafbfc; min-height:88px;
    }
    .signal-label { font-size:.72rem; color:#667085; text-transform:uppercase; font-weight:700; }
    .signal-value { font-size:1.05rem; color:#172033; font-weight:800; margin-top:4px; }

    .callout {
        background:#f8fafc; border-left:4px solid #475467; padding:13px 15px;
        border-radius:9px; color:#344054;
    }

    div[data-testid="stMetric"] {
        background:white; border:1px solid #e6eaf0; border-radius:14px;
        padding:12px 15px; box-shadow:0 4px 14px rgba(16,24,40,.035);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =====================================================================
# HELPERS
# =====================================================================

@st.cache_data

def load_csv(path: Path):
    if not path.exists():
        return None
    return pd.read_csv(path)


def money(value):
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "N/A"


def number(value, digits=2):
    try:
        return f"{float(value):,.{digits}f}"
    except Exception:
        return "N/A"


def pct(value):
    try:
        x = float(value)
        if x <= 1:
            x *= 100
        return f"{x:.1f}%"
    except Exception:
        return "N/A"


def clean_value(value):
    if pd.isna(value):
        return "N/A"
    return str(value)


def badge(value):
    value = clean_value(value)
    key = value.lower().replace(" ", "-")
    cls = "badge"
    if key in {"critical", "p1"}:
        cls += " badge-critical" if key == "critical" else " badge-p1"
    elif key in {"high", "p2"}:
        cls += " badge-high" if key == "high" else " badge-p2"
    elif key in {"medium", "p3"}:
        cls += " badge-medium" if key == "medium" else " badge-p3"
    elif key in {"low", "p4"}:
        cls += " badge-low" if key == "low" else " badge-p4"
    return f'<span class="{cls}">{html.escape(value)}</span>'


def kpi(label, value, note=""):
    st.markdown(
        f'''<div class="kpi">
        <div class="kpi-label">{html.escape(label)}</div>
        <div class="kpi-value">{html.escape(str(value))}</div>
        <div class="kpi-note">{html.escape(note)}</div>
        </div>''',
        unsafe_allow_html=True,
    )


def signal(label, value):
    st.markdown(
        f'''<div class="signal">
        <div class="signal-label">{html.escape(label)}</div>
        <div class="signal-value">{html.escape(str(value))}</div>
        </div>''',
        unsafe_allow_html=True,
    )


def available(df, columns):
    return [c for c in columns if c in df.columns]


def top_counts(data, column, n=10):
    if column not in data.columns:
        return pd.Series(dtype=int)
    return data[column].fillna("UNKNOWN").astype(str).value_counts().head(n)


def get_explanation(row):
    candidates = [
        "investigator_explanation",
        "explanation",
        "risk_reasons",
        "priority_reason",
        "shap_explanation",
    ]
    for c in candidates:
        if c in row.index:
            value = str(row[c]).strip()
            if value and value.lower() != "nan":
                return value, c
    return "No stored explanation field was found for this alert.", None


def timestamp_age_hours(value):
    try:
        ts = pd.to_datetime(value, errors="coerce")
        if pd.isna(ts):
            return None
        if getattr(ts, "tzinfo", None) is not None:
            now = pd.Timestamp.now(tz=ts.tz)
        else:
            now = pd.Timestamp.now()
        return max(0, (now - ts).total_seconds() / 3600)
    except Exception:
        return None


# =====================================================================
# LOAD DATA
# =====================================================================

df = load_csv(DATA_PATH)

if df is None:
    st.error(f"Dataset not found: {DATA_PATH}")
    st.code("python src/prioritization/prioritize_alerts.py", language="bash")
    st.stop()

if df.empty:
    st.warning("The prioritized alert dataset is empty.")
    st.stop()


# =====================================================================
# SESSION STATE
# =====================================================================

if "case_status" not in st.session_state:
    st.session_state.case_status = {}
if "case_notes" not in st.session_state:
    st.session_state.case_notes = {}
if "assigned_to" not in st.session_state:
    st.session_state.assigned_to = {}
if "selected_alert" not in st.session_state:
    st.session_state.selected_alert = None


# =====================================================================
# HEADER
# =====================================================================

st.markdown(
    f'''
    <div class="hero">
      <div class="hero-row">
        <div>
          <div class="hero-title">🛡️ AML Alert Triage Engine</div>
          <div class="hero-sub">AI-assisted risk scoring • explainability • investigator prioritization • case workflow</div>
        </div>
        <div class="live-pill">● LOCAL ANALYTICS • {len(df):,} ALERTS</div>
      </div>
    </div>
    ''',
    unsafe_allow_html=True,
)


# =====================================================================
# SIDEBAR: WORKSPACE CONTROLS
# =====================================================================

st.sidebar.markdown("# 🛡️ Investigator Console")
st.sidebar.caption("Build a focused work queue, then investigate individual alerts.")

if st.sidebar.button("↻ Reset workspace", use_container_width=True):
    for key in ["case_status", "case_notes", "assigned_to", "selected_alert"]:
        st.session_state.pop(key, None)
    st.rerun()

st.sidebar.divider()

search = st.sidebar.text_input("🔍 Global alert search", placeholder="Alert ID, customer, rule...")

risk_values = ["ALL"]
if "risk_level" in df.columns:
    risk_values += [x for x in ["CRITICAL", "HIGH", "MEDIUM", "LOW"] if x in set(df["risk_level"].astype(str))]
risk_filter = st.sidebar.multiselect("Risk level", risk_values, default=risk_values)

priority_values = ["ALL"]
if "priority" in df.columns:
    priority_values += sorted(df["priority"].dropna().astype(str).unique().tolist())
priority_filter = st.sidebar.multiselect("Priority", priority_values, default=priority_values)

alert_values = ["ALL"]
if "alert_type" in df.columns:
    alert_values += sorted(df["alert_type"].dropna().astype(str).unique().tolist())
alert_filter = st.sidebar.multiselect("Alert type", alert_values, default=alert_values)

outcome_values = ["ALL"]
if "investigation_outcome" in df.columns:
    outcome_values += sorted(df["investigation_outcome"].dropna().astype(str).unique().tolist())
outcome_filter = st.sidebar.multiselect("Outcome", outcome_values, default=outcome_values)

if "risk_score" in df.columns:
    min_risk = float(df["risk_score"].min())
    max_risk = float(df["risk_score"].max())
    risk_range = st.sidebar.slider("Risk score range", min_risk, max_risk, (min_risk, max_risk), 1.0)
else:
    risk_range = None

if "transaction_amount" in df.columns and df["transaction_amount"].notna().any():
    amt_min = float(df["transaction_amount"].min())
    amt_max = float(df["transaction_amount"].max())
    amount_range = st.sidebar.slider("Transaction amount", amt_min, amt_max, (amt_min, amt_max))
else:
    amount_range = None

sort_choice = st.sidebar.selectbox(
    "Queue sorting",
    ["Risk score ↓", "Priority score ↓", "ML probability ↓", "Transaction amount ↓", "Newest alert"],
)

st.sidebar.divider()
st.sidebar.markdown("### Product modules")
st.sidebar.caption("Overview · Queue · Analytics · Investigation · Model XAI · Data Quality")


# =====================================================================
# FILTER ENGINE
# =====================================================================

filtered = df.copy()

if risk_filter and "ALL" not in risk_filter and "risk_level" in filtered.columns:
    filtered = filtered[filtered["risk_level"].astype(str).isin(risk_filter)]

if priority_filter and "ALL" not in priority_filter and "priority" in filtered.columns:
    filtered = filtered[filtered["priority"].astype(str).isin(priority_filter)]

if alert_filter and "ALL" not in alert_filter and "alert_type" in filtered.columns:
    filtered = filtered[filtered["alert_type"].astype(str).isin(alert_filter)]

if outcome_filter and "ALL" not in outcome_filter and "investigation_outcome" in filtered.columns:
    filtered = filtered[filtered["investigation_outcome"].astype(str).isin(outcome_filter)]

if risk_range is not None and "risk_score" in filtered.columns:
    filtered = filtered[filtered["risk_score"].fillna(0).between(risk_range[0], risk_range[1])]

if amount_range is not None and "transaction_amount" in filtered.columns:
    filtered = filtered[filtered["transaction_amount"].fillna(0).between(amount_range[0], amount_range[1])]

if search.strip():
    searchable = available(filtered, [
        "alert_id", "customer_id", "transaction_id", "alert_type",
        "triggered_rule", "risk_level", "priority", "risk_reasons",
        "investigator_explanation", "explanation",
    ])
    mask = pd.Series(False, index=filtered.index)
    q = search.lower().strip()
    for col in searchable:
        mask |= filtered[col].astype(str).str.lower().str.contains(q, na=False, regex=False)
    filtered = filtered[mask]


# =====================================================================
# SORT
# =====================================================================

if sort_choice == "Risk score ↓" and "risk_score" in filtered.columns:
    filtered = filtered.sort_values("risk_score", ascending=False)
elif sort_choice == "Priority score ↓" and "priority_score" in filtered.columns:
    filtered = filtered.sort_values("priority_score", ascending=False)
elif sort_choice == "ML probability ↓" and "ml_probability" in filtered.columns:
    filtered = filtered.sort_values("ml_probability", ascending=False)
elif sort_choice == "Transaction amount ↓" and "transaction_amount" in filtered.columns:
    filtered = filtered.sort_values("transaction_amount", ascending=False)
elif sort_choice == "Newest alert" and "alert_timestamp" in filtered.columns:
    filtered = filtered.sort_values("alert_timestamp", ascending=False)


# =====================================================================
# TOP KPIs
# =====================================================================

total = len(df)
matched = len(filtered)
critical = int((df["risk_level"].astype(str) == "CRITICAL").sum()) if "risk_level" in df.columns else 0
high = int((df["risk_level"].astype(str) == "HIGH").sum()) if "risk_level" in df.columns else 0
p1 = int((df["priority"].astype(str) == "P1").sum()) if "priority" in df.columns else 0
avg_risk = float(df["risk_score"].mean()) if "risk_score" in df.columns else 0
avg_ml = float(df["ml_probability"].mean()) if "ml_probability" in df.columns else 0


# =====================================================================
# NAVIGATION
# =====================================================================

tabs = st.tabs([
    "🏠 Command Center",
    "📋 Triage Queue",
    "🔎 Investigation Desk",
    "📈 Risk Intelligence",
    "🧠 Model & XAI",
    "🧪 Data Quality",
])


# =====================================================================
# TAB 1: COMMAND CENTER
# =====================================================================

with tabs[0]:
    st.markdown('<div class="section">Command Center</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Executive view of the alert population and the current investigator workload.</div>', unsafe_allow_html=True)

    cols = st.columns(6)
    for col, label, value, note in [
        (cols[0], "Total alerts", f"{total:,}", "Prioritized dataset"),
        (cols[1], "In current queue", f"{matched:,}", "After active filters"),
        (cols[2], "Critical", f"{critical:,}", "Highest risk level"),
        (cols[3], "High", f"{high:,}", "High-risk population"),
        (cols[4], "P1 alerts", f"{p1:,}", "Top priority"),
        (cols[5], "Average risk", f"{avg_risk:.2f}", "Risk score mean"),
    ]:
        with col:
            kpi(label, value, note)

    st.write("")
    left, right = st.columns([1.05, .95])

    with left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Risk profile")
        if "risk_level" in df.columns:
            risk_counts = top_counts(df, "risk_level", 10).reindex(["CRITICAL", "HIGH", "MEDIUM", "LOW"], fill_value=0)
            st.bar_chart(risk_counts.rename("alerts"), height=280)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Priority workload")
        if "priority" in df.columns:
            priority_counts = top_counts(df, "priority", 10).reindex(["P1", "P2", "P3", "P4"], fill_value=0)
            st.bar_chart(priority_counts.rename("alerts"), height=280)
        st.markdown('</div>', unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Alert type mix")
        if "alert_type" in df.columns:
            st.bar_chart(top_counts(df, "alert_type", 12).rename("alerts"), height=300)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Investigation outcomes")
        if "investigation_outcome" in df.columns:
            st.bar_chart(top_counts(df, "investigation_outcome", 12).rename("alerts"), height=300)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section">Priority watchlist</div>', unsafe_allow_html=True)
    watch_cols = available(df, [
        "alert_id", "customer_id", "alert_type", "transaction_amount",
        "risk_score", "ml_probability", "risk_level", "priority", "triggered_rule",
    ])
    if watch_cols and "risk_score" in df.columns:
        watch = df.sort_values("risk_score", ascending=False)[watch_cols].head(12)
        st.dataframe(watch, use_container_width=True, hide_index=True, height=400)


# =====================================================================
# TAB 2: TRIAGE QUEUE
# =====================================================================

with tabs[1]:
    st.markdown('<div class="section">Triage Queue</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Turn the full alert population into a focused investigation workload.</div>', unsafe_allow_html=True)

    q1, q2, q3, q4 = st.columns(4)
    with q1: st.metric("Queue size", f"{len(filtered):,}")
    with q2:
        queue_critical = int((filtered["risk_level"].astype(str) == "CRITICAL").sum()) if "risk_level" in filtered.columns else 0
        st.metric("Critical in queue", f"{queue_critical:,}")
    with q3:
        queue_p1 = int((filtered["priority"].astype(str) == "P1").sum()) if "priority" in filtered.columns else 0
        st.metric("P1 in queue", f"{queue_p1:,}")
    with q4:
        st.metric("Average risk", number(filtered["risk_score"].mean()) if "risk_score" in filtered.columns and len(filtered) else "N/A")

    if filtered.empty:
        st.warning("No alerts match the current filters. Reset the workspace or broaden the filters.")
    else:
        queue_cols = available(filtered, [
            "alert_id", "customer_id", "transaction_id", "alert_timestamp",
            "alert_type", "risk_score", "risk_level", "ml_probability",
            "behavioral_risk", "priority_score", "priority", "transaction_amount",
            "triggered_rule", "investigation_outcome",
        ])
        queue = filtered[queue_cols].head(500).copy()

        st.caption(f"Showing {len(queue):,} of {len(filtered):,} matching alerts. Select an alert below to open the investigation desk.")
        st.dataframe(queue, use_container_width=True, hide_index=True, height=500)

        alert_col = "alert_id" if "alert_id" in filtered.columns else filtered.columns[0]
        choices = filtered[alert_col].astype(str).head(500).tolist()
        selected = st.selectbox("Open alert in Investigation Desk", ["— Select an alert —"] + choices)
        if selected != "— Select an alert —":
            st.session_state.selected_alert = selected
            st.success(f"Alert {selected} selected. Open the **Investigation Desk** tab above.")

        csv_bytes = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇ Export current queue as CSV",
            data=csv_bytes,
            file_name="aml_investigation_queue.csv",
            mime="text/csv",
        )


# =====================================================================
# TAB 3: INVESTIGATION DESK
# =====================================================================

with tabs[2]:
    st.markdown('<div class="section">Investigation Desk</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">A single-alert workspace for risk assessment, behavioral evidence, explanation, and case handling.</div>', unsafe_allow_html=True)

    alert_col = "alert_id" if "alert_id" in filtered.columns else filtered.columns[0]
    all_alert_ids = filtered[alert_col].astype(str).tolist()

    default_index = 0
    if st.session_state.selected_alert in all_alert_ids:
        default_index = all_alert_ids.index(st.session_state.selected_alert)

    if not all_alert_ids:
        st.info("No alerts available for investigation under the current filters.")
    else:
        selected_id = st.selectbox("Select alert", all_alert_ids, index=default_index)
        st.session_state.selected_alert = selected_id

        row = filtered[filtered[alert_col].astype(str) == selected_id].iloc[0]

        risk_level = clean_value(row.get("risk_level", "N/A"))
        priority = clean_value(row.get("priority", "N/A"))
        risk_score = number(row.get("risk_score"), 2)
        ml_probability = pct(row.get("ml_probability"))

        st.markdown(
            f'''<div class="alert-header">
            <div class="alert-id">{html.escape(selected_id)}</div>
            <div class="muted" style="margin-top:6px">Risk {badge(risk_level)} &nbsp;&nbsp; Priority {badge(priority)} &nbsp;&nbsp; Risk score <b>{html.escape(risk_score)}</b> &nbsp;&nbsp; ML probability <b>{html.escape(ml_probability)}</b></div>
            </div>''',
            unsafe_allow_html=True,
        )

        s1, s2, s3, s4, s5, s6 = st.columns(6)
        with s1: signal("Risk score", risk_score)
        with s2: signal("ML probability", ml_probability)
        with s3: signal("Behavioral risk", number(row.get("behavioral_risk"), 2))
        with s4: signal("Transaction", money(row.get("transaction_amount")))
        with s5: signal("Counterparties", number(row.get("unique_counterparties"), 0))
        with s6: signal("Cross-border", clean_value(row.get("is_cross_border", "N/A")))

        st.write("")
        detail1, detail2, detail3, detail4 = st.tabs([
            "🧾 Alert evidence",
            "🧠 Why this alert was flagged",
            "👤 Customer context",
            "🗂 Case workspace",
        ])

        with detail1:
            st.subheader("Transaction & rule evidence")
            cols = st.columns(3)
            evidence = [
                ("Transaction ID", row.get("transaction_id")),
                ("Alert type", row.get("alert_type")),
                ("Triggered rule", row.get("triggered_rule")),
                ("Timestamp", row.get("alert_timestamp")),
                ("Transaction amount", money(row.get("transaction_amount"))),
                ("Outcome", row.get("investigation_outcome")),
                ("Outgoing ratio", pct(row.get("outgoing_ratio"))),
                ("Amount deviation", number(row.get("amount_deviation_ratio"), 2)),
                ("Transactions / 7 days", number(row.get("transactions_last_7_days"), 0)),
            ]
            for i, (label, value) in enumerate(evidence):
                with cols[i % 3]:
                    signal(label, clean_value(value))

            if "risk_reasons" in row.index:
                st.markdown("#### Stored risk reasons")
                st.info(clean_value(row["risk_reasons"]))

        with detail2:
            explanation, source_col = get_explanation(row)
            if source_col:
                st.caption(f"Explanation source field: `{source_col}`")
            st.markdown('<div class="callout">', unsafe_allow_html=True)
            st.write(explanation)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("#### Model-facing signals")
            model_signals = available(row.to_frame().T, [
                "customer_transaction_count",
                "customer_avg_transaction_amount",
                "customer_std_transaction_amount",
                "customer_max_transaction_amount",
                "customer_min_transaction_amount",
                "customer_total_transaction_amount",
                "unique_counterparties",
                "unique_countries",
                "transactions_last_7_days",
                "avg_amount_last_7_days",
                "prior_avg_transaction_amount",
                "income_ratio",
                "amount_deviation_ratio",
                "is_cross_border",
            ])
            if model_signals:
                signal_table = pd.DataFrame({
                    "Feature": [x.replace("_", " ").title() for x in model_signals],
                    "Value": [clean_value(row[x]) for x in model_signals],
                })
                st.dataframe(signal_table, use_container_width=True, hide_index=True)

        with detail3:
            st.subheader("Customer profile")
            customer_fields = [
                "customer_id", "customer_type", "customer_country", "account_age_days",
                "monthly_income", "risk_profile", "income_ratio", "customer_transaction_count",
                "customer_avg_transaction_amount", "customer_std_transaction_amount",
                "customer_max_transaction_amount", "customer_min_transaction_amount",
                "customer_total_transaction_amount", "unique_countries", "unique_counterparties",
            ]
            customer_fields = available(row.to_frame().T, customer_fields)
            if customer_fields:
                left, right = st.columns(2)
                for i, field in enumerate(customer_fields):
                    target = left if i % 2 == 0 else right
                    with target:
                        label = field.replace("_", " ").title()
                        value = row[field]
                        if field == "monthly_income":
                            value = money(value)
                        elif field == "income_ratio":
                            value = number(value, 2)
                        elif field == "customer_avg_transaction_amount":
                            value = money(value)
                        target.markdown(f"**{label}:** {clean_value(value)}")
            else:
                st.info("Customer-level fields are not present in this dataset.")

        with detail4:
            st.subheader("Investigator workflow")
            current_status = st.session_state.case_status.get(selected_id, "Open")
            statuses = ["Open", "Under Review", "Escalate", "Close - False Positive", "Close - Cleared"]
            assignees = ["Unassigned", "Investigator 1", "Investigator 2", "Compliance Review"]

            a, b = st.columns(2)
            with a:
                status = st.selectbox("Case status", statuses, index=statuses.index(current_status), key=f"status_{selected_id}")
                assignee = st.selectbox("Assigned investigator", assignees, index=assignees.index(st.session_state.assigned_to.get(selected_id, "Unassigned")), key=f"assignee_{selected_id}")
            with b:
                notes = st.text_area("Investigator notes", value=st.session_state.case_notes.get(selected_id, ""), height=150, placeholder="Document evidence, reasoning, next steps...", key=f"notes_{selected_id}")

            if st.button("💾 Save case workspace", type="primary", key=f"save_{selected_id}"):
                st.session_state.case_status[selected_id] = status
                st.session_state.assigned_to[selected_id] = assignee
                st.session_state.case_notes[selected_id] = notes
                st.success("Case workspace saved for this Streamlit session.")

            st.caption("This demo workflow is session-only; it does not write investigator actions back into the AML CSV.")

        st.divider()
        st.subheader("Raw alert record")
        with st.expander("Show all fields"):
            raw = row.to_frame("value")
            raw.index.name = "field"
            st.dataframe(raw, use_container_width=True)
            st.download_button(
                "⬇ Download alert JSON",
                data=json.dumps(row.to_dict(), default=str, indent=2),
                file_name=f"{selected_id}_alert.json",
                mime="application/json",
                key=f"json_{selected_id}",
            )


# =====================================================================
# TAB 4: RISK INTELLIGENCE
# =====================================================================

with tabs[3]:
    st.markdown('<div class="section">Risk Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Explore how risk, behavioral signals, transaction patterns, and alert types behave across the population.</div>', unsafe_allow_html=True)

    a, b, c, d = st.columns(4)
    with a: st.metric("Mean risk score", number(df["risk_score"].mean()) if "risk_score" in df.columns else "N/A")
    with b: st.metric("Median risk score", number(df["risk_score"].median()) if "risk_score" in df.columns else "N/A")
    with c: st.metric("Mean ML probability", pct(df["ml_probability"].mean()) if "ml_probability" in df.columns else "N/A")
    with d: st.metric("Mean behavioral risk", number(df["behavioral_risk"].mean()) if "behavioral_risk" in df.columns else "N/A")

    left, right = st.columns(2)
    with left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Risk score bands")
        if "risk_score" in df.columns:
            bands = pd.cut(df["risk_score"].fillna(0), [-1, 20, 40, 60, 80, float("inf")], labels=["0–20", "21–40", "41–60", "61–80", "81+"]).value_counts().sort_index()
            st.bar_chart(bands.rename("alerts"), height=300)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("ML probability bands")
        if "ml_probability" in df.columns:
            prob = df["ml_probability"].fillna(0)
            bands = pd.cut(prob, [-.001, .25, .5, .75, 1.001], labels=["0–25%", "25–50%", "50–75%", "75–100%"]).value_counts().sort_index()
            st.bar_chart(bands.rename("alerts"), height=300)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section">Behavioral signal dashboard</div>', unsafe_allow_html=True)
    signal_cols = available(df, [
        "transaction_amount", "transactions_last_7_days", "avg_amount_last_7_days",
        "unique_counterparties", "unique_countries", "outgoing_ratio",
        "amount_deviation_ratio", "income_ratio", "account_age_days",
    ])
    if signal_cols:
        summary = pd.DataFrame({
            "Mean": [df[c].mean() for c in signal_cols],
            "Median": [df[c].median() for c in signal_cols],
            "Std": [df[c].std() for c in signal_cols],
            "Missing %": [df[c].isna().mean() * 100 for c in signal_cols],
        }, index=[c.replace("_", " ").title() for c in signal_cols])
        st.dataframe(summary.round(3), use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Average risk by alert type")
        if "alert_type" in df.columns and "risk_score" in df.columns:
            by_type = df.groupby("alert_type")["risk_score"].mean().sort_values(ascending=False).head(15)
            st.bar_chart(by_type.rename("average risk"), height=350)
    with right:
        st.subheader("Average transaction amount by risk level")
        if "risk_level" in df.columns and "transaction_amount" in df.columns:
            by_risk = df.groupby("risk_level")["transaction_amount"].mean().reindex(["CRITICAL", "HIGH", "MEDIUM", "LOW"]).dropna()
            st.bar_chart(by_risk.rename("average transaction"), height=350)

    st.subheader("Top triggered rules")
    if "triggered_rule" in df.columns:
        rules = top_counts(df, "triggered_rule", 20).rename("alert_count").to_frame()
        st.dataframe(rules, use_container_width=True)


# =====================================================================
# TAB 5: MODEL & XAI
# =====================================================================

with tabs[4]:
    st.markdown('<div class="section">Model & Explainability</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Show recruiters and reviewers that the system does more than produce a score: it exposes the model pipeline and its explanatory artifacts.</div>', unsafe_allow_html=True)

    files = [
        ("Risk scoring output", RISK_PATH),
        ("Explainability output", EXPLAINED_PATH),
        ("Prioritized output", DATA_PATH),
        ("XAI feature importance", XAI_PATH),
        ("XAI summary", XAI_SUMMARY_PATH),
    ]

    status_table = pd.DataFrame({
        "Artifact": [x[0] for x in files],
        "Status": ["Available" if x[1].exists() else "Missing" for x in files],
        "Path": [str(x[1].relative_to(PROJECT_ROOT)) if x[1].exists() else str(x[1].relative_to(PROJECT_ROOT)) for x in files],
    })
    st.dataframe(status_table, use_container_width=True, hide_index=True)

    st.divider()

    if XAI_PATH.exists():
        try:
            xai = pd.read_csv(XAI_PATH)
            st.subheader("Global feature importance")
            st.dataframe(xai.head(25), use_container_width=True, hide_index=True)

            numeric = [c for c in xai.columns if pd.api.types.is_numeric_dtype(xai[c])]
            if numeric and len(xai.columns) >= 2:
                importance_col = numeric[-1]
                feature_col = xai.columns[0]
                chart = xai.sort_values(importance_col, ascending=False).head(15).set_index(feature_col)[importance_col]
                st.bar_chart(chart.rename("mean absolute SHAP"), height=420)
        except Exception as exc:
            st.warning(f"Could not read XAI feature importance: {exc}")
    else:
        st.info("xai_feature_importance.csv is not present yet.")

    if XAI_SUMMARY_PATH.exists():
        st.subheader("XAI run summary")
        try:
            summary = json.loads(XAI_SUMMARY_PATH.read_text(encoding="utf-8"))
            st.json(summary)
        except Exception as exc:
            st.warning(f"Could not read xai_summary.json: {exc}")

    st.divider()
    st.subheader("What the architecture demonstrates")
    architecture = pd.DataFrame({
        "Layer": [
            "Data generation / ingestion",
            "Feature engineering",
            "ML risk scoring",
            "Explainable AI",
            "Alert prioritization",
            "Investigator interface",
        ],
        "Evidence in project": [
            "Synthetic AML customers, transactions, behavior and alerts",
            "Behavioral + transaction + customer features",
            "Logistic Regression + Random Forest artifacts",
            "SHAP-based explanation artifact",
            "Risk/priority queue output",
            "Interactive Streamlit investigation workspace",
        ],
    })
    st.dataframe(architecture, use_container_width=True, hide_index=True)


# =====================================================================
# TAB 6: DATA QUALITY
# =====================================================================

with tabs[5]:
    st.markdown('<div class="section">Data Quality & Pipeline Health</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">A production-minded dashboard should expose the health of the data feeding the model, not hide it.</div>', unsafe_allow_html=True)

    rows, cols = df.shape
    missing_cells = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Rows", f"{rows:,}")
    with c2: st.metric("Columns", f"{cols:,}")
    with c3: st.metric("Missing cells", f"{missing_cells:,}")
    with c4: st.metric("Duplicate rows", f"{duplicate_rows:,}")

    st.subheader("Column quality profile")
    quality = pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "non_null": df.notna().sum(),
        "missing": df.isna().sum(),
        "missing_%": df.isna().mean() * 100,
        "unique": df.nunique(dropna=True),
    })
    quality = quality.sort_values(["missing_%", "unique"], ascending=[False, False])
    st.dataframe(quality.round(2), use_container_width=True, height=500)

    st.subheader("Dataset preview")
    st.dataframe(df.head(25), use_container_width=True, height=450)

    st.subheader("Pipeline artifact paths")
    artifact_paths = pd.DataFrame({
        "Stage": [
            "Risk scored alerts",
            "Explained alerts",
            "Prioritized alerts",
            "Random Forest model",
            "Logistic Regression model",
        ],
        "Expected path": [
            "data/processed/aml_risk_scored_alerts.csv",
            "data/processed/aml_explained_alerts.csv",
            "data/processed/aml_prioritized_alerts.csv",
            "models/aml_random_forest.joblib",
            "models/aml_logistic_regression.joblib",
        ],
        "Exists": [
            RISK_PATH.exists(),
            EXPLAINED_PATH.exists(),
            DATA_PATH.exists(),
            (PROJECT_ROOT / "models" / "aml_random_forest.joblib").exists(),
            (PROJECT_ROOT / "models" / "aml_logistic_regression.joblib").exists(),
        ],
    })
    st.dataframe(artifact_paths, use_container_width=True, hide_index=True)


# =====================================================================
# FOOTER
# =====================================================================

st.divider()
st.caption(
    f"AML Alert Triage Engine • Premium Investigator Dashboard • Dataset: {DATA_PATH.name} • "
    f"Last dashboard load: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
st.caption(
    "Design principle: model output supports investigator review; it is not a substitute for applicable compliance procedures or human investigation."
)
