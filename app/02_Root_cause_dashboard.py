from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents import root_cause_agent
from app.engine import run_root_cause_engine
from app.noc_ui import (
    COLORS,
    kpi_card,
    page_header,
    render_grid,
    report_card,
    section_header,
    style_plotly,
)


DATA_DIR = PROJECT_ROOT / "data"
ALARM_PATH = DATA_DIR / "alarm_logs.csv"
NT_PATH = DATA_DIR / "network_topology.jpg"
AC_PATH = DATA_DIR / "root_cause_subgraph.jpg"


@st.cache_data(show_spinner="Running root cause engine...")
def load_top_candidates() -> pd.DataFrame:
    engine_output = run_root_cause_engine(str(ALARM_PATH), output_dir=str(DATA_DIR))
    return pd.DataFrame(engine_output["top_candidates"])


@st.cache_data
def load_alarm_data() -> pd.DataFrame:
    return pd.read_csv(ALARM_PATH)


def build_topology_figure(alarms: pd.DataFrame) -> go.Figure:
    graph = nx.Graph()
    relations = (
        alarms[["equipment_name", "alarm_name", "severity"]]
        .drop_duplicates()
        .head(35)
    )
    for row in relations.itertuples(index=False):
        graph.add_node(row.equipment_name, kind="equipment", severity=row.severity)
        graph.add_node(row.alarm_name, kind="alarm", severity=row.severity)
        graph.add_edge(row.equipment_name, row.alarm_name)

    positions = nx.spring_layout(graph, seed=17, k=0.75)
    edge_x, edge_y = [], []
    for source, target in graph.edges():
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    fig = go.Figure(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(width=1, color="rgba(148,163,184,.28)"),
            hoverinfo="skip",
        )
    )
    severity_colors = {
        "Critical": COLORS["danger"],
        "Major": COLORS["warning"],
        "Minor": "#EAB308",
    }
    for kind in ("equipment", "alarm"):
        nodes = [node for node, attrs in graph.nodes(data=True) if attrs["kind"] == kind]
        fig.add_trace(
            go.Scatter(
                x=[positions[node][0] for node in nodes],
                y=[positions[node][1] for node in nodes],
                text=nodes,
                customdata=[graph.nodes[node]["severity"] for node in nodes],
                mode="markers+text",
                name=kind.title(),
                textposition="top center",
                textfont=dict(size=9, color=COLORS["muted"]),
                marker=dict(
                    size=18 if kind == "equipment" else 12,
                    color=[
                        COLORS["primary"]
                        if kind == "equipment"
                        else severity_colors.get(graph.nodes[node]["severity"], COLORS["warning"])
                        for node in nodes
                    ],
                    line=dict(width=1, color="#D7F7FF"),
                    opacity=0.88,
                ),
                hovertemplate="<b>%{text}</b><br>Severity: %{customdata}<extra></extra>",
            )
        )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(
        title=dict(text="Interactive Dependency Topology", font=dict(size=13)),
        showlegend=True,
    )
    return style_plotly(fig, height=470)


page_header(
    "Root Cause Analysis",
    "AI-assisted root cause identification with ranked evidence and topology context.",
    "Incident Intelligence",
)

top_candidates_df = load_top_candidates()
alarm_df = load_alarm_data()
rc_output = st.session_state.get("root_cause_output", {})
confidence = int(float(rc_output.get("confidence", 0)) * 100)

summary_cols = st.columns(4)
with summary_cols[0]:
    kpi_card(
        "Root cause",
        rc_output.get("root_cause", "Pending"),
        "Latest agent conclusion",
        "danger" if rc_output else "primary",
        "!",
    )
with summary_cols[1]:
    kpi_card("Confidence", f"{confidence}%", "AI confidence score", "success", "%")
with summary_cols[2]:
    kpi_card(
        "Candidates",
        len(top_candidates_df),
        "Ranked by graph score",
        "primary",
        "#",
    )
with summary_cols[3]:
    affected = len(rc_output.get("affected_equipment", []))
    kpi_card("Affected assets", affected, "Confirmed equipment", "warning", "◆")

report_tab, topology_tab, evidence_tab = st.tabs(
    ["Investigation Report", "Interactive Topology", "Alarm Evidence"]
)

with report_tab:
    action_col, candidates_col = st.columns([0.37, 0.63])
    with action_col:
        with st.container(border=True):
            section_header("RCA Agent", "On demand")
            st.caption(
                "Correlate alarm clusters, graph rank, topology evidence, and model reasoning."
            )
            if st.button(
                "Run Root Cause Identification",
                type="primary",
                width="stretch",
            ):
                with st.spinner("Root Cause Identification Agent running..."):
                    agent_state = root_cause_agent(
                        {
                            "alarm_path": str(ALARM_PATH),
                            "topology_path": str(NT_PATH),
                            "graph_path": str(AC_PATH),
                        }
                    )
                st.session_state["root_cause_output"] = agent_state.get(
                    "root_cause_output", {}
                )
                st.session_state["root_cause_agent_executed"] = True
                st.rerun()
    with candidates_col:
        with st.container(border=True):
            section_header("Top Root Cause Nodes", "Search, sort, and filter")
            render_grid(
                top_candidates_df,
                key="rca_candidates_grid",
                height=300,
                search_label="Search RCA candidates",
            )

    if st.session_state.get("root_cause_agent_executed") or rc_output:
        rc_output = st.session_state.get("root_cause_output", rc_output)
        st.write("")
        detail_col, reasoning_col = st.columns([0.34, 0.66])
        with detail_col:
            report_card(
                [
                    ("Identified root cause", rc_output.get("root_cause", "Analyzing"), "danger"),
                    ("Confidence", f"{int(float(rc_output.get('confidence', 0)) * 100)}%", "success"),
                    ("Impact radius", rc_output.get("impact", "N/A"), "primary"),
                    (
                        "Affected equipment",
                        ", ".join(rc_output.get("affected_equipment", [])) or "N/A",
                        "",
                    ),
                ]
            )
        with reasoning_col:
            with st.container(border=True):
                section_header("AI Investigation Report", "Evidence-backed conclusion")
                st.write(rc_output.get("reasoning", "No reasoning provided."))
                affected_equipment = rc_output.get("affected_equipment", [])
                if affected_equipment:
                    st.markdown(
                        "**Affected equipment:** "
                        + ", ".join(f"`{item}`" for item in affected_equipment)
                    )
                with st.expander("Raw agent output"):
                    st.json(rc_output)

with topology_tab:
    graph_col, source_col = st.columns([0.68, 0.32])
    with graph_col:
        with st.container(border=True):
            st.plotly_chart(
                build_topology_figure(alarm_df),
                width="stretch",
                config={"displayModeBar": False, "responsive": True},
            )
    with source_col:
        with st.container(border=True):
            section_header("Topology Source", "Reference artifact")
            st.image(str(NT_PATH), width="stretch")
            st.caption(
                "The interactive view is derived from current alarm-to-equipment relationships; "
                "the source topology remains available for visual verification."
            )

with evidence_tab:
    image_col, context_col = st.columns([0.62, 0.38])
    with image_col:
        with st.container(border=True):
            section_header("Root Cause Alarm Subgraph", "Generated by RCA engine")
            st.image(str(AC_PATH), width="stretch")
    with context_col:
        with st.container(border=True):
            section_header("Evidence Context", "Latest agent observations")
            image_descriptions = rc_output.get("image_descriptions", [])
            if image_descriptions:
                for item in image_descriptions:
                    st.markdown(f"**{item.get('label', 'Evidence')}**")
                    st.caption(item.get("description", "No description available."))
            else:
                st.info("Run the RCA agent to populate visual evidence descriptions.")
