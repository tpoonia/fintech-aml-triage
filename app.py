"""
AML Alert Triage Engine - investigator workspace
=================================================

A case-management style Streamlit app on top of the synthetic triage pipeline:

    Overview   - workload at a glance, the alert galaxy, alerts that need attention
    Work queue - filter and sort alerts; click a row to open the case
    Case       - one alert: risk gauge, why it was flagged, customer history, actions
    Insights   - 3D risk explorer and population analytics
    Model      - held-out performance, explainability, data quality

Data source (built automatically on first launch):
    data/processed/aml_prioritized_alerts.csv

Run from the project root:
    streamlit run src/dashboard/app.py

Case status, assignee and notes are session-only by design; they never change
the underlying dataset. Scores support human review; they are not findings.
"""

from datetime import datetime
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import altair as alt
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.triage_config import SCORE_THRESHOLDS  # noqa: E402
from src.dashboard import visuals  # noqa: E402

_configured = os.environ.get("AML_ALERTS_DATA_PATH")
DATA_PATH = Path(_configured).expanduser() if _configured else PROJECT_ROOT / "data" / "processed" / "aml_prioritized_alerts.csv"
if not DATA_PATH.is_absolute():
    DATA_PATH = PROJECT_ROOT / DATA_PATH
TX_PATH = PROJECT_ROOT / "data" / "raw" / "transactions.csv"
XAI_PATH = PROJECT_ROOT / "models" / "xai_feature_importance.csv"
XAI_SUMMARY_PATH = PROJECT_ROOT / "models" / "xai_summary.json"
METRICS_PATH = PROJECT_ROOT / "models" / "metrics.json"
RISK_SUMMARY_PATH = PROJECT_ROOT / "models" / "risk_scoring_summary.json"
AUTO_BUILD_DEMO = os.environ.get("AML_AUTO_BUILD_DEMO", "1").lower() not in {"0", "false", "no"}

PAGES = ["Overview", "Work queue", "Case", "Insights", "Model"]
PAGE_ICONS = {"Overview": ":material/space_dashboard:", "Work queue": ":material/inbox:",
              "Case": ":material/folder_open:", "Insights": ":material/insights:", "Model": ":material/model_training:"}
STATUSES = ["Open", "In review", "Escalated", "Closed – no concern", "Closed – SAR filed"]
ASSIGNEES = ["Unassigned", "A. Rivera", "J. Chen", "M. Okafor", "Compliance lead"]

st.set_page_config(page_title="AML Alert Triage", page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")


# =====================================================================
# THEME
# =====================================================================

st.markdown(
    """
    <style>
    :root{--bg:#070b16;--panel:#0d1424;--panel-2:#111a2e;--line:rgba(148,163,184,.13);--line-2:rgba(148,163,184,.22);
          --text:#e6edf7;--muted:#8b9ab4;--faint:#64748b;--accent:#38bdf8;
          --p1:#ff4d6d;--p2:#ff9f43;--p3:#f7c948;--p4:#2dd4bf;--ok:#34d399}
    .stApp{background:radial-gradient(1100px 520px at 90% -12%,rgba(56,189,248,.07),transparent 60%),var(--bg)}
    .block-container{max-width:1440px;padding-top:.9rem;padding-bottom:2.5rem}
    [data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],[data-testid="stSidebarNav"]{display:none}
    [data-testid="stHeader"]{background:transparent;height:0}
    [data-testid="stToolbar"]{right:.5rem}
    iframe{border:0}
    h1,h2,h3{letter-spacing:-.02em}
    h3{font-size:1.05rem !important;font-weight:700 !important;color:var(--text)}

    .appbar{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:6px 2px 14px}
    .brand{display:flex;align-items:center;gap:12px}
    .logo{width:36px;height:36px;border-radius:10px;display:grid;place-items:center;
          background:linear-gradient(135deg,#0ea5e9,#6366f1);box-shadow:0 6px 20px rgba(56,189,248,.25)}
    .brand-name{font-weight:800;font-size:1.06rem;color:var(--text);line-height:1.1}
    .brand-sub{font-size:.76rem;color:var(--muted)}
    .appbar-meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:flex-end}
    .chip{display:inline-flex;align-items:center;gap:6px;font-size:.74rem;color:#cbd5e1;border:1px solid var(--line-2);
          background:rgba(255,255,255,.02);border-radius:999px;padding:4px 10px;white-space:nowrap}
    .chip.warn{color:#facc15;border-color:rgba(250,204,21,.35);background:rgba(250,204,21,.06)}
    .dot{width:7px;height:7px;border-radius:50%;display:inline-block}
    div[data-testid="stButtonGroup"] button{border-radius:10px !important}

    .ph{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;margin:14px 0 6px}
    .ph h2{font-size:1.55rem;font-weight:800;margin:0;color:var(--text)}
    .ph p{margin:4px 0 0;color:var(--muted);font-size:.92rem}

    .stat{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px 16px;height:100%}
    .stat .l{font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;font-weight:650}
    .stat .v{font-size:1.65rem;font-weight:800;color:var(--text);margin-top:4px;font-variant-numeric:tabular-nums}
    .stat .n{font-size:.76rem;color:var(--faint);margin-top:2px}
    .stat .bar{height:4px;border-radius:4px;margin-top:10px;background:rgba(148,163,184,.12);overflow:hidden}
    .stat .bar span{display:block;height:100%;border-radius:4px}

    .tier{display:inline-flex;align-items:center;gap:6px;padding:2px 9px;border-radius:999px;font-size:.72rem;font-weight:800;white-space:nowrap}
    .tier.P1{color:var(--p1);background:rgba(255,77,109,.12);border:1px solid rgba(255,77,109,.38)}
    .tier.P2{color:var(--p2);background:rgba(255,159,67,.12);border:1px solid rgba(255,159,67,.38)}
    .tier.P3{color:var(--p3);background:rgba(247,201,72,.10);border:1px solid rgba(247,201,72,.32)}
    .tier.P4{color:var(--p4);background:rgba(45,212,191,.10);border:1px solid rgba(45,212,191,.32)}
    .status{display:inline-block;padding:2px 9px;border-radius:999px;font-size:.72rem;font-weight:700;
            color:#cbd5e1;background:rgba(148,163,184,.12);border:1px solid var(--line-2)}

    .att{display:flex;align-items:center;gap:14px;padding:8px 2px}
    .att .id{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-weight:700;color:var(--text);font-size:.9rem}
    .att .why{color:var(--muted);font-size:.8rem;margin-top:2px}
    .att .amt{margin-left:auto;text-align:right;font-variant-numeric:tabular-nums;color:var(--text);font-weight:700;font-size:.9rem}
    .att .amt small{display:block;color:var(--faint);font-weight:500;font-size:.72rem}

    .case-head{background:linear-gradient(135deg,#0f1a33,#0a1020);border:1px solid var(--line);border-radius:16px;padding:16px 20px}
    .case-id{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:1.5rem;font-weight:800;color:var(--text)}
    .facts{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-top:14px}
    .fact .k{font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;font-weight:650}
    .fact .v{font-size:.98rem;color:var(--text);font-weight:700;margin-top:3px;word-break:break-word}
    .reason{display:flex;gap:10px;align-items:flex-start;padding:9px 0;border-bottom:1px solid var(--line);color:#d5deeb;font-size:.9rem}
    .reason:last-child{border-bottom:0}
    .reason i{flex:none;width:20px;height:20px;border-radius:6px;display:grid;place-items:center;font-style:normal;font-size:.7rem;
              background:rgba(56,189,248,.12);color:var(--accent);font-weight:800}
    .kv{display:flex;justify-content:space-between;gap:10px;padding:7px 0;border-bottom:1px dashed var(--line);font-size:.88rem}
    .kv:last-child{border-bottom:0}.kv span:first-child{color:var(--muted)}.kv span:last-child{color:var(--text);font-weight:600;text-align:right}
    .note{font-size:.78rem;color:var(--faint)}
    .disclaimer{display:flex;gap:10px;align-items:center;background:rgba(250,204,21,.05);border:1px solid rgba(250,204,21,.22);
                color:#e9d8a6;padding:9px 14px;border-radius:12px;font-size:.84rem;margin:10px 0 12px}

    div[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:12px;overflow:hidden}
    div[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--line) !important;border-radius:14px !important;background:var(--panel)}
    div[data-testid="stExpander"] details{border-color:var(--line) !important;border-radius:12px !important;background:var(--panel)}
    @media (max-width:900px){.facts{grid-template-columns:repeat(2,minmax(0,1fr))}.appbar-meta{display:none}}
    </style>
    """,
    unsafe_allow_html=True,
)


# =====================================================================
# FORMATTING HELPERS
# =====================================================================

_ACRONYMS = {"sar": "SAR", "ml": "ML", "id": "ID", "ach": "ACH", "atm": "ATM", "swift": "SWIFT", "p2p": "P2P"}


def human(value) -> str:
    """NEW_COUNTERPARTY+RAPID_FUND_MOVEMENT -> 'New counterparty + rapid fund movement'."""

    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    parts = []
    for chunk in str(value).split("+"):
        words = chunk.strip().replace("_", " ").lower().split()
        parts.append(" ".join(_ACRONYMS.get(w, w) for w in words))
    text = " + ".join(p for p in parts if p).replace("tier2", "tier 2")
    return text[:1].upper() + text[1:] if text else "—"


def feature_name(raw: str) -> str:
    raw = re.sub(r"^(num|cat)__", "", str(raw))
    for prefix, label in (("triggered_rule_", "Rule"), ("alert_type_", "Alert type"), ("customer_type_", "Customer type"),
                          ("customer_country_", "Country"), ("risk_profile_", "Risk profile")):
        if raw.startswith(prefix):
            return f"{label}: {human(raw[len(prefix):]).lower()}"
    raw = raw.replace("_", " ")
    return raw[:1].upper() + raw[1:]


def money(value, digits=2) -> str:
    try:
        return f"${float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def pct(value, digits=1) -> str:
    try:
        x = float(value)
        return f"{x * 100:.{digits}f}%" if x <= 1 else f"{x:.{digits}f}%"
    except (TypeError, ValueError):
        return "—"


def num(value, digits=0) -> str:
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def fnum(row, field, default=0.0) -> float:
    try:
        value = float(row.get(field, default))
        return default if pd.isna(value) else value
    except (TypeError, ValueError):
        return default


def tier_badge(tier: str) -> str:
    t = html.escape(str(tier))
    return f'<span class="tier {t}">{t} · {visuals.TIER_LABELS.get(t, "")}</span>'


def when(value) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    return "—" if pd.isna(ts) else ts.strftime("%b %d, %Y · %H:%M")


def page_header(title: str, subtitle: str = ""):
    st.markdown(f'<div class="ph"><div><h2>{html.escape(title)}</h2><p>{html.escape(subtitle)}</p></div></div>',
                unsafe_allow_html=True)


def stat(label, value, note="", bar=None, color="#38bdf8"):
    bar_html = (f'<div class="bar"><span style="width:{max(0, min(100, bar)):.1f}%;background:{color}"></span></div>'
                if bar is not None else "")
    st.markdown(f'<div class="stat"><div class="l">{html.escape(label)}</div><div class="v">{html.escape(str(value))}</div>'
                f'<div class="n">{html.escape(note)}</div>{bar_html}</div>', unsafe_allow_html=True)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def display_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


# =====================================================================
# CHART HELPERS
# =====================================================================

TIER_SCALE = alt.Scale(domain=visuals.TIER_ORDER, range=[visuals.TIER_COLORS[t] for t in visuals.TIER_ORDER])
LEVEL_TO_TIER = {"CRITICAL": "P1", "HIGH": "P2", "MEDIUM": "P3", "LOW": "P4"}


def style_chart(chart, height=280):
    return (
        chart.properties(height=height, background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(labelColor="#8b9ab4", titleColor="#8b9ab4", gridColor="rgba(148,163,184,.09)",
                        domainColor="rgba(148,163,184,.25)", tickColor="rgba(148,163,184,.25)",
                        labelFontSize=11, titleFontSize=11, titleFontWeight=500)
        .configure_legend(labelColor="#cbd5e1", titleColor="#8b9ab4", orient="top", direction="horizontal")
    )


def bar_chart(series: pd.Series, label: str, color="#38bdf8", height=260, fmt=",.0f", labels=False):
    data = series.rename("value").reset_index()
    data.columns = ["category", "value"]
    enc = alt.Chart(data).mark_bar(cornerRadiusEnd=5, color=color).encode(
        y=alt.Y("category:N", sort=data.sort_values("value", ascending=False)["category"].tolist(), title=None,
                axis=alt.Axis(labelLimit=240, labelOverlap=False)),
        x=alt.X("value:Q", title=label),
        tooltip=[alt.Tooltip("category:N", title="Category"), alt.Tooltip("value:Q", title=label, format=fmt)])
    if labels:
        enc = enc + enc.mark_text(align="left", dx=5, color="#cbd5e1", fontSize=11).encode(text=alt.Text("value:Q", format=fmt))
    st.altair_chart(style_chart(enc, height), width="stretch")


def risk_histogram(data: pd.DataFrame, height=260):
    frame = pd.DataFrame({"risk_score": pd.to_numeric(data["risk_score"], errors="coerce"),
                          "tier": data["priority"].astype(str)}).dropna()
    bars = alt.Chart(frame).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
        x=alt.X("risk_score:Q", bin=alt.Bin(step=2), title="Risk score"),
        y=alt.Y("count():Q", title="Alerts (log scale)", scale=alt.Scale(type="symlog")),
        color=alt.Color("tier:N", scale=TIER_SCALE, title=None),
        tooltip=[alt.Tooltip("tier:N", title="Tier"), alt.Tooltip("count():Q", title="Alerts", format=",")])
    rules = pd.DataFrame([{"x": v, "label": f"{LEVEL_TO_TIER[k]} ≥ {v}"} for k, v in SCORE_THRESHOLDS.items()])
    rule = alt.Chart(rules).mark_rule(strokeDash=[4, 4], color="#cbd5e1", opacity=.45).encode(x="x:Q")
    lbl = alt.Chart(rules).mark_text(align="left", dx=4, color="#cbd5e1", fontSize=10).encode(
        x="x:Q", y=alt.value(6), text="label:N")
    st.altair_chart(style_chart(bars + rule + lbl, height), width="stretch")


def tier_bars(counts: dict, height=180):
    data = pd.DataFrame([{"tier": t, "label": f"{t} · {visuals.TIER_LABELS[t]}", "alerts": counts.get(t, 0)}
                         for t in visuals.TIER_ORDER])
    data["share"] = data["alerts"] / max(1, data["alerts"].sum())
    chart = alt.Chart(data).mark_bar(cornerRadiusEnd=6, height=22).encode(
        y=alt.Y("label:N", sort=None, title=None),
        x=alt.X("alerts:Q", title=None, scale=alt.Scale(type="symlog"), axis=None),
        color=alt.Color("tier:N", scale=TIER_SCALE, legend=None),
        tooltip=[alt.Tooltip("label:N", title="Tier"), alt.Tooltip("alerts:Q", format=","),
                 alt.Tooltip("share:Q", title="Share", format=".1%")])
    text = chart.mark_text(align="left", dx=6, color="#cbd5e1").encode(text=alt.Text("alerts:Q", format=","))
    st.altair_chart(style_chart(chart + text, height), width="stretch")


# =====================================================================
# DATA
# =====================================================================

@st.cache_data(show_spinner=False)
def load_table(path_str: str, mtime: float):
    path = Path(path_str)
    if not path.exists():
        return None
    return pd.read_parquet(path) if path.suffix.lower() == ".parquet" else pd.read_csv(path)


@st.cache_data(show_spinner=False)
def load_transactions(path_str: str, mtime: float):
    path = Path(path_str)
    if not path.exists():
        return None
    tx = pd.read_csv(path)
    tx["timestamp"] = pd.to_datetime(tx["timestamp"], errors="coerce")
    return tx


@st.cache_resource(show_spinner=False)
def build_demo_data() -> bool:
    """Build the seeded demo queue once per server process (shared by all sessions)."""

    subprocess.run([sys.executable, str(PROJECT_ROOT / "ensure_demo_data.py")], cwd=PROJECT_ROOT,
                   check=True, capture_output=True, text=True)
    return True


def mtime(path: Path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


df = load_table(str(DATA_PATH), mtime(DATA_PATH))

if df is None and AUTO_BUILD_DEMO:
    page_header("Preparing the AML demo", "First launch on this server: generating synthetic customers, transactions "
                "and alerts, then training, scoring and explaining the models. This takes about a minute and happens once.")
    with st.status("Building the synthetic demo dataset…", expanded=True) as status:
        st.write("Generating 1,500 synthetic customers and their transactions")
        st.write("Training logistic regression and random forest on a customer-disjoint split")
        st.write("Scoring, explaining (SHAP) and prioritizing every alert")
        try:
            build_demo_data()
            status.update(label="Demo dataset ready", state="complete")
        except subprocess.CalledProcessError as exc:
            build_demo_data.clear()
            status.update(label="Demo build failed", state="error")
            st.code((exc.stderr or str(exc))[-3000:])
            st.stop()
    st.cache_data.clear()
    st.rerun()

if df is None:
    st.error(f"Prioritized alert data is missing: {display_path(DATA_PATH)}")
    if st.button("Generate demo dataset", type="primary"):
        with st.spinner("Building demo data…"):
            build_demo_data()
        st.cache_data.clear()
        st.rerun()
    st.code("python run_pipeline.py --demo", language="bash")
    st.stop()

if df.empty:
    st.warning("The prioritized alert dataset is empty.")
    st.stop()

TIER_RANK = {t: i for i, t in enumerate(visuals.TIER_ORDER)}
df = df.copy()
df["alert_id"] = df["alert_id"].astype(str)
df["priority"] = df["priority"].astype(str)
_order_col = "priority_score" if "priority_score" in df.columns else "risk_score"
df = (df.assign(_tier_rank=df["priority"].map(TIER_RANK).fillna(9))
        .sort_values(["_tier_rank", _order_col], ascending=[True, False])
        .drop(columns="_tier_rank").reset_index(drop=True))
ALERT_INDEX = {aid: i for i, aid in enumerate(df["alert_id"])}
DATA_VERSION = (str(DATA_PATH), mtime(DATA_PATH))
METRICS = load_json(METRICS_PATH)
RISK_SUMMARY = load_json(RISK_SUMMARY_PATH)
TIER_COUNTS = df["priority"].value_counts().to_dict()


@st.cache_data(show_spinner=False)
def cached_galaxy(version):
    return visuals.galaxy_payload(load_table(version[0], version[1]))


@st.cache_data(show_spinner=False)
def cached_explorer(version):
    full = load_table(version[0], version[1])
    return visuals.explorer_payload(full, visuals.explorer_bounds(full))


# =====================================================================
# SESSION STATE + NAVIGATION ACTIONS
# =====================================================================

st.session_state.setdefault("nav", "Overview")
st.session_state.setdefault("case_status", {})
st.session_state.setdefault("case_notes", {})
st.session_state.setdefault("assigned_to", {})
st.session_state.setdefault("case_log", {})
st.session_state.setdefault("selected_alert", df["alert_id"].iloc[0])
st.session_state.setdefault("queue_ids", df.loc[df["priority"].isin(["P1", "P2"]), "alert_id"].tolist())

_qp_alert = st.query_params.get("alert")  # deep link: ?alert=A000123
if _qp_alert and _qp_alert in ALERT_INDEX and st.session_state.get("_qp_done") != _qp_alert:
    st.session_state.selected_alert = _qp_alert
    st.session_state.nav = "Case"
    st.session_state._qp_done = _qp_alert


def open_case(alert_id: str):
    st.session_state.selected_alert = alert_id
    st.session_state.nav = "Case"


def go(page_name: str):
    st.session_state.nav = page_name


def on_queue_select():
    rows = st.session_state.get("queue_table", {}).get("selection", {}).get("rows", [])
    ids = st.session_state.get("queue_ids", [])
    if rows and rows[0] < len(ids):
        open_case(ids[rows[0]])


def step_case(delta: int):
    ids = st.session_state.get("queue_ids") or df["alert_id"].tolist()
    current = st.session_state.selected_alert
    i = ids.index(current) if current in ids else -1
    st.session_state.selected_alert = ids[max(0, min(len(ids) - 1, i + delta))]


def status_of(alert_id: str) -> str:
    return st.session_state.case_status.get(alert_id, "Open")


def save_case(alert_id: str, then_next: bool = False):
    status = st.session_state[f"st_{alert_id}"]
    assignee = st.session_state[f"as_{alert_id}"]
    st.session_state.case_status[alert_id] = status
    st.session_state.assigned_to[alert_id] = assignee
    st.session_state.case_notes[alert_id] = st.session_state[f"nt_{alert_id}"]
    st.session_state.case_log.setdefault(alert_id, []).append(f"{datetime.now():%H:%M} · {status} · {assignee}")
    st.toast(f"{alert_id} saved as {status}", icon="✅")
    if then_next:
        step_case(1)


# =====================================================================
# APP BAR + NAV
# =====================================================================

_rf = METRICS.get("results", {}).get("random_forest", {})
_worked = len(st.session_state.case_status)
st.markdown(
    f'''<div class="appbar"><div class="brand"><div class="logo">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6l8-3z"/><path d="M9 12l2 2 4-4"/></svg></div>
      <div><div class="brand-name">AML Alert Triage</div><div class="brand-sub">Investigator workspace</div></div></div>
      <div class="appbar-meta">
        <span class="chip warn">● Synthetic demo data</span>
        <span class="chip"><span class="dot" style="background:var(--p1)"></span>{TIER_COUNTS.get("P1", 0):,} P1 alerts</span>
        <span class="chip">{len(df):,} alerts scored</span>
        <span class="chip">{_worked:,} worked this session</span>
        <span class="chip">Random forest · PR-AUC {_rf.get("pr_auc", 0):.2f}</span>
      </div></div>''',
    unsafe_allow_html=True,
)

page = st.segmented_control("Navigation", PAGES, key="nav", label_visibility="collapsed",
                            format_func=lambda p: f"{PAGE_ICONS[p]} {p}")
if page is None:  # clicking the active segment deselects it; stay on the previous page
    page = st.session_state.get("_last_page", "Overview")
st.session_state._last_page = page


# =====================================================================
# PAGE: OVERVIEW
# =====================================================================

def render_overview():
    p1, p2 = TIER_COUNTS.get("P1", 0), TIER_COUNTS.get("P2", 0)
    p1_hold = RISK_SUMMARY.get("heldout_tier_metrics", {}).get("P1", {})
    kpis = [
        {"label": "Alerts scored", "value": len(df), "note": "synthetic population"},
        {"label": "P1 · review first", "value": p1, "note": f"{p1 / len(df):.1%} of alerts"},
        {"label": "P2 · elevated", "value": p2, "note": f"{p2 / len(df):.1%} of alerts"},
    ]
    if p1_hold.get("alerts"):
        kpis.append({"label": "P1 hit rate", "value": round(100 * p1_hold.get("precision", 0), 1), "suffix": "%",
                     "note": "truly suspicious, held-out"})
    st.iframe(visuals.galaxy_hero(cached_galaxy(DATA_VERSION), kpis, TIER_COUNTS, len(df), height=400), height=402)
    st.markdown('<div class="disclaimer">⚖️ <span><b>Decision support only.</b> Scores set the order of review; '
                'a human investigator decides whether activity is suspicious.</span></div>', unsafe_allow_html=True)

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        with st.container(border=True):
            head, action = st.columns([3, 1.1], vertical_alignment="center")
            head.markdown("### Needs attention")
            action.button("Open work queue →", width="stretch", on_click=go, args=("Work queue",))
            st.caption("Highest-priority alerts that are still open.")
            todo = df[df["alert_id"].map(status_of).isin(["Open", "In review"])].head(7)
            for _, row in todo.iterrows():
                c1, c2 = st.columns([6, 1], vertical_alignment="center")
                reason = str(row.get("risk_reasons", "")).split(";")[0].strip() or human(row.get("alert_type"))
                c1.markdown(
                    f'<div class="att"><div>{tier_badge(row["priority"])}</div>'
                    f'<div><div class="id">{html.escape(row["alert_id"])} '
                    f'<span class="note">· {html.escape(str(row.get("customer_id", "")))}</span></div>'
                    f'<div class="why">{html.escape(reason[:1].upper() + reason[1:])} · score {num(row.get("risk_score"))}</div></div>'
                    f'<div class="amt">{money(row.get("transaction_amount"), 0)}<small>{when(row.get("alert_timestamp"))}</small></div></div>',
                    unsafe_allow_html=True)
                c2.button("Open", key=f"att_{row['alert_id']}", on_click=open_case, args=(row["alert_id"],), width="stretch")
    with right:
        with st.container(border=True):
            st.markdown("### Workload by priority")
            tier_bars(TIER_COUNTS)
        with st.container(border=True):
            st.markdown("### Risk score distribution")
            risk_histogram(df, height=190)


# =====================================================================
# PAGE: WORK QUEUE
# =====================================================================

def render_queue():
    page_header("Work queue", "Narrow the alert population to a review list, then click a row to open the case.")
    with st.container(border=True):
        f1, f2, f3, f4 = st.columns([2.1, 2.6, 1.7, 1.4])
        search = f1.text_input("Search", placeholder="Alert, customer or transaction ID", key="q_search")
        tiers = f2.pills("Priority", visuals.TIER_ORDER, selection_mode="multi", default=["P1", "P2"], key="q_tiers",
                         format_func=lambda t: f"{t} · {visuals.TIER_LABELS[t]}")
        types = ["All alert types"] + sorted(df["alert_type"].dropna().astype(str).unique().tolist())
        a_type = f3.selectbox("Alert type", types, key="q_type",
                              format_func=lambda t: t if t.startswith("All") else human(t))
        status_filter = f4.selectbox("Case status", ["Any status"] + STATUSES, key="q_status")
        with st.expander("More filters and sorting"):
            m1, m2, m3 = st.columns(3)
            lo, hi = float(df["risk_score"].min()), float(df["risk_score"].max())
            score_range = m1.slider("Risk score", lo, hi, (lo, hi), 1.0, key="q_score")
            min_amount = m2.number_input("Minimum amount ($)", min_value=0.0, value=0.0, step=1000.0, key="q_amount")
            sort = m3.selectbox("Sort by", ["Priority (recommended)", "Risk score", "Amount", "Newest first"], key="q_sort")

    q = df
    if tiers:
        q = q[q["priority"].isin(tiers)]
    if a_type != "All alert types":
        q = q[q["alert_type"].astype(str) == a_type]
    if status_filter != "Any status":
        q = q[q["alert_id"].map(status_of) == status_filter]
    q = q[q["risk_score"].between(*score_range)]
    if min_amount:
        q = q[q["transaction_amount"].fillna(0) >= min_amount]
    if search.strip():
        s = search.strip().lower()
        mask = pd.Series(False, index=q.index)
        for col in ["alert_id", "customer_id", "transaction_id"]:
            if col in q:
                mask |= q[col].astype(str).str.lower().str.contains(s, regex=False)
        q = q[mask]
    if sort == "Risk score":
        q = q.sort_values("risk_score", ascending=False)
    elif sort == "Amount":
        q = q.sort_values("transaction_amount", ascending=False)
    elif sort == "Newest first":
        q = q.sort_values("alert_timestamp", ascending=False)

    st.session_state.queue_ids = q["alert_id"].tolist()
    counts = q["priority"].value_counts()
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        stat("In this view", f"{len(q):,}", f"of {len(df):,} alerts", 100 * len(q) / len(df))
    with s2:
        stat("P1 critical", f"{counts.get('P1', 0):,}", "review first",
             100 * counts.get("P1", 0) / max(1, len(q)), visuals.TIER_COLORS["P1"])
    with s3:
        stat("P2 high", f"{counts.get('P2', 0):,}", "elevated queue",
             100 * counts.get("P2", 0) / max(1, len(q)), visuals.TIER_COLORS["P2"])
    with s4:
        stat("Exposure", money(q["transaction_amount"].sum(), 0), "sum of alerted amounts")
    st.write("")

    if q.empty:
        st.info("No alerts match these filters. Add P3 to the priority filter or clear the search.")
        return

    limit = 1000
    view = q.head(limit)
    table = pd.DataFrame({
        "Alert": view["alert_id"].values,
        "Priority": view["priority"].map(lambda t: f"{t} · {visuals.TIER_LABELS.get(t, '')}").values,
        "Risk score": view["risk_score"].values,
        "ML probability": view["ml_probability"].values,
        "Alert type": view["alert_type"].map(human).values,
        "Customer": view["customer_id"].values,
        "Amount": view["transaction_amount"].values,
        "Raised": pd.to_datetime(view["alert_timestamp"], errors="coerce").values,
        "Status": view["alert_id"].map(status_of).values,
        "Assignee": view["alert_id"].map(lambda a: st.session_state.assigned_to.get(a, "Unassigned")).values,
    })
    st.dataframe(
        table, hide_index=True, width="stretch", height=540, key="queue_table",
        on_select=on_queue_select, selection_mode="single-row",
        column_config={
            "Risk score": st.column_config.ProgressColumn("Risk score", min_value=0, max_value=100, format="%.0f"),
            "ML probability": st.column_config.ProgressColumn("ML probability", min_value=0, max_value=1, format="percent"),
            "Amount": st.column_config.NumberColumn("Amount", format="dollar"),
            "Raised": st.column_config.DatetimeColumn("Raised", format="MMM D, YYYY HH:mm"),
            "Alert type": st.column_config.TextColumn("Alert type", width="medium"),
        },
    )
    c1, c2 = st.columns([3, 1], vertical_alignment="center")
    c1.caption(f"Showing {len(view):,} of {len(q):,} alerts"
               + (" (first 1,000; narrow the filters to see the rest)." if len(q) > limit else ".")
               + " Select a row to open it; Previous/Next on the case page follow this order.")
    c2.download_button("Export view as CSV",
                       q.drop(columns=["investigation_outcome"], errors="ignore").to_csv(index=False).encode(),
                       file_name="aml_work_queue.csv", mime="text/csv", width="stretch")


# =====================================================================
# PAGE: CASE
# =====================================================================

_SHAP_RE = re.compile(r"(?:num|cat)__([\w ]+?)=([-\d.eE]+) \(SHAP ([+-][\d.eE]+)\)")


def render_case():
    ids = st.session_state.get("queue_ids") or df["alert_id"].tolist()
    alert_id = st.session_state.selected_alert
    if alert_id not in ALERT_INDEX:
        alert_id = ids[0] if ids else df["alert_id"].iloc[0]
        st.session_state.selected_alert = alert_id
    row = df.iloc[ALERT_INDEX[alert_id]]
    pos = ids.index(alert_id) + 1 if alert_id in ids else None

    n1, n2, n3, n4 = st.columns([1.3, 1, 1, 3], vertical_alignment="bottom")
    n1.button("← Back to queue", width="stretch", on_click=go, args=("Work queue",))
    n2.button("‹ Previous", width="stretch", on_click=step_case, args=(-1,), disabled=pos in (None, 1))
    n3.button("Next ›", width="stretch", on_click=step_case, args=(1,), disabled=pos is None or pos >= len(ids))
    with n4.form("jump_form", border=False, clear_on_submit=True):
        j1, j2 = st.columns([3, 1], vertical_alignment="bottom")
        target = j1.text_input("Jump to alert", placeholder="Go to alert ID, e.g. A003809", label_visibility="collapsed")
        if j2.form_submit_button("Go", width="stretch") and target.strip():
            target = target.strip().upper()
            if target in ALERT_INDEX:
                st.session_state.selected_alert = target
                st.rerun()
            st.toast(f"No alert called {target}", icon="⚠️")

    status = status_of(alert_id)
    queue_note = f"Case {pos:,} of {len(ids):,} in your queue" if pos else "Not in the current queue view"
    st.markdown(
        f'''<div class="case-head">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
          <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap"><span class="case-id">{html.escape(alert_id)}</span>
          {tier_badge(row["priority"])}<span class="status">{html.escape(status)}</span></div>
          <span class="note">{queue_note}</span></div>
        <div class="facts">
          <div class="fact"><div class="k">Customer</div><div class="v">{html.escape(str(row.get("customer_id")))} · {human(row.get("customer_type"))}</div></div>
          <div class="fact"><div class="k">Amount</div><div class="v">{money(row.get("transaction_amount"))}</div></div>
          <div class="fact"><div class="k">Alert type</div><div class="v">{human(row.get("alert_type"))}</div></div>
          <div class="fact"><div class="k">Raised</div><div class="v">{when(row.get("alert_timestamp"))}</div></div>
          <div class="fact"><div class="k">Transaction</div><div class="v">{html.escape(str(row.get("transaction_id")))}</div></div>
        </div></div>''',
        unsafe_allow_html=True,
    )
    st.write("")

    main, side = st.columns([1.75, 1], gap="large")
    with main:
        signals = [
            ("ML probability", fnum(row, "ml_probability") * 100, pct(row.get("ml_probability"))),
            ("Behavioral risk", fnum(row, "behavioral_risk") * 100, num(row.get("behavioral_risk"), 2)),
            ("Amount deviation", fnum(row, "amount_deviation_signal"), num(row.get("amount_deviation_signal"))),
            ("Recent activity", fnum(row, "recent_activity_signal"), num(row.get("recent_activity_signal"))),
            ("Velocity", fnum(row, "velocity_signal"), num(row.get("velocity_signal"))),
            ("Counterparties", fnum(row, "counterparty_signal"), num(row.get("counterparty_signal"))),
        ]
        st.iframe(visuals.risk_gauge(alert_id, fnum(row, "risk_score"), row["priority"], SCORE_THRESHOLDS, signals), height=274)

        with st.container(border=True):
            st.markdown("### Why this alert was flagged")
            behaviour = [r.strip() for r in str(row.get("behavioral_explanation", "")).split(";")
                         if r.strip() and r.strip().lower() != "nan"]
            if behaviour:
                st.markdown("".join(f'<div class="reason"><i>{i}</i><span>{html.escape(r[:1].upper() + r[1:])}</span></div>'
                                    for i, r in enumerate(behaviour, 1)), unsafe_allow_html=True)
            else:
                st.caption("No behavioral reasons were recorded for this alert.")
            drivers = _SHAP_RE.findall(str(row.get("shap_top_features", "")))
            if drivers:
                st.markdown('<div class="note" style="margin-top:12px">Top model drivers (SHAP): how far each feature '
                            "moved this alert's model score up or down.</div>", unsafe_allow_html=True)
                frame = pd.DataFrame([{"feature": feature_name(f), "shap": float(s)} for f, _, s in drivers])
                frame = frame.sort_values("shap", key=abs, ascending=False)
                frame["direction"] = frame["shap"].map(lambda v: "raises risk" if v > 0 else "lowers risk")
                chart = alt.Chart(frame).mark_bar(cornerRadiusEnd=4).encode(
                    y=alt.Y("feature:N", sort=frame["feature"].tolist(), title=None, axis=alt.Axis(labelLimit=260)),
                    x=alt.X("shap:Q", title="SHAP contribution"),
                    color=alt.Color("direction:N", scale=alt.Scale(domain=["raises risk", "lowers risk"],
                                                                  range=["#ff6b81", "#38bdf8"]), title=None),
                    tooltip=["feature", alt.Tooltip("shap:Q", format="+.3f"), "direction"])
                st.altair_chart(style_chart(chart, 48 * len(frame) + 110), width="stretch")

        with st.container(border=True):
            st.markdown("### Customer activity")
            tx = load_transactions(str(TX_PATH), mtime(TX_PATH))
            cust = str(row.get("customer_id"))
            hist = None if tx is None else tx[tx["customer_id"] == cust].sort_values("timestamp")
            if hist is None or hist.empty:
                st.caption("No transaction history is available for this customer in this deployment.")
            else:
                alert_ts = pd.to_datetime(row.get("alert_timestamp"), errors="coerce")
                is_alert = hist["transaction_id"].astype(str) == str(row.get("transaction_id"))
                phase = pd.Series("After alert", index=hist.index)
                if pd.notna(alert_ts):
                    phase[hist["timestamp"] < alert_ts] = "Before alert"
                phase[is_alert] = "This alert"
                hist = hist.assign(phase=phase, amount_plot=hist["amount"].clip(lower=1))
                pts = alt.Chart(hist).mark_circle(opacity=.85).encode(
                    x=alt.X("timestamp:T", title=None),
                    y=alt.Y("amount_plot:Q", title="Amount ($, log scale)", scale=alt.Scale(type="log")),
                    color=alt.Color("phase:N", scale=alt.Scale(domain=["Before alert", "This alert", "After alert"],
                                                               range=["#38bdf8", "#ff4d6d", "#475569"]), title=None),
                    size=alt.condition(alt.datum.phase == "This alert", alt.value(180), alt.value(26)),
                    tooltip=[alt.Tooltip("timestamp:T", title="Date", format="%b %d %Y %H:%M"),
                             alt.Tooltip("amount:Q", format="$,.2f"), "transaction_type", "direction", "country",
                             "counterparty_id"])
                st.altair_chart(style_chart(pts, 210), width="stretch")
                before = hist[hist["timestamp"] <= alert_ts] if pd.notna(alert_ts) else hist
                recent = before.tail(8).iloc[::-1]
                st.dataframe(pd.DataFrame({
                    "Date": recent["timestamp"].values, "Amount": recent["amount"].values,
                    "Type": recent["transaction_type"].map(human).values, "Direction": recent["direction"].map(human).values,
                    "Country": recent["country"].values, "Counterparty": recent["counterparty_id"].values,
                }), hide_index=True, width="stretch", column_config={
                    "Date": st.column_config.DatetimeColumn(format="MMM D, YYYY HH:mm"),
                    "Amount": st.column_config.NumberColumn(format="dollar")})
                st.caption(f"{len(hist):,} transactions on file for {cust}; the 8 most recent up to this alert are listed.")

    with side:
        with st.container(border=True):
            st.markdown("### Case actions")
            st.selectbox("Status", STATUSES, index=STATUSES.index(status), key=f"st_{alert_id}")
            st.selectbox("Assignee", ASSIGNEES, key=f"as_{alert_id}",
                         index=ASSIGNEES.index(st.session_state.assigned_to.get(alert_id, "Unassigned")))
            st.text_area("Investigator notes", value=st.session_state.case_notes.get(alert_id, ""), height=110,
                         placeholder="Evidence reviewed, rationale, next steps…", key=f"nt_{alert_id}")
            b1, b2 = st.columns(2)
            b1.button("Save", type="primary", width="stretch", key=f"sv_{alert_id}", on_click=save_case, args=(alert_id,))
            b2.button("Save & next ›", width="stretch", key=f"sn_{alert_id}", on_click=save_case, args=(alert_id, True),
                      disabled=pos is None or pos >= len(ids))
            log = st.session_state.case_log.get(alert_id, [])
            if log:
                st.markdown('<div class="note" style="margin-top:8px">Activity this session</div>'
                            + "".join(f'<div class="note">• {html.escape(x)}</div>' for x in reversed(log[-5:])),
                            unsafe_allow_html=True)
            st.caption("Demo workflow: changes are kept for this browser session only.")

        with st.container(border=True):
            st.markdown("### Customer profile")
            facts = [
                ("Customer type", human(row.get("customer_type"))),
                ("Country", str(row.get("customer_country", "—"))),
                ("Declared risk profile", human(row.get("risk_profile"))),
                ("Account age", f"{num(row.get('account_age_days'))} days"),
                ("Monthly income", money(row.get("monthly_income"), 0)),
                ("Transactions before alert", num(row.get("prior_transaction_count"))),
                ("Average prior amount", money(row.get("prior_avg_transaction_amount"))),
                ("Unique counterparties", num(row.get("unique_counterparties"))),
                ("Transactions, last 7 days", num(row.get("transactions_last_7_days"))),
            ]
            st.markdown("".join(f'<div class="kv"><span>{k}</span><span>{html.escape(v)}</span></div>' for k, v in facts),
                        unsafe_allow_html=True)
            others = df[(df["customer_id"] == row.get("customer_id")) & (df["alert_id"] != alert_id)]
            if len(others):
                st.markdown(f'<div class="note" style="margin:12px 0 6px">{len(others):,} other alerts for this customer · '
                            f'{int(others["priority"].isin(["P1", "P2"]).sum()):,} are P1/P2</div>', unsafe_allow_html=True)
                for _, o in others.head(4).iterrows():
                    st.button(f"{o['alert_id']} · {o['priority']} · score {num(o['risk_score'])}", key=f"oth_{o['alert_id']}",
                              on_click=open_case, args=(o["alert_id"],), width="stretch")

        with st.expander("Evaluation label (synthetic)"):
            st.caption("The synthetic dataset records how this alert was resolved. An investigator would not see this "
                       "on an open alert; it is shown only so the demo can be checked.")
            st.markdown(f"**Recorded outcome:** {human(row.get('investigation_outcome'))}")
        with st.expander("All fields"):
            raw = row.drop(labels=["investigation_outcome"], errors="ignore").map(
                lambda v: "—" if pd.isna(v) else str(v)).to_frame("value")
            st.dataframe(raw, width="stretch", height=320)
            st.download_button("Download case JSON", json.dumps(row.to_dict(), default=str, indent=2),
                               file_name=f"{alert_id}.json", mime="application/json", width="stretch")


# =====================================================================
# PAGE: INSIGHTS
# =====================================================================

def render_insights():
    page_header("Insights", "How risk is distributed across the alert population and what separates urgent alerts.")
    st.iframe(visuals.risk_explorer(cached_explorer(DATA_VERSION)), height=602)
    st.caption("Each point is an alert, placed by ML probability, behavioral risk and transaction amount. Every P1/P2 "
               "alert is plotted plus a sample of the rest. Drag to rotate, scroll to zoom, hover a point for details.")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(border=True):
            st.markdown("### Average risk by alert type")
            by_type = df.groupby("alert_type")["risk_score"].mean().sort_values(ascending=False).head(8)
            by_type.index = by_type.index.map(human)
            bar_chart(by_type, "Average risk score", color="#ff9f43", height=250, fmt=".1f")
    with c2:
        with st.container(border=True):
            st.markdown("### Alert volume by type")
            vol = df["alert_type"].value_counts().head(8)
            vol.index = vol.index.map(human)
            bar_chart(vol, "Alerts", color="#38bdf8", height=250, labels=True)

    c3, c4 = st.columns(2, gap="large")
    with c3:
        with st.container(border=True):
            st.markdown("### Average alerted amount by tier")
            frame = df.groupby("priority")["transaction_amount"].mean().reindex(visuals.TIER_ORDER).dropna().rename("value").reset_index()
            chart = alt.Chart(frame).mark_bar(cornerRadiusEnd=5).encode(
                x=alt.X("priority:N", sort=visuals.TIER_ORDER, title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("value:Q", title="Average amount ($)"),
                color=alt.Color("priority:N", scale=TIER_SCALE, legend=None),
                tooltip=["priority", alt.Tooltip("value:Q", title="Average amount", format="$,.0f")])
            st.altair_chart(style_chart(chart, 240), width="stretch")
    with c4:
        with st.container(border=True):
            st.markdown("### Priority mix by customer type")
            ct = df.groupby(["customer_type", "priority"]).size().rename("alerts").reset_index()
            ct["customer_type"] = ct["customer_type"].map(human)
            chart = alt.Chart(ct).mark_bar().encode(
                y=alt.Y("customer_type:N", title=None, axis=alt.Axis(labelOverlap=False)),
                x=alt.X("alerts:Q", title="Share of alerts", stack="normalize", axis=alt.Axis(format="%")),
                color=alt.Color("priority:N", scale=TIER_SCALE, title=None, sort=visuals.TIER_ORDER),
                order=alt.Order("priority:N"),
                tooltip=["customer_type", "priority", alt.Tooltip("alerts:Q", format=",")])
            st.altair_chart(style_chart(chart, 240), width="stretch")


# =====================================================================
# PAGE: MODEL
# =====================================================================

def render_model():
    page_header("Model", "How scores are produced, how well they hold up on unseen customers, and what drives them.")
    st.iframe(visuals.pipeline_flow([
        ("Customers", "synthetic profiles"), ("Transactions", "seeded generator"), ("Rule alerts", "monitoring rules"),
        ("Features", "pre-alert only"), ("Models", "LR + random forest"), ("Risk tiers", "shared P1–P4"),
        ("SHAP", "explanations"), ("Queue", "API + dashboard"),
    ]), height=132)

    results = METRICS.get("results", {})
    names = {"logistic_regression": "Logistic regression", "random_forest": "Random forest"}
    if results:
        cols = st.columns(2 * len(results))
        for i, (key, m) in enumerate(results.items()):
            with cols[2 * i]:
                stat(f"{names.get(key, key)} · PR-AUC", f"{m.get('pr_auc', 0):.3f}", f"ROC-AUC {m.get('roc_auc', 0):.3f}")
            with cols[2 * i + 1]:
                stat(f"{names.get(key, key)} · precision", pct(m.get("precision", 0)), f"recall {pct(m.get('recall', 0))}")
        st.caption(f"Held-out evaluation on customers the model never saw: {METRICS.get('train_rows', 0):,} training "
                   f"alerts, {METRICS.get('test_rows', 0):,} test alerts, {METRICS.get('customer_overlap', 0)} customers in both.")

    c1, c2 = st.columns([1, 1.2], gap="large")
    with c1:
        tiers = RISK_SUMMARY.get("heldout_tier_metrics", {})
        if tiers:
            with st.container(border=True):
                st.markdown("### How often each tier was right")
                frame = pd.DataFrame([{"tier": t, "precision": v.get("precision", 0), "alerts": v.get("alerts", 0)}
                                      for t, v in tiers.items()])
                chart = alt.Chart(frame).mark_bar(cornerRadiusEnd=6, height=24).encode(
                    y=alt.Y("tier:N", sort=visuals.TIER_ORDER, title=None),
                    x=alt.X("precision:Q", title="Share truly suspicious (held-out)", axis=alt.Axis(format="%"),
                            scale=alt.Scale(domain=[0, 1])),
                    color=alt.Color("tier:N", scale=TIER_SCALE, legend=None),
                    tooltip=["tier", alt.Tooltip("precision:Q", format=".1%"), alt.Tooltip("alerts:Q", format=",")])
                label = chart.mark_text(align="left", dx=6, color="#cbd5e1").encode(text=alt.Text("precision:Q", format=".0%"))
                st.altair_chart(style_chart(chart + label, 200), width="stretch")
                st.caption("Ground truth is the synthetic `is_suspicious` flag, which the model never sees in training.")
    with c2:
        if XAI_PATH.exists():
            with st.container(border=True):
                st.markdown("### What drives the model overall")
                xai = pd.read_csv(XAI_PATH)
                numeric = [c for c in xai.columns if pd.api.types.is_numeric_dtype(xai[c])]
                if numeric:
                    imp = xai.sort_values(numeric[-1], ascending=False).head(10).set_index(xai.columns[0])[numeric[-1]]
                    imp.index = imp.index.map(feature_name)
                    bar_chart(imp, "Mean |SHAP|", height=290, fmt=".4f")

    with st.expander("Data quality and pipeline artifacts"):
        q1, q2, q3, q4 = st.columns(4)
        with q1:
            stat("Rows", f"{len(df):,}")
        with q2:
            stat("Columns", f"{df.shape[1]:,}")
        with q3:
            stat("Missing cells", f"{int(df.isna().sum().sum()):,}")
        with q4:
            stat("Duplicate alert IDs", f"{int(df['alert_id'].duplicated().sum()):,}")
        quality = pd.DataFrame({"Type": df.dtypes.astype(str), "Missing %": (df.isna().mean() * 100).round(2),
                                "Unique values": df.nunique(dropna=True)}).sort_values("Missing %", ascending=False)
        st.dataframe(quality, width="stretch", height=300)
        files = [("Prioritized queue", DATA_PATH), ("Transactions", TX_PATH), ("Model metrics", METRICS_PATH),
                 ("Feature importance", XAI_PATH), ("XAI summary", XAI_SUMMARY_PATH)]
        st.dataframe(pd.DataFrame({"Artifact": [f[0] for f in files], "Available": [f[1].exists() for f in files],
                                   "Path": [display_path(f[1]) for f in files]}), hide_index=True, width="stretch")


# =====================================================================
# ROUTER + FOOTER
# =====================================================================

{"Overview": render_overview, "Work queue": render_queue, "Case": render_case,
 "Insights": render_insights, "Model": render_model}[page]()

st.markdown(
    '<div class="note" style="margin-top:28px;border-top:1px solid var(--line);padding-top:12px">'
    "AML Alert Triage · synthetic data for demonstration · scores support, and never replace, human investigation "
    "under your compliance procedures.</div>",
    unsafe_allow_html=True,
)
