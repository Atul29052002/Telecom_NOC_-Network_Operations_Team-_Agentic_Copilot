from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any, TypedDict

import pandas as pd
import requests
from langgraph.graph import END, START, StateGraph
from pypdf import PdfReader

from app.engine import run_root_cause_engine


class NocState(TypedDict, total=False):
    alarm_path: str
    topology_path: str
    graph_path: str
    root_cause_output: dict[str, Any]
    remediation_output: dict[str, Any]
    issue_class: str
    approval: str
    execution_status: dict[str, Any]
    ticket_id: str


def _read_manual_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text_chunks = []
    for page in reader.pages:
        text_chunks.append(page.extract_text() or "")
    return "\n".join(text_chunks)


def _heuristic_root_cause(top_candidates: list[dict[str, Any]], topology_path: str, graph_path: str) -> dict[str, Any]:
    primary = top_candidates[0]
    secondary = top_candidates[1] if len(top_candidates) > 1 else top_candidates[0]
    root = primary if "Fiber" in primary.get("alarm_name", "") else secondary
    affected_equipment = [root.get("equipment", "Edge Router")]
    if root.get("alarm_name") == "Fiber Cut":
        confidence = 0.95
        impact = "Primary fiber segment and downstream transport services impacted"
        reasoning = "The alarm graph indicates a high-weight fiber-related event that explains downstream link and service alarms."
    else:
        confidence = 0.82
        impact = "Regional transport degradation around the selected site"
        reasoning = "The clustering and graph ranking point to a localized network failure with spreading impact."
    return {
        "root_cause": root.get("alarm_name", "Fiber Cut"),
        "confidence": round(confidence, 2),
        "affected_equipment": affected_equipment,
        "reasoning": reasoning,
        "impact": impact,
    }


def root_cause_agent(state: NocState) -> NocState:
    engine_output = run_root_cause_engine(state["alarm_path"], output_dir=str(Path(state["alarm_path"]).parent))
    root_cause = _heuristic_root_cause(engine_output.get("top_candidates", []), state.get("topology_path", ""), state.get("graph_path", ""))
    state["root_cause_output"] = root_cause
    return state


def remediation_agent(state: NocState) -> NocState:
    manual_pdf = str(Path(state["alarm_path"]).parent / "solution_manual.pdf")
    manual_text = _read_manual_text(manual_pdf)
    root_cause = state["root_cause_output"].get("root_cause", "Fiber Cut")
    query = root_cause.lower()
    relevant = [line for line in manual_text.splitlines() if query in line.lower()][:4]
    if not relevant:
        relevant = ["No direct match found in the manual."]
    fix = relevant[0] if relevant else "Escalate to the field operations team."
    complexity = "MAJOR" if "fiber" in query or "power" in query or "tower" in query else "MINOR"
    state["remediation_output"] = {
        "root_cause": root_cause,
        "fix": fix,
        "complexity": complexity,
        "confidence": 0.89,
    }
    return state


def issue_classifier(state: NocState) -> NocState:
    complexity = state["remediation_output"].get("complexity", "MINOR")
    state["issue_class"] = complexity
    return state


def create_ticket(state: NocState) -> NocState:
    defect_log = Path(state["alarm_path"]).parent / "defect_log.csv"
    df = pd.read_csv(defect_log) if defect_log.exists() else pd.DataFrame(columns=["ticket_id", "root_cause", "severity", "status", "created_at"])
    ticket_id = f"TKT-{len(df)+1:03d}"
    row = {
        "ticket_id": ticket_id,
        "root_cause": state["root_cause_output"].get("root_cause", "Unknown"),
        "severity": state["issue_class"],
        "status": "Open",
        "created_at": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(defect_log, index=False)
    state["ticket_id"] = ticket_id
    return state


def human_approval(state: NocState) -> NocState:
    state["approval"] = state.get("approval", "Approve")
    return state


def minor_resolver_agent(state: NocState) -> NocState:
    tool_name = "router_reset"
    result = execute_mcp_tool(tool_name, target="Edge Router")
    state["execution_status"] = result
    return state


def execute_mcp_tool(tool_name: str, target: str = "Edge Router") -> dict[str, Any]:
    from app.mcp_server import handle_tool

    return handle_tool(tool_name, target)


def build_workflow() -> Any:
    workflow = StateGraph(NocState)
    workflow.add_node("root_cause_engine", root_cause_agent)
    workflow.add_node("remediation_agent", remediation_agent)
    workflow.add_node("issue_classifier", issue_classifier)
    workflow.add_node("create_ticket", create_ticket)
    workflow.add_node("human_approval", human_approval)
    workflow.add_node("minor_resolver_agent", minor_resolver_agent)

    workflow.add_edge(START, "root_cause_engine")
    workflow.add_edge("root_cause_engine", "remediation_agent")
    workflow.add_edge("remediation_agent", "issue_classifier")
    workflow.add_conditional_edges(
        "issue_classifier",
        lambda state: "create_ticket" if state["issue_class"] == "MAJOR" else "human_approval",
        {"create_ticket": "create_ticket", "human_approval": "human_approval"},
    )
    workflow.add_edge("create_ticket", END)
    workflow.add_edge("human_approval", "minor_resolver_agent")
    workflow.add_edge("minor_resolver_agent", END)
    return workflow.compile()


def run_workflow(alarm_path: str, approval: str = "Approve") -> dict[str, Any]:
    app = build_workflow()
    initial_state: NocState = {
        "alarm_path": alarm_path,
        "topology_path": str(Path(alarm_path).parent / "network_topology.jpg"),
        "graph_path": str(Path(alarm_path).parent / "root_cause_subgraph.jpg"),
        "approval": approval,
    }
    final_state = app.invoke(initial_state)
    return final_state
