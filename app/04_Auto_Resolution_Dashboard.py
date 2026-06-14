from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents import human_rejection_handler, minor_resolver_agent
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
ALARM_PATH = DATA_DIR / "alarm_logs.csv"


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def persist_state(next_state: dict[str, Any]) -> None:
    STATE_PATH.write_text(
        json.dumps(next_state, indent=2),
        encoding="utf-8",
    )


def execution_overall_status(execution: Any) -> str:
    if isinstance(execution, dict):
        return str(execution.get("overall_status") or execution.get("status") or "").casefold()
    return str(execution or "").casefold()


def execution_display_status(approval_value: str | None, execution: Any) -> tuple[str, str]:
    overall = execution_overall_status(execution)
    if approval_value == "Reject" or overall == "rejected":
        return "Rejected", "danger"
    if approval_value != "Approve":
        return "Waiting", "primary"
    if overall in {"success", "completed", "complete", "executed"} or (execution and not overall):
        return "Executed", "success"
    if overall:
        return overall.replace("_", " ").title(), "warning"
    return "Waiting", "primary"


def workflow_statuses(approval_value: str | None, execution: Any) -> list[str]:
    statuses = ["complete", "complete", "complete", "active", ""]
    overall = execution_overall_status(execution)
    if approval_value == "Reject" or overall == "rejected":
        return ["complete", "complete", "complete", "failed", "failed"]
    if approval_value == "Approve":
        statuses[3] = "complete"
        statuses[4] = (
            "complete"
            if overall in {"success", "completed", "complete", "executed"} or (execution and not overall)
            else "active"
        )
    return statuses


TOOL_LABELS = {
    "router_reset": "Router reset",
    "clear_router_alarms": "Clear router alarms",
    "verify_router_health": "Verify router health",
}


def title_text(value: Any) -> str:
    return str(value or "unknown").replace("_", " ").title()


def parse_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def execution_metric_text(tool_name: str, payload: dict[str, Any]) -> str:
    if tool_name == "router_reset":
        post_check = payload.get("steps", {}).get("post_validation", {})
        if isinstance(post_check, dict):
            return (
                f"CPU {post_check.get('cpu_percent', 'N/A')}%, "
                f"memory {post_check.get('memory_percent', 'N/A')}%, "
                f"interfaces down {post_check.get('interfaces_down', 'N/A')}."
            )
    if tool_name == "clear_router_alarms":
        details = payload.get("details", {})
        if isinstance(details, dict):
            return f"Alarms cleared: {details.get('alarms_cleared', 'N/A')}."
    if tool_name == "verify_router_health":
        health = payload.get("health", {})
        if isinstance(health, dict):
            return (
                f"CPU {health.get('cpu_percent', 'N/A')}%, "
                f"memory {health.get('memory_percent', 'N/A')}%, "
                f"active alarms {health.get('alarms_active', 'N/A')}."
            )
    return ""


def execution_timeline_items(execution: Any) -> list[tuple[str, str, str]]:
    if not isinstance(execution, dict):
        return [("Current", "Execution status", str(execution))]

    items: list[tuple[str, str, str]] = []
    overall = execution.get("overall_status") or execution.get("status")
    if overall:
        items.append(("Status", title_text(overall), execution.get("message", "Execution status recorded.")))

    for index, tool_name in enumerate(TOOL_LABELS, start=1):
        payload = execution.get(tool_name)
        if not isinstance(payload, dict):
            continue
        status = title_text(payload.get("status"))
        target = payload.get("target", "target equipment")
        message = payload.get("message", f"{TOOL_LABELS[tool_name]} completed for {target}.")
        metrics = execution_metric_text(tool_name, payload)
        copy = f"{message} {metrics}".strip()
        items.append((str(index).zfill(2), f"{TOOL_LABELS[tool_name]} - {status}", copy))

    summary_payload = parse_json_object(execution.get("llm_summary"))
    summary = summary_payload.get("summary") if summary_payload else None
    if summary:
        items.append(("Summary", "Execution summary", str(summary)))

    known_keys = {*TOOL_LABELS, "overall_status", "status", "message", "llm_summary"}
    for key, value in execution.items():
        if key in known_keys or isinstance(value, (dict, list)):
            continue
        items.append(("Detail", title_text(key), str(value)))

    return items or [("Current", "Execution status", "No execution details are available yet.")]


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
minor_resolver_output = workflow_result.get("minor_resolver_output", {})
execution_label, execution_tone = execution_display_status(approval, execution_status)
workflow_step_statuses = workflow_statuses(approval, execution_status)
active_index = workflow_step_statuses.index("active") if "active" in workflow_step_statuses else len(workflow_step_statuses)

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
    approval_tone = "success" if approval == "Approve" else "danger" if approval == "Reject" else "warning"
    kpi_card(
        "Approval",
        approval or "Pending",
        "Human-in-the-loop policy",
        approval_tone,
        "H",
    )
with summary_cols[3]:
    kpi_card(
        "Execution",
        execution_label,
        "MCP execution state",
        execution_tone,
        "▶",
    )

with st.container(border=True):
    section_header("Resolution Workflow", "Governed automation")
    workflow_stepper(
        ["Detection", "RCA", "Recommendation", "Approval", "Execution"],
        active_index=active_index,
        statuses=workflow_step_statuses,
    )

approval_tab, execution_tab, audit_tab = st.tabs(
    ["Approval Center", "Execution Timeline", "Resolver Monitor"]
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
                index=None,
            )
            st.caption(
                " Once the decision is approved, the workflow proceeds to minor issue resolution agent."
            )
            if st.button(
                "Commit Decision",
                type="primary",
                width="stretch",
            ):
                if decision is None:
                    st.warning("Select Approve or Reject before committing the decision.")
                    st.stop()
                workflow_result["approval"] = decision
                workflow_result["approval_committed"] = True
                workflow_result["alarm_path"] = workflow_result.get("alarm_path", str(ALARM_PATH))
                workflow_result["issue_class"] = workflow_result.get(
                    "issue_class",
                    workflow_result.get("remediation_output", {}).get("complexity", "SIMPLE FIX"),
                )
                if decision == "Approve":
                    workflow_result.pop("execution_status", None)
                    workflow_result.pop("minor_resolver_output", None)
                    st.session_state.pop("minor_resolver_output", None)
                    st.session_state.pop("execution_status", None)
                    toast_message = "Human approval recorded. Execution is waiting for operator start."
                else:
                    workflow_result = dict(human_rejection_handler(workflow_result))
                    st.session_state["minor_resolver_output"] = workflow_result.get(
                        "minor_resolver_output", {}
                    )
                    st.session_state["execution_status"] = workflow_result.get(
                        "execution_status", {}
                    )
                    toast_message = "Solution rejected and inserted into defect log."
                state["workflow_result"] = workflow_result
                persist_state(state)
                st.success(f"Policy Updated: {decision}. {toast_message}")
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
                timeline(execution_timeline_items(execution_status))
            elif approval == "Approve":
                if st.button(
                    "Start Approved Execution",
                    type="primary",
                    width="stretch",
                ):
                    workflow_result = dict(minor_resolver_agent(workflow_result))
                    st.session_state["minor_resolver_output"] = workflow_result.get(
                        "minor_resolver_output", {}
                    )
                    st.session_state["execution_status"] = workflow_result.get(
                        "execution_status", {}
                    )
                    state["workflow_result"] = workflow_result
                    persist_state(state)
                    st.success("Approved execution completed.")
                    st.rerun()
                timeline(
                    [
                        ("Recorded", "Operator decision", "Human approval committed."),
                        ("Waiting", "Execution waiting", "MCP execution has not been started yet."),
                    ]
                )
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
    resolver_payload = st.session_state.get(
        "minor_resolver_output",
        minor_resolver_output,
    )
    current_execution = st.session_state.get("execution_status", execution_status)
    status_rows = resolver_payload.get("tool_execution_status", [])
    tool_outputs = resolver_payload.get("tool_outputs", {})

    status_col, output_col = st.columns([0.42, 0.58])
    with status_col:
        with st.container(border=True):
            section_header("Minor Issue Resolver Agent", "Tool execution status")
            if resolver_payload:
                report_card(
                    [
                        (
                            "Approval",
                            resolver_payload.get("approval", approval or "Pending"),
                            "success" if resolver_payload.get("approval") == "Approve" else "warning",
                        ),
                        (
                            "Overall status",
                            resolver_payload.get("overall_status", "Waiting"),
                            "success"
                            if resolver_payload.get("overall_status") == "success"
                            else "warning",
                        ),
                        (
                            "Target",
                            resolver_payload.get("target", "N/A"),
                            "primary",
                        ),
                        (
                            "Escalation",
                            "Required" if resolver_payload.get("requires_escalation") else "Not required",
                            "danger" if resolver_payload.get("requires_escalation") else "success",
                        ),
                    ]
                )
                st.markdown("**Resolver summary**")
                st.write(resolver_payload.get("summary", "No summary generated."))
            elif approval == "Approve":
                st.info("Approval is recorded, but no minor issue resolver output is available yet.")
            elif approval == "Reject":
                st.info("Solution was rejected. Resolver execution is skipped and the defect log is updated.")
            else:
                st.info("Commit an approval decision to populate the resolver monitor.")

    with output_col:
        with st.container(border=True):
            section_header("MCP Tool Results", "Reset, alarm clear, health verification")
            if status_rows:
                timeline(
                    [
                        (
                            str(index).zfill(2),
                            f"{row.get('tool', 'unknown')} - {row.get('status', 'unknown')}",
                            row.get("message", ""),
                        )
                        for index, row in enumerate(status_rows, start=1)
                    ]
                )
            elif current_execution:
                st.json(current_execution)
            else:
                st.info("No MCP tool execution has been recorded.")

    with st.expander("Raw minor_resolver_agent output"):
        if resolver_payload:
            st.json(resolver_payload)
        else:
            st.json(workflow_result)

    if tool_outputs:
        with st.expander("Detailed tool payloads"):
            st.json(tool_outputs)
