from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, TypedDict

import pandas as pd
import requests

from app.engine import run_root_cause_engine


class NocState(TypedDict, total=False):
    alarm_path: str
    output_dir: str
    topology_path: str
    graph_path: str
    root_cause_output: dict[str, Any]
    remediation_output: dict[str, Any]
    issue_class: str
    approval: str
    execution_status: dict[str, Any]
    ticket_id: str


VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
VLLM_MODEL = os.getenv("VLLM_MODEL", "meta-llama/Llama-3.2-3B")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
USE_VLLM = os.getenv("USE_VLLM", "1").lower() in {"1", "true", "yes", "on"}


def _read_manual_text(pdf_path: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    text_chunks = []
    for page in reader.pages:
        text_chunks.append(page.extract_text() or "")
    return "\n".join(text_chunks)


@lru_cache(maxsize=1)
def _get_embedding_model() -> Any:
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def _vllm_available() -> bool:
    if not USE_VLLM:
        return False
    try:
        response = requests.get(f"{VLLM_BASE_URL.rstrip('/')}/models", timeout=1.5)
        return response.status_code < 500
    except Exception:
        return False


def _get_or_create_vector_store(pdf_path: str, persist_dir: str) -> Any:
    from langchain_chroma import Chroma
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    text = _read_manual_text(pdf_path)
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=90)
    documents = [Document(page_content=chunk, metadata={"source": pdf_path}) for chunk in splitter.split_text(text)]

    embeddings = _get_embedding_model()
    persist_path = Path(persist_dir)
    persist_path.mkdir(parents=True, exist_ok=True)
    if any(persist_path.iterdir()):
        return Chroma(persist_directory=str(persist_path), embedding_function=embeddings, collection_name="telecom_manual")
    return Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=str(persist_path),
        collection_name="telecom_manual",
    )


def _get_llm() -> Any | None:
    if not _vllm_available():
        return None
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=VLLM_MODEL,
        base_url=VLLM_BASE_URL,
        api_key=os.getenv("VLLM_API_KEY", "EMPTY"),
        temperature=0.1,
        max_tokens=320,
        request_timeout=4,
        max_retries=0,
    )


def _parse_json_response(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
    return {}


def _heuristic_root_cause(top_candidates: list[dict[str, Any]], topology_path: str, graph_path: str) -> dict[str, Any]:
    primary = top_candidates[0] if top_candidates else {"alarm_name": "Fiber Cut", "equipment": "Edge Router"}
    secondary = top_candidates[1] if len(top_candidates) > 1 else primary
    root = primary if "Fiber" in primary.get("alarm_name", "") else secondary
    affected_equipment = [root.get("equipment", "Edge Router")]
    prompt = (
        "You are a senior telecom NOC architect. Based on the ranked alarms below, decide the single most likely root cause. "
        "Return concise JSON with keys root_cause, confidence, affected_equipment, reasoning, impact.\n"
        f"Top candidates: {top_candidates}\n"
        f"Topology path: {topology_path}\nGraph path: {graph_path}"
    )
    try:
        llm = _get_llm()
        if llm is not None:
            response = llm.invoke(prompt)
            parsed = _parse_json_response(getattr(response, "content", str(response)))
            if parsed:
                parsed["confidence"] = float(parsed.get("confidence", 0.85))
                parsed["affected_equipment"] = parsed.get("affected_equipment", affected_equipment)
                parsed["impact"] = parsed.get("impact", "Regional transport impact")
                return parsed
    except Exception:
        pass

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
    output_dir = state.get("output_dir", str(Path(state["alarm_path"]).parent))
    engine_output = run_root_cause_engine(state["alarm_path"], output_dir=output_dir)
    root_cause = _heuristic_root_cause(engine_output.get("top_candidates", []), state.get("topology_path", ""), state.get("graph_path", ""))
    state["root_cause_output"] = root_cause
    return state


def remediation_agent(state: NocState) -> NocState:
    manual_pdf = str(Path(state["alarm_path"]).parent / "solution_manual.pdf")
    persist_dir = str(Path(state["alarm_path"]).parent / "chroma_db")
    root_cause = state["root_cause_output"].get("root_cause", "Fiber Cut")
    query = f"Telecom incident {root_cause}; provide remediation steps, fix procedure, complexity and troubleshooting"
    try:
        vector_store = _get_or_create_vector_store(manual_pdf, persist_dir)
        documents = vector_store.similarity_search(query, k=4)
    except Exception:
        documents = []
    context = "\n\n".join(doc.page_content for doc in documents)

    prompt = (
        "You are a telecom NOC remediation specialist. Use the knowledge base context below to propose a remediation plan. "
        "Return concise JSON with keys fix, complexity, confidence, reasoning.\n"
        f"Root cause: {root_cause}\n"
        f"Context: {context}"
    )
    try:
        llm = _get_llm()
        if llm is not None:
            response = llm.invoke(prompt)
            parsed = _parse_json_response(getattr(response, "content", str(response)))
            if parsed:
                state["remediation_output"] = {
                    "root_cause": root_cause,
                    "fix": parsed.get("fix", "Consult the field operations team"),
                    "complexity": parsed.get("complexity", "MAJOR" if "fiber" in root_cause.lower() else "MINOR"),
                    "confidence": float(parsed.get("confidence", 0.88)),
                }
                return state
    except Exception:
        pass

    complexity = "MAJOR" if "fiber" in root_cause.lower() or "power" in root_cause.lower() or "tower" in root_cause.lower() else "MINOR"
    if documents:
        fix = documents[0].page_content
    elif complexity == "MAJOR":
        fix = "Dispatch field operations, isolate the impacted segment, validate alternate routing, repair the physical fault, and confirm alarm clearance."
    else:
        fix = "Apply the standard remote recovery procedure, monitor alarm clearance, and escalate if the alarm persists."
    state["remediation_output"] = {
        "root_cause": root_cause,
        "fix": fix,
        "complexity": complexity,
        "confidence": 0.88,
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
    from langgraph.graph import END, START, StateGraph

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
