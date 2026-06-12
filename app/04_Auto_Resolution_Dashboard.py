from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data"
STATE_PATH = DATA_DIR / "telecom_state.json"

st.markdown(
    """
    <style>
      .stApp { background-color: #0f172a; color: #f8fafc; }
      [data-testid="stMetricValue"] { color: #3b82f6; font-weight: 700; text-shadow: 0 0 10px rgba(59, 130, 246, 0.3); }
      [data-testid="stMetricLabel"] { color: #94a3b8 !important; }
      h1, h2, h3 { color: #f8fafc; font-weight: 700; }
      .stTabs [data-baseweb="tab"] { color: #94a3b8; }
      .stTabs [aria-selected="true"] { color: #3b82f6 !important; }
      button[data-baseweb="tab"] { font-size: 1.1rem !important; font-weight: 600 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


state = load_state()
workflow_result = state.get("workflow_result", {})

st.markdown(
    """
    <h1 style="margin:0 0 0.25rem 0; color:#f8fafc;">✅ Auto Resolution Console</h1>
    <p style="margin:0; color:#94a3b8;">Approve, reject, or modify the workflow’s proposed remediation before execution.</p>
    """,
    unsafe_allow_html=True,
)

st.divider()
approval_tab, status_tab = st.tabs(["Approval", "Resolution status"])

with approval_tab:
    decision = st.radio("Choose an action", ["Approve", "Reject", "Modify"], horizontal=True)
    if st.button("Submit approval", type="primary"):
        workflow_result["approval"] = decision
        state["workflow_result"] = workflow_result
        STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
        st.success(f"Decision recorded: {decision}")

    # Initialize toggle state
    if "show_json_auto" not in st.session_state:
        st.session_state.show_json_auto = False

    if st.button("Toggle JSON/Text View"):
        st.session_state.show_json_auto = not st.session_state.show_json_auto

    rem_output = workflow_result.get("remediation_output", {})
    if st.session_state.show_json_auto:
        st.json(rem_output)
    else:
        if rem_output:
            for key, value in rem_output.items():
                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
        else:
            st.write("Recommended action: Review the remediation playbook first.")

with status_tab:
    st.subheader("Execution summary")
    if workflow_result.get("approval"):
        st.info(f"Current decision: {workflow_result['approval']}")
    else:
        st.info("No approval has been submitted yet.")
    st.write("The resolution workflow will proceed only after the human approval step is completed.")
