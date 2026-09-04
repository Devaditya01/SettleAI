"""
Streamlit UI for the Settlement Intelligence Agent (SettleAI).
Phases 16 & 17: Sequence of Evidence View & Date-to-Transaction-ID Search.
"""

import sys
import os
import pandas as pd
import streamlit as st

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.loader import load_data
from src.tracer import trace_transaction
from src.journey import build_journey
from src.rules import apply_rules
from src.exceptions import evaluate_exceptions
from src.recommendations import get_recommendation

# ---------------------------------------------------------------------------
# Page Configuration & Styling
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SettleAI — Settlement Intelligence Agent",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern dark-mode aesthetics
st.markdown("""
<style>
    /* Dark Theme Core */
    .stApp {
        background-color: #11110f;
        color: #e6e6e6;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Headers & Typography */
    h1, h2, h3, h4 {
        color: #ffffff !important;
        font-weight: 600;
    }
    .brand-header {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 24px;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: #ffffff;
        margin-bottom: 4px;
    }
    .brand-mark {
        color: #d7c8ae;
        font-size: 28px;
    }
    .brand-sub {
        color: #888888;
        font-size: 14px;
        margin-bottom: 24px;
    }
    
    /* Metrics & Badge Cards */
    .metric-card {
        background: #191917;
        border: 1px solid #2a2a26;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 16px;
    }
    .metric-label {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #888888;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 22px;
        font-weight: 700;
        color: #ffffff;
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.03em;
    }
    .badge-settled { background-color: rgba(46, 204, 113, 0.15); color: #2ecc71; border: 1px solid #2ecc71; }
    .badge-failed { background-color: rgba(231, 76, 60, 0.15); color: #e74c3c; border: 1px solid #e74c3c; }
    .badge-processing { background-color: rgba(52, 152, 219, 0.15); color: #3498db; border: 1px solid #3498db; }
    .badge-at_risk { background-color: rgba(241, 196, 15, 0.15); color: #f1c40f; border: 1px solid #f1c40f; }
    .badge-delayed { background-color: rgba(230, 126, 34, 0.15); color: #e67e22; border: 1px solid #e67e22; }
    .badge-unresolved { background-color: rgba(155, 89, 182, 0.15); color: #9b59b6; border: 1px solid #9b59b6; }

    .badge-high { background-color: rgba(46, 204, 113, 0.15); color: #2ecc71; border: 1px solid #2ecc71; }
    .badge-medium { background-color: rgba(241, 196, 15, 0.15); color: #f1c40f; border: 1px solid #f1c40f; }
    .badge-low { background-color: rgba(231, 76, 60, 0.15); color: #e74c3c; border: 1px solid #e74c3c; }

    /* Timeline Hop Card */
    .hop-box {
        background: #161614;
        border-left: 3px solid #d7c8ae;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    .hop-title {
        font-weight: 600;
        color: #ffffff;
        font-size: 14px;
    }
    .hop-time {
        color: #d7c8ae;
        font-size: 13px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data Loading Cache
# ---------------------------------------------------------------------------
@st.cache_data
def get_cached_data():
    """Load dataset once and cache in memory."""
    return load_data("data")


try:
    data = get_cached_data()
except Exception as e:
    st.error(f"Failed to load dataset from `data/`: {e}")
    st.stop()


# ---------------------------------------------------------------------------
# Sidebar & Filters (Phase 17 Date Search & ID Selector)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="brand-header"><span class="brand-mark">✦</span> SettleAI</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">Predictive Settlement Intelligence</div>', unsafe_allow_html=True)
    st.divider()

    st.subheader("🔍 Investigation Search")
    
    search_mode = st.radio("Search By:", ["Date & Transaction List", "Direct Transaction ID"], index=0)
    
    selected_tx_id = None
    
    if search_mode == "Date & Transaction List":
        # Extract available dates from Gateway dataset
        gw_df = data["gateway"]
        if "gateway_timestamp" in gw_df.columns and not gw_df["gateway_timestamp"].isna().all():
            available_dates = sorted(
                gw_df["gateway_timestamp"].dropna().dt.strftime("%Y-%m-%d").unique().tolist(),
                reverse=True
            )
        else:
            available_dates = ["2026-09-04", "2026-09-03", "2026-09-02", "2026-09-01"]
        
        selected_date = st.selectbox("📅 Select Payment Date:", available_dates)
        
        # Filter transactions on selected date
        if "gateway_timestamp" in gw_df.columns:
            date_matches = gw_df[gw_df["gateway_timestamp"].dt.strftime("%Y-%m-%d") == selected_date]
        else:
            date_matches = gw_df
        
        tx_options = date_matches.index.tolist()
        st.info(f"Found **{len(tx_options)}** transactions on `{selected_date}`.")
        
        if tx_options:
            selected_tx_id = st.selectbox("💳 Select Transaction ID:", tx_options)
        else:
            st.warning("No transactions found for this date.")
            
    else:
        tx_input = st.text_input("Enter Transaction ID:", value="TXN000002")
        if tx_input:
            selected_tx_id = tx_input.strip()

    st.divider()
    st.subheader("⚡ Quick Demo Presets")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        if st.button("Normal (TXN000002)"):
            selected_tx_id = "TXN000002"
        if st.button("Missing Bank (TXN000020)"):
            selected_tx_id = "TXN000020"
        if st.button("Gateway Failure (TXN000048)"):
            selected_tx_id = "TXN000048"
    with col_p2:
        if st.button("Bank Delay (TXN000001)"):
            selected_tx_id = "TXN000001"
        if st.button("Mismatch (TXN000035)"):
            selected_tx_id = "TXN000035"
        if st.button("Ledger Delay (TXN000070)"):
            selected_tx_id = "TXN000070"


# ---------------------------------------------------------------------------
# Main Screen — Phase 16 Sequence of Evidence
# ---------------------------------------------------------------------------
st.title("Settlement Intelligence Dashboard")
st.caption("Evidence-grounded, multi-system transaction tracing & root-cause diagnosis.")

if not selected_tx_id:
    st.info("Please select or enter a Transaction ID to begin analysis.")
    st.stop()

# Run Pipeline
trace = trace_transaction(selected_tx_id, data)
journey = build_journey(trace)
rules_res = apply_rules(journey, trace)
exceptions_res = evaluate_exceptions(journey, trace, rules_res)
recommendation = get_recommendation(rules_res["root_cause"])

# Status & Confidence Badge classes
status = rules_res["status"]
confidence = exceptions_res["evidence_confidence"]
status_badge_class = f"badge-{status.lower()}"
conf_badge_class = f"badge-{confidence.lower()}"

# Header Row Metrics
m_col1, m_col2, m_col3, m_col4 = st.columns(4)

gw_data = trace.get("gateway") or {}
amount = gw_data.get("amount", "N/A")
pm = gw_data.get("payment_method", "N/A")

with m_col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Transaction ID</div>
        <div class="metric-value">{selected_tx_id}</div>
    </div>
    """, unsafe_allow_html=True)

with m_col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Amount & Method</div>
        <div class="metric-value">₹{amount} <span style="font-size:14px; font-weight:normal; color:#888;">({pm})</span></div>
    </div>
    """, unsafe_allow_html=True)

with m_col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Product Status</div>
        <div style="margin-top:6px;"><span class="badge {status_badge_class}">{status}</span></div>
    </div>
    """, unsafe_allow_html=True)

with m_col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Evidence Confidence</div>
        <div style="margin-top:6px;"><span class="badge {conf_badge_class}">{confidence} CONFIDENCE</span></div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# Diagnostic & Recommendation Card
diag_col, rec_col = st.columns([1, 1])

with diag_col:
    st.subheader("📌 Root Cause Diagnosis")
    st.markdown(f"**Diagnosed Cause**: `{rules_res['root_cause']}`")
    
    if exceptions_res["exceptions"]:
        st.warning(f"**Detected Exceptions**: {', '.join(exceptions_res['exceptions'])}")
    else:
        st.success("No critical data anomalies or record missing flags.")

with rec_col:
    st.subheader("💡 Recommended Action")
    st.markdown(f"**Action**: `{recommendation['action']}`")
    st.markdown(f"**{recommendation['title']}**: {recommendation['description']}")

st.divider()

# Sequence of Evidence (Timeline / Hops)
st.subheader("⏱️ Sequence of Evidence (Hop-by-Hop Journey)")

h_col1, h_col2, h_col3, h_col4 = st.columns(4)

with h_col1:
    h1 = journey.get("gateway_to_bank_minutes")
    h1_str = f"{h1} min" if h1 is not None else "N/A"
    st.markdown(f"""
    <div class="hop-box">
        <div class="hop-title">Hop 1: Gateway → Bank</div>
        <div class="hop-time">{h1_str}</div>
    </div>
    """, unsafe_allow_html=True)

with h_col2:
    h2 = journey.get("bank_processing_minutes")
    h2_str = f"{h2} min" if h2 is not None else "N/A"
    st.markdown(f"""
    <div class="hop-box">
        <div class="hop-title">Hop 2: Bank Processing</div>
        <div class="hop-time">{h2_str}</div>
    </div>
    """, unsafe_allow_html=True)

with h_col3:
    h3 = journey.get("bank_to_ledger_minutes")
    h3_str = f"{h3} min" if h3 is not None else "N/A"
    st.markdown(f"""
    <div class="hop-box">
        <div class="hop-title">Hop 3: Bank → Ledger</div>
        <div class="hop-time">{h3_str}</div>
    </div>
    """, unsafe_allow_html=True)

with h_col4:
    tot = journey.get("total_elapsed_minutes")
    tot_str = f"{tot} min" if tot is not None else "N/A"
    st.markdown(f"""
    <div class="hop-box" style="border-left-color: #3498db;">
        <div class="hop-title">Total Latency (SLA 30m)</div>
        <div class="hop-time">{tot_str}</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# Tabbed Raw Evidence Audit
st.subheader("📂 Verified System Records")
tab_gw, tab_bank, tab_ledger, tab_audit = st.tabs(["Gateway Record", "Bank Record", "Ledger Record", "Exceptions Audit"])

with tab_gw:
    if trace["gateway"]:
        st.json(trace["gateway"])
    else:
        st.warning("No record found in Gateway system.")

with tab_bank:
    if trace["bank"]:
        st.json(trace["bank"])
    else:
        st.warning("No record found in Bank system.")

with tab_ledger:
    if trace["ledger"]:
        st.json(trace["ledger"])
    else:
        st.warning("No record found in Ledger system.")

with tab_audit:
    st.write("**Exception Flags Detected**:", exceptions_res["exceptions"])
    st.write("**Confidence Level**:", exceptions_res["evidence_confidence"])
    st.write("**Journey Metrics Dict**:", journey)
