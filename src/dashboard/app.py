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
import os
import subprocess
import sys

import altair as alt
import pandas as pd
import streamlit as st


# =====================================================================
# CONFIGURATION
# =====================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.triage_config import LEVEL_TO_PRIORITY, PRIORITY_DEFINITIONS, SCORE_THRESHOLDS
from src.dashboard import visuals

_configured_data_path = os.environ.get("AML_ALERTS_DATA_PATH")
DATA_PATH = Path(_configured_data_path).expanduser() if _configured_data_path else PROJECT_ROOT / "data" / "processed" / "aml_prioritized_alerts.csv"
if not DATA_PATH.is_absolute():
    DATA_PATH = PROJECT_ROOT / DATA_PATH
XAI_PATH = PROJECT_ROOT / "models" / "xai_feature_importance.csv"
XAI_SUMMARY_PATH = PROJECT_ROOT / "models" / "xai_summary.json"
RISK_PATH = PROJECT_ROOT / "data" / "processed" / "aml_risk_scored_alerts.csv"
EXPLAINED_PATH = PROJECT_ROOT / "data" / "processed" / "aml_explained_alerts.csv"
METRICS_PATH = PROJECT_ROOT / "models" / "metrics.json"
RISK_SUMMARY_PATH = PROJECT_ROOT / "models" / "risk_scoring_summary.json"
AUTO_BUILD_DEMO = os.environ.get("AML_AUTO_BUILD_DEMO", "1").lower() not in {"0", "false", "no"}

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
    :root{--bg:#070b16;--panel:#0e1526;--line:rgba(148,163,184,.14);--text:#e6edf7;--muted:#8b9ab4;
          --p1:#ff4d6d;--p2:#ff9f43;--p3:#f7c948;--p4:#2dd4bf;--accent:#38bdf8}
    .stApp { background: radial-gradient(1200px 600px at 85% -10%, rgba(56,189,248,.08), transparent 60%), var(--bg); }
    .block-container { max-width: 1540px; padding-top: 1.1rem; padding-bottom: 3rem; }
    [data-testid="stSidebar"] { background: #0a1020; border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] .stCaption { color: var(--muted) !important; }
    [data-testid="stHeader"] { background: transparent; }
    iframe { border: 0; }

    .stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--line); }
    .stTabs [data-baseweb="tab"] { padding: 10px 16px; border-radius: 10px 10px 0 0; color: var(--muted); }
    .stTabs [aria-selected="true"] { color: var(--text); background: rgba(56,189,248,.08); }

    .section { font-size:1.4rem; font-weight:800; color:var(--text); margin:22px 0 4px; letter-spacing:-.02em; }
    .section-sub { color:var(--muted); margin-bottom:14px; }

    .kpi { background:var(--panel); border:1px solid var(--line); border-radius:15px; padding:16px 18px; min-height:108px; }
    .kpi-label { color:var(--muted); font-size:.76rem; font-weight:650; text-transform:uppercase; letter-spacing:.06em; }
    .kpi-value { color:var(--text); font-size:1.75rem; font-weight:800; margin-top:6px; font-variant-numeric:tabular-nums; }
    .kpi-note { color:#71809b; font-size:.76rem; margin-top:4px; }

    .badge { display:inline-block; padding:3px 10px; border-radius:999px; font-size:.73rem; font-weight:800;
             letter-spacing:.02em; background:rgba(148,163,184,.14); color:#cbd5e1; }
    .badge-critical, .badge-p1 { background:rgba(255,77,109,.14); color:var(--p1); border:1px solid rgba(255,77,109,.4); }
    .badge-high, .badge-p2 { background:rgba(255,159,67,.14); color:var(--p2); border:1px solid rgba(255,159,67,.4); }
    .badge-medium, .badge-p3 { background:rgba(247,201,72,.12); color:var(--p3); border:1px solid rgba(247,201,72,.35); }
    .badge-low, .badge-p4 { background:rgba(45,212,191,.12); color:var(--p4); border:1px solid rgba(45,212,191,.35); }

    .alert-header { background:linear-gradient(135deg,#0e1730,#0a1020); border:1px solid var(--line); border-radius:18px;
                    padding:18px 20px; margin-bottom:12px; }
    .alert-id { font-size:1.45rem; font-weight:800; color:var(--text); font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
    .muted { color:var(--muted); }

    .signal { border:1px solid var(--line); border-radius:12px; padding:12px; background:var(--panel); min-height:84px;
              transition:border-color .2s, transform .2s; }
    .signal:hover { border-color:rgba(56,189,248,.45); transform:translateY(-2px); }
    .signal-label { font-size:.7rem; color:var(--muted); text-transform:uppercase; font-weight:700; letter-spacing:.05em; }
    .signal-value { font-size:1.02rem; color:var(--text); font-weight:800; margin-top:4px; word-break:break-word; }

    .callout { background:rgba(56,189,248,.06); border:1px solid rgba(56,189,248,.25); border-left:4px solid var(--accent);
               padding:13px 15px; border-radius:10px; color:#cbd5e1; }
    .disclaimer { display:flex; gap:10px; align-items:center; background:rgba(247,201,72,.06);
                  border:1px solid rgba(247,201,72,.25); color:#e9d8a6; padding:10px 14px; border-radius:12px;
                  font-size:.88rem; margin:12px 0 4px; }
    .tiers { display:flex; gap:8px; flex-wrap:wrap; margin:8px 0 2px; }
    .tier-chip { font-size:.78rem; color:var(--muted); border:1px solid var(--line); border-radius:999px; padding:4px 10px; }
    .tier-chip b { margin-right:4px; }

    div[data-testid="stMetric"] { background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:12px 15px; }
    div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; }
    @media (prefers-reduced-motion: reduce) { .signal { transition:none; } .signal:hover { transform:none; } }
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
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
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


def display_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def top_counts(data, column, n=10):
    if column not in data.columns:
        return pd.Series(dtype=int)
    return data[column].fillna("UNKNOWN").astype(str).value_counts().head(n)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


TIER_SCALE = alt.Scale(domain=visuals.TIER_ORDER, range=[visuals.TIER_COLORS[t] for t in visuals.TIER_ORDER])
LEVEL_TO_TIER = {"CRITICAL": "P1", "HIGH": "P2", "MEDIUM": "P3", "LOW": "P4"}


def style_chart(chart, height=300):
    """Shared dark chart styling so every Altair chart matches the dashboard theme."""

    return (
        chart.properties(height=height, background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(
            labelColor="#8b9ab4", titleColor="#8b9ab4", gridColor="rgba(148,163,184,.10)",
            domainColor="rgba(148,163,184,.25)", tickColor="rgba(148,163,184,.25)", labelFontSize=11, titleFontSize=11,
        )
        .configure_legend(labelColor="#cbd5e1", titleColor="#8b9ab4")
    )


def bar_chart(series: pd.Series, label: str, color="#38bdf8", height=300, horizontal=True):
    data = series.rename("value").reset_index()
    data.columns = ["category", "value"]
    if horizontal:
        enc = alt.Chart(data).mark_bar(cornerRadiusEnd=5, color=color).encode(
            y=alt.Y("category:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
            x=alt.X("value:Q", title=label),
            tooltip=[alt.Tooltip("category:N", title="Category"), alt.Tooltip("value:Q", title=label, format=",.2f")],
        )
    else:
        enc = alt.Chart(data).mark_bar(cornerRadiusEnd=5, color=color).encode(
            x=alt.X("category:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("value:Q", title=label),
            tooltip=[alt.Tooltip("category:N", title="Category"), alt.Tooltip("value:Q", title=label, format=",.2f")],
        )
    st.altair_chart(style_chart(enc, height), width="stretch")


def tier_bar_chart(counts: pd.Series, height=260):
    data = counts.rename("alerts").reset_index()
    data.columns = ["tier", "alerts"]
    data["label"] = data["tier"].map(lambda t: f"{t} · {visuals.TIER_LABELS.get(t, t)}")
    data["share"] = data["alerts"] / max(1, data["alerts"].sum())
    chart = alt.Chart(data).mark_bar(cornerRadiusEnd=6, height=26).encode(
        y=alt.Y("label:N", sort=None, title=None),
        x=alt.X("alerts:Q", title="Alerts (log scale)", scale=alt.Scale(type="symlog"),
                axis=alt.Axis(values=[0, 10, 100, 1000, 10000], format="~s", grid=False)),
        color=alt.Color("tier:N", scale=TIER_SCALE, legend=None),
        tooltip=[alt.Tooltip("label:N", title="Tier"), alt.Tooltip("alerts:Q", format=","),
                 alt.Tooltip("share:Q", title="Share", format=".1%")],
    )
    text = chart.mark_text(align="left", dx=6, color="#cbd5e1").encode(text=alt.Text("alerts:Q", format=","))
    st.altair_chart(style_chart(chart + text, height), width="stretch")
    st.caption("Log scale so the small P1 and P2 tiers stay visible next to P3.")


def risk_histogram(data: pd.DataFrame, height=300):
    frame = pd.DataFrame({
        "risk_score": pd.to_numeric(data["risk_score"], errors="coerce"),
        "tier": data["priority"].astype(str) if "priority" in data else "P3",
    }).dropna()
    bars = alt.Chart(frame).mark_bar(opacity=.9, cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
        x=alt.X("risk_score:Q", bin=alt.Bin(step=2), title="Risk score"),
        y=alt.Y("count():Q", title="Alerts", scale=alt.Scale(type="symlog")),
        color=alt.Color("tier:N", scale=TIER_SCALE, title="Tier"),
        tooltip=[alt.Tooltip("tier:N"), alt.Tooltip("count():Q", title="Alerts", format=",")],
    )
    rules = pd.DataFrame([{"x": v, "label": f"{LEVEL_TO_TIER[k]} ≥ {v}"} for k, v in SCORE_THRESHOLDS.items()])
    rule = alt.Chart(rules).mark_rule(strokeDash=[4, 4], color="#cbd5e1", opacity=.5).encode(x="x:Q")
    lbl = alt.Chart(rules).mark_text(align="left", dx=4, color="#cbd5e1", fontSize=10).encode(
        x="x:Q", y=alt.value(6), text="label:N")
    st.altair_chart(style_chart(bars + rule + lbl, height), width="stretch")


TABLE_CONFIG = {
    "risk_score": st.column_config.ProgressColumn("Risk score", min_value=0, max_value=100, format="%.0f"),
    "ml_probability": st.column_config.ProgressColumn("ML probability", min_value=0, max_value=1, format="percent"),
    "priority_score": st.column_config.ProgressColumn("Priority score", min_value=0, max_value=100, format="%.1f"),
    "transaction_amount": st.column_config.NumberColumn("Amount", format="dollar"),
    "alert_id": st.column_config.TextColumn("Alert"),
    "customer_id": st.column_config.TextColumn("Customer"),
}


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

@st.cache_resource(show_spinner=False)
def build_demo_data() -> bool:
    """Build the seeded demo queue once per server process (shared by all sessions)."""

    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "ensure_demo_data.py")],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return True


df = load_csv(DATA_PATH)

if df is None and AUTO_BUILD_DEMO:
    st.markdown(
        '<div class="section">Preparing the AML demo</div>'
        '<div class="section-sub">First launch: generating synthetic customers, transactions and alerts, then training, '
        'scoring and explaining the models. This takes about a minute and only happens once per server.</div>',
        unsafe_allow_html=True,
    )
    with st.status("Building the synthetic demo dataset…", expanded=True) as status:
        st.write("Generating 1,500 synthetic customers and their transactions")
        st.write("Training Logistic Regression and Random Forest on a customer-disjoint split")
        st.write("Scoring, explaining (SHAP) and prioritizing every alert")
        try:
            build_demo_data()
            status.update(label="Demo dataset ready", state="complete")
        except subprocess.CalledProcessError as exc:
            build_demo_data.clear()
            status.update(label="Demo build failed", state="error")
            st.error("The demo pipeline failed. Details are below.")
            st.code((exc.stderr or str(exc))[-3000:])
            st.stop()
    st.cache_data.clear()
    st.rerun()

if df is None:
    st.error(f"Prioritized alert data is missing: {DATA_PATH}")
    st.info("Generate the synthetic demo dataset to populate this dashboard.")
    if st.button("Generate demo dataset"):
        with st.spinner("Building demo data and the investigator queue..."):
            try:
                subprocess.run(
                    [sys.executable, str(PROJECT_ROOT / "ensure_demo_data.py")],
                    cwd=PROJECT_ROOT,
                    check=True,
                )
                st.cache_data.clear()
                st.rerun()
            except subprocess.CalledProcessError as exc:
                st.error(f"Demo pipeline failed at stage {exc.cmd}: {exc}")
    st.code("python run_pipeline.py --demo", language="bash")
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

DATA_VERSION = (str(DATA_PATH), DATA_PATH.stat().st_mtime if DATA_PATH.exists() else 0)


@st.cache_data(show_spinner=False)
def cached_galaxy(version):
    return visuals.galaxy_payload(load_csv(Path(version[0])))


@st.cache_data(show_spinner=False)
def cached_bounds(version):
    return visuals.explorer_bounds(load_csv(Path(version[0])))


METRICS = load_json(METRICS_PATH)
RISK_SUMMARY = load_json(RISK_SUMMARY_PATH)
_rf = METRICS.get("results", {}).get("random_forest", {})
_p1_holdout = RISK_SUMMARY.get("heldout_tier_metrics", {}).get("P1", {})
_tier_counts = df["priority"].astype(str).value_counts().to_dict() if "priority" in df.columns else {}

hero_kpis = [
    {"label": "Alerts scored", "value": len(df), "note": "synthetic population"},
    {"label": "P1 · critical", "value": _tier_counts.get("P1", 0), "note": "review first"},
    {"label": "P2 · high", "value": _tier_counts.get("P2", 0), "note": "elevated queue"},
]
if _p1_holdout.get("alerts"):
    hero_kpis.append({"label": "P1 hit rate", "value": round(100 * _p1_holdout.get("precision", 0), 1),
                      "decimals": 0, "suffix": "%", "note": "truly suspicious, held-out"})
if _rf.get("pr_auc") is not None:
    hero_kpis.append({"label": "Model PR-AUC", "value": round(_rf["pr_auc"], 3), "decimals": 2,
                      "note": "random forest, held-out"})

st.iframe(
    visuals.galaxy_hero(cached_galaxy(DATA_VERSION), hero_kpis, _tier_counts, len(df), height=470),
    height=472,
)
st.markdown(
    '<div class="disclaimer">⚖️ <span><b>Decision support only.</b> Scores and explanations decide the order of review. '
    'Whether activity is suspicious is decided by a human investigator.</span></div>'
    '<div class="tiers">'
    + "".join(
        f'<span class="tier-chip"><b style="color:{visuals.TIER_COLORS[LEVEL_TO_PRIORITY[level]]}">'
        f'{LEVEL_TO_PRIORITY[level]}</b>{level.title()} · score ≥ {score}</span>'
        for level, score in SCORE_THRESHOLDS.items()
    )
    + f'<span class="tier-chip"><b style="color:{visuals.TIER_COLORS["P4"]}">P4</b>Low · score &lt; {SCORE_THRESHOLDS["MEDIUM"]}</span>'
    + "</div>",
    unsafe_allow_html=True,
)


# =====================================================================
# SIDEBAR: WORKSPACE CONTROLS
# =====================================================================

st.sidebar.markdown("# 🛡️ Investigator Console")
st.sidebar.caption("Build a focused work queue, then investigate individual alerts.")

if st.sidebar.button("↻ Reset workspace", width="stretch"):
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

    cols = st.columns(4)
    for col, label, value, note in [
        (cols[0], "In current queue", f"{matched:,}", "after sidebar filters"),
        (cols[1], "Critical + high", f"{critical + high:,}", "P1 and P2 workload"),
        (cols[2], "Average risk", f"{avg_risk:.1f}", "risk score mean (0–100)"),
        (cols[3], "Avg ML probability", pct(avg_ml), "model output mean"),
    ]:
        with col:
            kpi(label, value, note)

    st.write("")
    left, right = st.columns([1, 1.25])
    with left:
        st.subheader("Priority workload")
        if "priority" in df.columns:
            tier_bar_chart(top_counts(df, "priority", 10).reindex(visuals.TIER_ORDER, fill_value=0))
    with right:
        st.subheader("Risk score distribution")
        if {"risk_score", "priority"} <= set(df.columns):
            risk_histogram(df, height=260)
            st.caption("Dashed lines mark the shared tier thresholds used by scoring, the queue, the API and this dashboard.")

    left, right = st.columns(2)
    with left:
        st.subheader("Alert type mix")
        if "alert_type" in df.columns:
            types = top_counts(df, "alert_type", 8)
            types.index = types.index.str.replace("_", " ").str.replace("+", " + ").str.lower()
            bar_chart(types, "Alerts", color="#38bdf8", height=280)
    with right:
        st.subheader("Investigation outcomes")
        if "investigation_outcome" in df.columns:
            outcomes = top_counts(df, "investigation_outcome", 8)
            outcomes.index = outcomes.index.str.replace("_", " ").str.title()
            bar_chart(outcomes, "Alerts", color="#a78bfa", height=280)

    st.markdown('<div class="section">Priority watchlist</div>', unsafe_allow_html=True)
    watch_cols = available(df, [
        "alert_id", "customer_id", "alert_type", "transaction_amount",
        "risk_score", "ml_probability", "risk_level", "priority", "triggered_rule",
    ])
    if watch_cols and "risk_score" in df.columns:
        watch = df.sort_values("risk_score", ascending=False)[watch_cols].head(12)
        st.dataframe(watch, width="stretch", hide_index=True, height=400, column_config=TABLE_CONFIG)


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
        st.dataframe(queue, width="stretch", hide_index=True, height=500, column_config=TABLE_CONFIG)

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

        def _num(field, default=0.0):
            try:
                value = float(row.get(field, default))
                return default if pd.isna(value) else value
            except (TypeError, ValueError):
                return default

        gauge_signals = [
            ("ML probability", _num("ml_probability") * 100, pct(row.get("ml_probability"))),
            ("Behavioral risk", _num("behavioral_risk") * 100, number(row.get("behavioral_risk"), 2)),
            ("Amount deviation", _num("amount_deviation_signal"), number(row.get("amount_deviation_signal"), 0)),
            ("Recent activity", _num("recent_activity_signal"), number(row.get("recent_activity_signal"), 0)),
            ("Velocity", _num("velocity_signal"), number(row.get("velocity_signal"), 0)),
            ("Counterparties", _num("counterparty_signal"), number(row.get("counterparty_signal"), 0)),
        ]
        st.iframe(
            visuals.risk_gauge(selected_id, _num("risk_score"), priority, SCORE_THRESHOLDS, gauge_signals),
            height=274,
        )
        st.caption("Signal bars are on a 0–100 scale relative to the whole alert population (ML probability and behavioral risk shown as %).")

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
            parts = [html.escape(part.strip()) for part in explanation.replace(" | ", ";").split(";") if part.strip()]
            st.markdown(
                '<div class="callout"><ul style="margin:0;padding-left:18px">'
                + "".join(f"<li>{part}</li>" for part in parts)
                + "</ul></div>",
                unsafe_allow_html=True,
            )

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
                st.dataframe(signal_table, width="stretch", hide_index=True)

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
            raw = row.map(lambda value: "N/A" if pd.isna(value) else str(value)).to_frame("value")
            raw.index.name = "field"
            st.dataframe(raw, width="stretch")
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

    st.markdown('<div class="section">3D risk explorer</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-sub">Each point is an alert placed by what the model and behavior signals say about it. '
        'Rotate the cube to see how P1/P2 alerts separate from routine ones; hover any point for its details. '
        'Follows the sidebar filters.</div>',
        unsafe_allow_html=True,
    )
    if filtered.empty:
        st.info("No alerts match the current filters.")
    elif {"ml_probability", "behavioral_risk", "transaction_amount", "priority", "risk_score", "alert_id"} <= set(filtered.columns):
        st.iframe(visuals.risk_explorer(visuals.explorer_payload(filtered, cached_bounds(DATA_VERSION))), height=602)

    left, right = st.columns(2)
    with left:
        st.subheader("Risk score by tier")
        if {"risk_score", "priority"} <= set(df.columns):
            risk_histogram(df, height=300)
    with right:
        st.subheader("ML probability bands")
        if "ml_probability" in df.columns:
            prob = df["ml_probability"].fillna(0)
            bands = pd.cut(prob, [-.001, .25, .5, .75, 1.001], labels=["0–25%", "25–50%", "50–75%", "75–100%"]).value_counts().sort_index()
            bands.index = bands.index.astype(str)
            bar_chart(bands, "Alerts", color="#a78bfa", height=300, horizontal=False)

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
        st.dataframe(summary.round(3), width="stretch")

    left, right = st.columns(2)
    with left:
        st.subheader("Average risk by alert type")
        if "alert_type" in df.columns and "risk_score" in df.columns:
            by_type = df.groupby("alert_type")["risk_score"].mean().sort_values(ascending=False).head(10)
            by_type.index = by_type.index.str.replace("_", " ").str.replace("+", " + ").str.lower()
            bar_chart(by_type, "Average risk score", color="#ff9f43", height=330)
    with right:
        st.subheader("Average transaction amount by risk level")
        if "risk_level" in df.columns and "transaction_amount" in df.columns:
            by_risk = df.groupby("risk_level")["transaction_amount"].mean().reindex(["CRITICAL", "HIGH", "MEDIUM", "LOW"]).dropna()
            bar_chart(by_risk, "Average amount ($)", color="#2dd4bf", height=330, horizontal=False)

    st.subheader("Top triggered rules")
    if "triggered_rule" in df.columns:
        rules = top_counts(df, "triggered_rule", 20).rename("alert_count").to_frame()
        st.dataframe(rules, width="stretch")


# =====================================================================
# TAB 5: MODEL & XAI
# =====================================================================

with tabs[4]:
    st.markdown('<div class="section">Model & Explainability</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Review the model pipeline, held-out performance, feature importance, and explanatory artifacts.</div>', unsafe_allow_html=True)

    st.iframe(
        visuals.pipeline_flow([
            ("Customers", "synthetic profiles"),
            ("Transactions", "seeded generator"),
            ("Rule alerts", "monitoring rules"),
            ("Features", "pre-alert only"),
            ("Models", "LR + random forest"),
            ("Risk tiers", "shared P1–P4"),
            ("SHAP", "explanations"),
            ("Queue", "API + dashboard"),
        ]),
        height=132,
    )

    results = METRICS.get("results", {})
    if results:
        st.subheader("Held-out model performance")
        st.caption(
            f"Customer-disjoint split ({METRICS.get('split', 'grouped split')}): "
            f"{METRICS.get('train_rows', 0):,} training alerts, {METRICS.get('test_rows', 0):,} test alerts, "
            f"{METRICS.get('customer_overlap', 0)} customers in both."
        )
        cols = st.columns(len(results) * 2)
        names = {"logistic_regression": "Logistic regression", "random_forest": "Random forest"}
        for i, (model_name, m) in enumerate(results.items()):
            with cols[i * 2]:
                kpi(f"{names.get(model_name, model_name)} · PR-AUC", f"{m.get('pr_auc', 0):.3f}",
                    f"ROC-AUC {m.get('roc_auc', 0):.3f}")
            with cols[i * 2 + 1]:
                kpi(f"{names.get(model_name, model_name)} · precision", pct(m.get("precision", 0)),
                    f"recall {pct(m.get('recall', 0))}")

    tiers = RISK_SUMMARY.get("heldout_tier_metrics", {})
    left, right = st.columns([1, 1.2])
    with left:
        if tiers:
            st.subheader("How often each tier was right")
            tier_frame = pd.DataFrame([
                {"tier": t, "precision": v.get("precision", 0), "alerts": v.get("alerts", 0)}
                for t, v in tiers.items()
            ])
            chart = alt.Chart(tier_frame).mark_bar(cornerRadiusEnd=6, height=26).encode(
                y=alt.Y("tier:N", sort=visuals.TIER_ORDER, title=None),
                x=alt.X("precision:Q", title="Share truly suspicious (held-out)", axis=alt.Axis(format="%"),
                        scale=alt.Scale(domain=[0, 1])),
                color=alt.Color("tier:N", scale=TIER_SCALE, legend=None),
                tooltip=[alt.Tooltip("tier:N"), alt.Tooltip("precision:Q", format=".1%"),
                         alt.Tooltip("alerts:Q", title="Held-out alerts", format=",")],
            )
            label = chart.mark_text(align="left", dx=6, color="#cbd5e1").encode(text=alt.Text("precision:Q", format=".0%"))
            st.altair_chart(style_chart(chart + label, 220), width="stretch")
            st.caption("Ground truth is the synthetic `is_suspicious` flag, which the model never sees during training.")
    with right:
        if XAI_PATH.exists():
            try:
                xai = pd.read_csv(XAI_PATH)
                numeric = [c for c in xai.columns if pd.api.types.is_numeric_dtype(xai[c])]
                if numeric:
                    st.subheader("What drives the model (mean |SHAP|)")
                    imp = xai.sort_values(numeric[-1], ascending=False).head(12).set_index(xai.columns[0])[numeric[-1]]
                    imp.index = imp.index.str.replace(r"^(num|cat)__", "", regex=True).str.replace("_", " ")
                    bar_chart(imp, "Mean |SHAP|", color="#38bdf8", height=330)
            except Exception as exc:
                st.warning(f"Could not read XAI feature importance: {exc}")
        else:
            st.info("xai_feature_importance.csv is not present yet.")

    with st.expander("Pipeline artifacts and XAI run summary"):
        files = [
            ("Risk scoring output", RISK_PATH),
            ("Explainability output", EXPLAINED_PATH),
            ("Prioritized output", DATA_PATH),
            ("XAI feature importance", XAI_PATH),
            ("XAI summary", XAI_SUMMARY_PATH),
        ]
        st.dataframe(pd.DataFrame({
            "Artifact": [x[0] for x in files],
            "Status": ["Available" if x[1].exists() else "Missing" for x in files],
            "Path": [display_path(x[1]) for x in files],
        }), width="stretch", hide_index=True)
        if XAI_SUMMARY_PATH.exists():
            st.json(load_json(XAI_SUMMARY_PATH))


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
    st.dataframe(quality.round(2), width="stretch", height=500)

    st.subheader("Dataset preview")
    st.dataframe(df.head(25), width="stretch", height=450)

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
    st.dataframe(artifact_paths, width="stretch", hide_index=True)


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
