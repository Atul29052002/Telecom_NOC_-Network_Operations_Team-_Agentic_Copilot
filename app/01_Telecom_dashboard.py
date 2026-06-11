from __future__ import annotations

import json
import os
import sys
import time
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
ALARM_PATH = DATA_DIR / "alarm_logs.csv"
STATE_PATH = DATA_DIR / "telecom_state.json"

df = pd.read_csv(ALARM_PATH)
st.header('Telecom Network Dashboard')
df["alarm_raised_time"] = pd.to_datetime(df["alarm_raised_time"], format="%Y-%m-%d %H:%M:%S", errors="coerce")

WINDOW_SIZE = pd.Timedelta(minutes=1)
WINDOW_STEP = pd.Timedelta(minutes=1)
UPDATE_SECONDS = 1
CHART_BUCKETS = 10


def get_alarm_count_delta(alarms: pd.DataFrame, severity: str, now: pd.Timestamp) -> tuple[int, int]:
    current_window_start = now - WINDOW_SIZE
    previous_window_start = now - (WINDOW_SIZE * 2)

    severity_match = alarms["severity"].astype(str).str.casefold() == severity.casefold()
    current_window = alarms["alarm_raised_time"].between(current_window_start, now, inclusive="both")
    previous_window = alarms["alarm_raised_time"].between(previous_window_start, current_window_start, inclusive="left")

    current_count = int((severity_match & current_window).sum())
    previous_count = int((severity_match & previous_window).sum())
    return current_count, current_count - previous_count


def get_sliding_window_ends(alarms: pd.DataFrame) -> pd.DatetimeIndex:
    alarm_times = alarms["alarm_raised_time"].dropna()
    if alarm_times.empty:
        return pd.DatetimeIndex([])

    first_window_end = alarm_times.min().floor("min")
    last_window_end = alarm_times.max().floor("min")
    return pd.date_range(first_window_end, last_window_end, freq=WINDOW_STEP)


def build_total_alarm_chart(alarms: pd.DataFrame, current_time: pd.Timestamp) -> plt.Figure:
    current_minute = current_time.floor("min")
    chart_window_ends = pd.date_range(
        current_minute - (WINDOW_STEP * (CHART_BUCKETS - 1)),
        current_minute,
        freq=WINDOW_STEP,
    )
    totals = [
        int(alarms["alarm_raised_time"].between(window_end - WINDOW_SIZE, window_end, inclusive="both").sum())
        for window_end in chart_window_ends
    ]

    fig, ax = plt.subplots(figsize=(9, 3.5))
    colors = ["#4C78A8"] * (len(chart_window_ends) - 1) + ["#F58518"]
    ax.bar([window_end.strftime("%H:%M") for window_end in chart_window_ends], totals, color=colors)
    ax.set_title("Total alarms per minute")
    ax.set_xlabel("Window end time")
    ax.set_ylabel("Alarm count")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    return fig


def get_alarm_map_points(alarms: pd.DataFrame, current_time: pd.Timestamp) -> pd.DataFrame:
    window_start = current_time - WINDOW_SIZE
    current_window = alarms["alarm_raised_time"].between(window_start, current_time, inclusive="both")
    return alarms.loc[current_window, ["latitude", "longitude"]].dropna()

font_css = """
<style>
    button[data-baseweb="tab"] {
    font-size: 24px;
    margin: 0;
    width: 100%;
    }
</style>
"""
st.write(font_css, unsafe_allow_html=True)

tabs = st.tabs(['Network KPI', 'Alarm Logs'])

with tabs[1]:
    st.subheader('Alarm Logs')
    st.dataframe(df, use_container_width=True, hide_index = True)

with tabs[0]:
    st.subheader('Network KPI Dashboard')
    st.divider()
    col1, col2, col3 =st.columns(3)
    window_label = st.empty()
    
    with col1:
        place_critical = st.empty()
    with col2:
        place_major = st.empty()
    with col3:
        place_minor = st.empty()
    st.divider() 
    alarm_chart = st.empty()
    alarm_map = st.empty()
    
    window_ends = get_sliding_window_ends(df)
    if window_ends.empty:
        with place_critical:
            st.metric('**Critical Alarm count**', 0, delta=0, delta_color='inverse', help= 'Count of critical alarm in past 1 minute')
        with place_major:
            st.metric('**Major Alarm count**', 0, delta=0, delta_color='inverse', help= 'Count of major alarm in past 1 minute')
        with place_minor:
            st.metric('**Minor Alarm count**', 0, delta=0, delta_color='inverse', help= 'Count of minor alarm in past 1 minute')
        alarm_chart.info("No valid alarm timestamps available for the alarm count chart.")
        alarm_map.info("No valid alarm locations available for the alarm map.")
    else:
        while True:
            for current_time in window_ends:
                critical_count, critical_delta = get_alarm_count_delta(df, "Critical", current_time)
                major_count, major_delta = get_alarm_count_delta(df, "Major", current_time)
                minor_count, minor_delta = get_alarm_count_delta(df, "Minor", current_time)

                window_start = current_time - WINDOW_SIZE
               # window_label.caption(f"Showing alarm counts from {window_start:%Y-%m-%d %H:%M:%S} to {current_time:%Y-%m-%d %H:%M:%S}")
                
                with place_critical:
                    st.metric('**Critical Alarm count**', critical_count, delta=critical_delta, delta_color='inverse', help= 'Count of critical alarm in past 1 minute')
                with place_major:
                    st.metric('**Major Alarm count**', major_count, delta=major_delta, delta_color='inverse', help= 'Count of major alarm in past 1 minute')
                with place_minor:
                    st.metric('**Minor Alarm count**', minor_count, delta=minor_delta, delta_color='inverse', help= 'Count of minor alarm in past 1 minute')

                fig = build_total_alarm_chart(df, current_time)
                alarm_chart.pyplot(fig)
                plt.close(fig)

                map_points = get_alarm_map_points(df, current_time)
                if map_points.empty:
                    alarm_map.info("No alarm locations in the current 1-minute window.")
                else:
                    alarm_map.map(map_points, latitude="latitude", longitude="longitude")

                time.sleep(UPDATE_SECONDS)
           

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
