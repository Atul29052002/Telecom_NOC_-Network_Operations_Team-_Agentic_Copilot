from __future__ import annotations

import base64
import sys
import time
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents import (
    create_ticket,
    human_approval,
    issue_classifier,
    remediation_agent,
    root_cause_agent,
)
from app.noc_ui import (
    kpi_card,
    page_header,
    report_card,
    section_header,
    timeline,
)


DATA_DIR = PROJECT_ROOT / "data"
ALARM_PATH = DATA_DIR / "alarm_logs.csv"
NT_PATH = DATA_DIR / "network_topology.jpg"
AC_PATH = DATA_DIR / "root_cause_subgraph.jpg"
SOLM_PATH = DATA_DIR / "solution_manual.pdf"


page_header(
    "Remediation & Intelligence",
    "Evidence-based recovery recommendations, playbooks, and operational next actions.",
    "AI Operations",
)

rem_output = st.session_state.get("remediation_output", {})
issue_class = st.session_state.get("remediation_issue_class", "")
confidence = int(float(rem_output.get("confidence", 0)) * 100)

summary_cols = st.columns(4)
with summary_cols[0]:
    kpi_card(
        "Incident severity",
        issue_class or "Pending",
        "Classifier output",
        "danger" if issue_class == "MAJOR" else "primary",
        "!",
    )
with summary_cols[1]:
    kpi_card(
        "Root cause",
        rem_output.get("root_cause", "Pending"),
        "RCA handoff",
        "warning",
        "◆",
    )
with summary_cols[2]:
    kpi_card(
        "AI confidence",
        f"{confidence}%",
        "Recommendation confidence",
        "success",
        "%",
    )
with summary_cols[3]:
    kpi_card(
        "Knowledge source",
        "RAG",
        "Solution manual indexed",
        "primary",
        "K",
    )

recommendation_tab, evidence_tab, knowledge_tab = st.tabs(
    ["Recommendation Center", "Evidence & History", "Knowledge Base"]
)

with recommendation_tab:
    with st.container(border=True):
        section_header("Analysis Workflow", "RCA → RAG → classification → routing")
        if st.button(
            "Execute Analysis Workflow",
            type="primary",
            width="stretch",
        ):
            with st.status("Initializing Agentic Workflow...", expanded=True) as status:
                st.write("Detecting root cause clusters...")
                time.sleep(0.5)
                agent_state = {
                    "alarm_path": str(ALARM_PATH),
                    "topology_path": str(NT_PATH),
                    "graph_path": str(AC_PATH),
                }
                if st.session_state.get("root_cause_output"):
                    agent_state["root_cause_output"] = st.session_state[
                        "root_cause_output"
                    ]
                else:
                    agent_state = root_cause_agent(agent_state)

                st.write("Querying Solution Manual via RAG...")
                time.sleep(0.5)
                agent_state = remediation_agent(agent_state)
                agent_state = issue_classifier(agent_state)
                if agent_state.get("issue_class") == "MAJOR":
                    agent_state = create_ticket(agent_state)
                    next_action = (
                        "Major issue inserted in defect logs as "
                        f"{agent_state.get('ticket_id', 'new ticket')}."
                    )
                else:
                    agent_state = human_approval(agent_state)
                    next_action = "Minor issue ready for the human approval section."
                status.update(
                    label="Analysis Complete!",
                    state="complete",
                    expanded=False,
                )

            st.session_state["root_cause_output"] = agent_state.get(
                "root_cause_output", {}
            )
            st.session_state["remediation_output"] = agent_state.get(
                "remediation_output", {}
            )
            st.session_state["remediation_issue_class"] = agent_state.get(
                "issue_class", ""
            )
            st.session_state["remediation_next_action"] = next_action
            st.session_state["remediation_agent_executed"] = True
            st.rerun()

    if st.session_state.get("remediation_agent_executed") or rem_output:
        rem_output = st.session_state.get("remediation_output", rem_output)
        issue_class = st.session_state.get("remediation_issue_class", issue_class)
        next_action = st.session_state.get("remediation_next_action", "")
        st.write("")
        recommendation_col, action_col = st.columns([0.68, 0.32])
        with recommendation_col:
            with st.container(border=True):
                section_header("AI Recommendation", "Grounded in solution manual")
                st.markdown(f"### {rem_output.get('root_cause', 'Recommended Action')}")
                st.write(rem_output.get("fix", "No recommendation available."))
                with st.expander("Raw remediation output"):
                    st.json(rem_output)
        with action_col:
            report_card(
                [
                    ("Resolution class", issue_class or "N/A", "danger" if issue_class == "MAJOR" else "warning"),
                    (
                        "Confidence",
                        f"{int(float(rem_output.get('confidence', 0)) * 100)}%",
                        "success",
                    ),
                    ("Next action", next_action or "Awaiting workflow", "primary"),
                ]
            )

with evidence_tab:
    graph_col, history_col = st.columns([0.58, 0.42])
    with graph_col:
        with st.container(border=True):
            section_header("Subgraph Evidence", "Root cause correlation")
            if AC_PATH.exists():
                st.image(
                    str(AC_PATH),
                    width="stretch",
                    caption="Root Cause Subgraph",
                )
            else:
                st.info("No evidence graph has been generated yet.")
    with history_col:
        with st.container(border=True):
            section_header("Intelligence Trail", "Current workflow")
            timeline(
                [
                    ("Stage 1", "Alarm correlation", "Clustered related alarms and ranked causal nodes."),
                    ("Stage 2", "Root cause handoff", "Consumed the latest RCA session output."),
                    ("Stage 3", "Knowledge retrieval", "Queried the indexed solution manual."),
                    (
                        "Stage 4",
                        "Operational routing",
                        st.session_state.get(
                            "remediation_next_action",
                            "Awaiting recommendation execution.",
                        ),
                    ),
                ]
            )

with knowledge_tab:
    with st.container(border=True):
        section_header("Solution Manual RAG", "Authoritative operational playbook")
        if SOLM_PATH.exists():
            encoded_pdf = base64.b64encode(SOLM_PATH.read_bytes()).decode("ascii")
            st.iframe(
                f"data:application/pdf;base64,{encoded_pdf}",
                height=790,
                width="stretch",
            )
        else:
            st.warning("Solution Manual PDF not found in data directory.")
