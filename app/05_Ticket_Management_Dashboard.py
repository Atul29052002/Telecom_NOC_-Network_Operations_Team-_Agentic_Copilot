from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data"

st.markdown(
    """
    <style>
      .stApp { background-color: #0f172a; color: #f8fafc; }
      [data-testid="stMetricValue"] { color: #3b82f6; font-weight: 700; text-shadow: 0 0 10px rgba(59, 130, 246, 0.3); }
      [data-testid="stMetricLabel"] { color: #94a3b8 !important; }
      h1, h2, h3 { color: #f8fafc; font-weight: 700; }
      .stDataFrame { background-color: #1e293b; border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <h1 style="margin:0 0 0.25rem 0; color:#f8fafc;">🎫 Ticket Management</h1>
    <p style="margin:0; color:#94a3b8;">Track the incidents that have moved from RCA into the operational workflow.</p>
    """,
    unsafe_allow_html=True,
)

st.divider()
defect_log = DATA_DIR / "defect_log.csv"
if defect_log.exists():
    tickets = pd.read_csv(defect_log)
    c1, c2, c3 = st.columns(3)
    c1.metric("Open tickets", len(tickets))
    c2.metric("Resolved", int((tickets["status"] == "Resolved").sum()) if "status" in tickets.columns else 0)
    c3.metric("Pending", int((tickets["status"] == "Pending").sum()) if "status" in tickets.columns else 0)
    st.dataframe(tickets, use_container_width=True, hide_index=True)
else:
    st.info("No tickets created yet. Run the workflow and create a defect entry to populate this pane.")
