from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents import run_workflow
from app.engine import load_or_stream_alarm_logs, run_root_cause_engine
from app.data_generation import build_demo_assets


DATA_DIR = PROJECT_ROOT / "data"
ALARM_PATH = DATA_DIR / "alarm_logs.csv"
STATE_PATH = DATA_DIR / "telecom_state.json"
LOGO_DIR = PROJECT_ROOT / "app" / "logo"


st.set_page_config(page_title="Telecom NOC Command Center", page_icon="📡", layout="wide")

st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(135deg, #07111f 0%, #102a43 100%);
            color: #f7fafc;
        }
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
        }
        div[data-testid="stSidebar"] {
            background: #081120;
            border-right: 1px solid #20354f;
        }
        .stMetric {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 0.8rem;
        }
        h1, h2, h3 {
            color: #f8fbff;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def _make_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _make_json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_make_json_safe(item) for item in value]
    if hasattr(value, "to_dict"):
        return _make_json_safe(value.to_dict())
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(_make_json_safe(state), indent=2, default=str), encoding="utf-8")


def ensure_assets() -> None:
    if not ALARM_PATH.exists():
        build_demo_assets(str(DATA_DIR))


def _render_summary_cards(alarms: pd.DataFrame, state: dict[str, Any]) -> None:
    active_alarms = len(alarms)
    critical_alarms = int((alarms["severity"] == "Critical").sum())
    top_candidates = state.get("engine_output", {}).get("top_candidates", [])
    workflow_result = state.get("workflow_result", {})
    execution_status = workflow_result.get("execution_status", {})

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Active alarms", active_alarms, delta="Live")
    c2.metric("Critical alarms", critical_alarms, delta="Immediate")
    c3.metric("Root cause candidates", len(top_candidates))
    c4.metric("Auto actions", len(execution_status) if isinstance(execution_status, dict) else 0)
    c5.metric("SLA risk", "High" if critical_alarms > 0 else "Low")


ensure_assets()
state = load_state()
if "workflow_result" not in state:
    state["workflow_result"] = {}

st.title("📡 Telecom NOC Command Center")
st.caption("A polished, operator-friendly view of alarms, root cause intelligence, and remediation actions.")

with st.sidebar:
    # Primary Logo
    logo1 = LOGO_DIR / "logo1.png"
    if logo1.exists():
        st.image(str(logo1), use_container_width=True)

    st.header("Operations")
    st.caption("Run the analysis workflow and review the latest incident outcome.")
    page = st.radio(
        "Navigate",
        [
            "Live Alarm Dashboard",
            "Alarm Heatmap",
            "Root Cause Graph",
            "Agent Reasoning Panel",
            "Remediation Recommendation",
            "Human Approval Console",
            "MCP Execution Status",
            "ITSM Tickets",
        ],
        horizontal=False,
    )

    st.divider()
    if st.button("Run Analysis", use_container_width=True):
        engine_output = run_root_cause_engine(str(ALARM_PATH), output_dir=str(DATA_DIR))
        workflow_result = run_workflow(str(ALARM_PATH), approval="Approve")
        state["engine_output"] = engine_output
        state["workflow_result"] = workflow_result
        save_state(state)
        st.success("Analysis completed")
    
    # Secondary Logo
    logo2 = LOGO_DIR / "logo2.png"
    if logo2.exists():
        st.image(str(logo2), width=100)

if page == "Live Alarm Dashboard":
    alarms = load_or_stream_alarm_logs(ALARM_PATH)
    _render_summary_cards(alarms, state)

    st.subheader("Latest alarms")
    st.dataframe(
        alarms.tail(20)[["alarm_id", "alarm_name", "equipment_name", "severity", "alarm_raised_time"]],
        use_container_width=True,
        hide_index=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Severity distribution")
        severity_counts = alarms["severity"].value_counts().reindex(["Critical", "Major", "Minor"], fill_value=0)
        fig, ax = plt.subplots(figsize=(6, 4))
        severity_counts.plot(kind="bar", color=["#ff4b4b", "#ffb703", "#2ec4b6"], ax=ax)
        ax.set_title("Alarm Severity")
        ax.set_ylabel("Count")
        ax.set_xlabel("Severity")
        ax.grid(axis="y", linestyle="--", alpha=0.3)
        plt.tight_layout()
        st.pyplot(fig)

    with col_b:
        st.subheader("Incident snapshot")
        st.info(
            "The dashboard highlights active alarms, likely root causes, and remediation recommendations in one place."
        )
        if state.get("workflow_result"):
            if "show_json_home" not in st.session_state:
                st.session_state.show_json_home = False
            if st.button("Toggle JSON/Text View"):
                st.session_state.show_json_home = not st.session_state.show_json_home
            
            rc_output = state["workflow_result"].get("root_cause_output", {})
            if st.session_state.show_json_home:
                st.json(rc_output if rc_output else {"status": "No root cause yet"})
            else:
                for key, value in rc_output.items():
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")

elif page == "Alarm Heatmap":
    alarms = load_or_stream_alarm_logs(ALARM_PATH)
    fig, ax = plt.subplots(figsize=(8, 5))
    heatmap, xedges, yedges = np.histogram2d(alarms["longitude"], alarms["latitude"], bins=10)
    im = ax.imshow(heatmap.T, origin="lower", extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]], cmap="hot")
    fig.colorbar(im, ax=ax)
    ax.set_title("Alarm Density Heatmap")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    st.pyplot(fig)

elif page == "Root Cause Graph":
    graph_path = DATA_DIR / "root_cause_subgraph.jpg"
    if graph_path.exists():
        st.image(str(graph_path), caption="Root cause graph generated from the alarm topology")
    else:
        st.info("Run analysis to generate the root cause graph.")

elif page == "Agent Reasoning Panel":
    root_output = state.get("workflow_result", {}).get("root_cause_output", {})
    st.subheader("Root cause reasoning")
    if "show_json_reason" not in st.session_state:
        st.session_state.show_json_reason = False
    if st.button("Toggle JSON/Text View"):
        st.session_state.show_json_reason = not st.session_state.show_json_reason
    
    if st.session_state.show_json_reason:
        st.json(root_output if root_output else {"message": "No root cause output yet"})
    else:
        for key, value in root_output.items():
            st.write(f"**{key.replace('_', ' ').title()}:** {value}")

elif page == "Remediation Recommendation":
    remediation = state.get("workflow_result", {}).get("remediation_output", {})
    st.subheader("Recommended action")
    if "show_json_remedy" not in st.session_state:
        st.session_state.show_json_remedy = False
    if st.button("Toggle JSON/Text View"):
        st.session_state.show_json_remedy = not st.session_state.show_json_remedy

    if st.session_state.show_json_remedy:
        st.json(remediation if remediation else {"message": "No remediation recommendation yet"})
    else:
        for key, value in remediation.items():
            st.write(f"**{key.replace('_', ' ').title()}:** {value}")

elif page == "Human Approval Console":
    st.subheader("Approval workflow")
    decision = st.radio("Approval", ["Approve", "Reject", "Modify"], horizontal=True)
    if st.button("Submit Approval", use_container_width=True):
        state["workflow_result"]["approval"] = decision
        save_state(state)
        st.success(f"Decision recorded: {decision}")

elif page == "MCP Execution Status":
    st.subheader("Execution status")
    exec_status = state.get("workflow_result", {}).get("execution_status", {})
    if "show_json_mcp" not in st.session_state:
        st.session_state.show_json_mcp = False
    if st.button("Toggle JSON/Text View"):
        st.session_state.show_json_mcp = not st.session_state.show_json_mcp

    if st.session_state.show_json_mcp:
        st.json(exec_status if exec_status else {"status": "No execution yet"})
    else:
        for key, value in exec_status.items():
            st.write(f"**{key.replace('_', ' ').title()}:** {value}")

elif page == "ITSM Tickets":
    defect_log = DATA_DIR / "defect_log.csv"
    st.subheader("Incident tickets")
    if defect_log.exists():
        st.dataframe(pd.read_csv(defect_log), use_container_width=True, hide_index=True)
    else:
        st.info("No tickets created yet")
