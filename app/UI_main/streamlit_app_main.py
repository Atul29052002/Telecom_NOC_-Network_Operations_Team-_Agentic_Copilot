from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents import run_workflow
from app.engine import load_or_stream_alarm_logs, run_root_cause_engine
from app.data_generation import build_demo_assets


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
APP_DIR = Path(__file__).resolve().parent.parent / "app"
ALARM_PATH = DATA_DIR / "alarm_logs.csv"
STATE_PATH = DATA_DIR / "telecom_state.json"
PAGE_1_PATH = APP_DIR / "01_Telecom_dashboard.py"
PAGE_2_PATH = APP_DIR / "02_Root_cause_dashboard.py"


with st.sidebar:
    st.write('**Telecom Network RCA and Remediation Copilot**')


pages = [
    st.Page(page = PAGE_1_PATH, title = 'Telecom Network Dashboard'),#, icon = ''),
    st.Page(page = PAGE_2_PATH, title = 'Root Cause Dashboard')#, icon = '')
]

pg = st.navigation(pages, position = 'sidebar', expanded = True)

pg.run()

# st.set_page_config(page_title="Telecom NOC Command Center", page_icon="📡", layout="wide")


# @st.cache_data(show_spinner=False)
# def load_state() -> dict[str, Any]:
#     if STATE_PATH.exists():
#         return json.loads(STATE_PATH.read_text(encoding="utf-8"))
#     return {}


# def save_state(state: dict[str, Any]) -> None:
#     STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


# def ensure_assets() -> None:
#     if not ALARM_PATH.exists():
#         build_demo_assets(str(DATA_DIR))


# ensure_assets()
# state = load_state()

# if "workflow_result" not in state:
#     state["workflow_result"] = {}

# st.markdown("# Modern Telecom NOC Command Center")
# st.markdown("Dark theme operational overview for telecom incident response")

# with st.sidebar:
#     st.header("Navigation")
#     page = st.radio("Go to", [
#         "Live Alarm Dashboard",
#         "Alarm Heatmap",
#         "Root Cause Graph",
#         "Agent Reasoning Panel",
#         "Remediation Recommendation",
#         "Human Approval Console",
#         "MCP Execution Status",
#         "ITSM Tickets",
#     ])

#     if st.button("Run Analysis"):
#         engine_output = run_root_cause_engine(str(ALARM_PATH), output_dir=str(DATA_DIR))
#         workflow_result = run_workflow(str(ALARM_PATH), approval="Approve")
#         state["engine_output"] = engine_output
#         state["workflow_result"] = workflow_result
#         save_state(state)
#         st.success("Analysis completed")

# if page == "Live Alarm Dashboard":
#     alarms = load_or_stream_alarm_logs(ALARM_PATH)
#     active_alarms = len(alarms)
#     critical_alarms = int((alarms["severity"] == "Critical").sum())
#     kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
#     kpi1.metric("Active Alarms", active_alarms)
#     kpi2.metric("Critical Alarms", critical_alarms)
#     kpi3.metric("Root Causes Detected", len(state.get("engine_output", {}).get("top_candidates", [])))
#     kpi4.metric("Auto Resolutions", len(state.get("workflow_result", {}).get("execution_status", {}).keys()) if isinstance(state.get("workflow_result", {}).get("execution_status", {}), dict) else 0)
#     kpi5.metric("SLA Risk", "High" if critical_alarms > 0 else "Low")

#     st.subheader("Latest alarms")
#     st.dataframe(alarms.tail(20)[["alarm_id", "alarm_name", "equipment_name", "severity", "alarm_raised_time"]], use_container_width=True)

# elif page == "Alarm Heatmap":
#     alarms = load_or_stream_alarm_logs(ALARM_PATH)
#     fig, ax = plt.subplots(figsize=(7, 5))
#     heatmap, xedges, yedges = np.histogram2d(alarms["longitude"], alarms["latitude"], bins=10)
#     im = ax.imshow(heatmap.T, origin="lower", extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]], cmap="hot")
#     fig.colorbar(im, ax=ax)
#     ax.set_title("Alarm Density Heatmap")
#     ax.set_xlabel("Longitude")
#     ax.set_ylabel("Latitude")
#     st.pyplot(fig)

# elif page == "Root Cause Graph":
#     st.image(str(DATA_DIR / "root_cause_subgraph.jpg"))

# elif page == "Agent Reasoning Panel":
#     root_output = state.get("workflow_result", {}).get("root_cause_output", {})
#     st.write(root_output if root_output else {"message": "No root cause output yet"})

# elif page == "Remediation Recommendation":
#     remediation = state.get("workflow_result", {}).get("remediation_output", {})
#     st.write(remediation if remediation else {"message": "No remediation recommendation yet"})

# elif page == "Human Approval Console":
#     decision = st.radio("Approval", ["Approve", "Reject", "Modify"], horizontal=True)
#     if st.button("Submit Approval"):
#         state["workflow_result"]["approval"] = decision
#         save_state(state)
#         st.success(f"Decision recorded: {decision}")

# elif page == "MCP Execution Status":
#     st.write(state.get("workflow_result", {}).get("execution_status", {"status": "No execution yet"}))

# elif page == "ITSM Tickets":
#     defect_log = DATA_DIR / "defect_log.csv"
#     if defect_log.exists():
#         st.dataframe(pd.read_csv(defect_log), use_container_width=True)
#     else:
#         st.info("No tickets created yet")
