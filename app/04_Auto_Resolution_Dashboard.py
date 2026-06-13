from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.noc_ui import (
    kpi_card,
    page_header,
    report_card,
    section_header,
    timeline,
    workflow_stepper,
)


DATA_DIR = PROJECT_ROOT / "data"
STATE_PATH = DATA_DIR / "telecom_state.json"


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


state = load_state()
workflow_result = dict(state.get("workflow_result", {}))

# The RCA and remediation pages keep their newest agent results in the shared
# Streamlit session. Prefer those values over the last persisted workflow run.
session_root_cause = st.session_state.get("root_cause_output")
session_remediation = st.session_state.get("remediation_output")
session_issue_class = st.session_state.get("remediation_issue_class")
if session_root_cause:
    workflow_result["root_cause_output"] = session_root_cause
if session_remediation:
    workflow_result["remediation_output"] = session_remediation
if session_issue_class:
    workflow_result["issue_class"] = session_issue_class

approval_committed = bool(workflow_result.get("approval_committed", False))
approval = workflow_result.get("approval") if approval_committed else None
execution_status = workflow_result.get("execution_status", {})
active_index = 5 if approval_committed and execution_status else 4 if approval_committed else 3

page_header(
    "Auto Resolution Console",
    "Human-governed remediation approval, execution readiness, and audit visibility.",
    "Closed-Loop Operations",
)

summary_cols = st.columns(4)
with summary_cols[0]:
    kpi_card("Detection", "Complete", "Alarm event correlated", "success", "✓")
with summary_cols[1]:
    kpi_card("RCA", "Complete", "Root cause available", "success", "✓")
with summary_cols[2]:
    kpi_card(
        "Approval",
        approval or "Pending",
        "Human-in-the-loop policy",
        "success" if approval == "Approve" else "warning",
        "H",
    )
with summary_cols[3]:
    kpi_card(
        "Execution",
        execution_status.get("status", "Waiting") if isinstance(execution_status, dict) else "Waiting",
        "MCP execution state",
        "success" if execution_status else "primary",
        "▶",
    )

with st.container(border=True):
    section_header("Resolution Workflow", "Governed automation")
    workflow_stepper(
        ["Detection", "RCA", "Recommendation", "Approval", "Execution", "Validation"],
        active_index=active_index,
    )

approval_tab, execution_tab, audit_tab = st.tabs(
    ["Approval Center", "Execution Timeline", "Audit & Agent Data"]
)

with approval_tab:
    action_col, proposal_col = st.columns([0.42, 0.58])
    with action_col:
        with st.container(border=True):
            section_header("Human-in-the-Loop Action", "Required control point")
            decision = st.radio(
                "Please review the proposed remediation and select an action:",
                ["Approve", "Reject"],
                horizontal=True,
            )
            st.caption(
                " Once the decision is approved, the workflow proceeds to minor issue resolution agent."
            )
            if st.button(
                "Commit Decision",
                type="primary",
                width="stretch",
            ):
                workflow_result["approval"] = decision
                workflow_result["approval_committed"] = True
                state["workflow_result"] = workflow_result
                STATE_PATH.write_text(
                    json.dumps(state, indent=2),
                    encoding="utf-8",
                )
                st.success(f"Policy Updated: {decision}")
                st.rerun()

    with proposal_col:
        rc_output = workflow_result.get("root_cause_output", {})
        rem_output = workflow_result.get("remediation_output", {})
        identified_issue = rc_output.get("root_cause", "")
        remediation_issue = rem_output.get("root_cause", "")
        outputs_are_synced = bool(
            rc_output
            and rem_output
            and identified_issue
            and remediation_issue
            and identified_issue.strip().casefold()
            == remediation_issue.strip().casefold()
        )
        if outputs_are_synced:
            affected_equipment = rc_output.get("affected_equipment", [])
            if isinstance(affected_equipment, str):
                affected_equipment = [affected_equipment]
            target = ", ".join(affected_equipment) or "Unknown"
            with st.container(border=True):
                section_header("Proposed Remediation", "AI-generated recovery plan")
                report_card(
                    [
                        ("Identified issue", identified_issue, "danger"),
                        ("Target", target, "primary"),
                        (
                            "Complexity",
                            rem_output.get("complexity", workflow_result.get("issue_class", "N/A")),
                            "warning",
                        ),
                        (
                            "Confidence",
                            f"{int(float(rem_output.get('confidence', 0)) * 100)}%",
                            "success",
                        ),
                    ]
                )
                st.markdown("**Recommended action**")
                st.write(rem_output.get("fix", "Review Required"))
        else:
            with st.container(border=True):
                st.info(
                    "No synchronized remediation proposal is available. "
                    "Run the analysis workflow to populate both agent outputs."
                )

with execution_tab:
    preview_col, log_col = st.columns([0.55, 0.45])
    with preview_col:
        with st.container(border=True):
            section_header("Execution Preview", "Controlled recovery sequence")
            timeline(
                [
                    ("01", "Validate target", "Confirm the impacted asset and active alarm context."),
                    ("02", "Apply remediation", "Execute the approved recovery action through MCP tooling."),
                    ("03", "Verify service", "Check alarm clearance and network health indicators."),
                    ("04", "Close or escalate", "Record success or route unresolved impact to operations."),
                ]
            )
    with log_col:
        with st.container(border=True):
            section_header("Execution Log", "Live workflow status")
            if execution_status:
                if isinstance(execution_status, dict):
                    timeline(
                        [
                            ("Current", str(key).replace("_", " ").title(), str(value))
                            for key, value in execution_status.items()
                        ]
                    )
                else:
                    st.write(execution_status)
            elif approval:
                timeline(
                    [
                        ("Recorded", "Operator decision", f"Workflow policy set to {approval}."),
                        ("Waiting", "Execution not started", "No MCP execution result is available yet."),
                    ]
                )
            else:
                st.info("Execution is locked until an approval decision is submitted.")

with audit_tab:
    with st.container(border=True):
        section_header("Raw Agent Reasoning", "Immutable workflow payload")
        st.json(workflow_result)
