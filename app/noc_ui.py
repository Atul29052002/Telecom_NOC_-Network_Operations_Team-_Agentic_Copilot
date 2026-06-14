from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
CSS_PATH = APP_DIR / "assets" / "noc.css"

COLORS = {
    "background": "#081120",
    "surface": "#0F172A",
    "card": "#111827",
    "primary": "#00C8FF",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "text": "#F8FAFC",
    "muted": "#94A3B8",
    "grid": "#1E293B",
}


def inject_theme() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def page_header(title: str, subtitle: str, eyebrow: str, live: bool = True) -> None:
    status = (
        '<div class="noc-live-pill"><span class="noc-live-dot"></span>Operational</div>'
        if live
        else ""
    )
    st.markdown(
        f"""
        <div class="noc-page-header">
          <div>
            <div class="noc-eyebrow">{escape(eyebrow)}</div>
            <div class="noc-page-title">{escape(title)}</div>
            <div class="noc-page-subtitle">{escape(subtitle)}</div>
          </div>
          {status}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, meta: str = "") -> None:
    st.markdown(
        f"""
        <div class="noc-section-heading">
          <div class="noc-section-title">{escape(title)}</div>
          <div class="noc-section-meta">{escape(meta)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(
    label: str,
    value: Any,
    delta: str = "",
    tone: str = "primary",
    icon: str = "•",
    positive: bool | None = None,
) -> None:
    accent = COLORS.get(tone, COLORS["primary"])
    delta_color = (
        COLORS["muted"]
        if positive is None
        else COLORS["success"] if positive else COLORS["danger"]
    )
    st.markdown(
        f"""
        <div class="noc-kpi-card"
             style="--accent:{accent};--accent-glow:{accent}22;--delta-color:{delta_color};">
          <div class="noc-kpi-label">{escape(str(label))}</div>
          <div class="noc-kpi-row">
            <div class="noc-kpi-value">{escape(str(value))}</div>
            <div class="noc-kpi-icon">{escape(icon)}</div>
          </div>
          <div class="noc-kpi-delta">{escape(delta) if delta else "&nbsp;"}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def report_card(items: Iterable[tuple[str, Any, str]]) -> None:
    rows = []
    for label, value, tone in items:
        rows.append(
            f'<div class="noc-report-label">{escape(str(label))}</div>'
            f'<div class="noc-report-value {escape(tone)}">{escape(str(value))}</div>'
        )
    st.markdown(
        f'<div class="noc-report">{"".join(rows)}</div>',
        unsafe_allow_html=True,
    )


def sidebar_status(agent_count: int = 4) -> None:
    st.markdown(
        """
        <div class="noc-sidebar-brand">
          <div class="noc-brand-mark">N</div>
          <div>
            <div class="noc-brand-name">Telecom NOC</div>
            <div class="noc-brand-sub">Command Center</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="noc-sidebar-card">
          <div class="noc-sidebar-card-title">NOC Copilot</div>
          <div class="noc-sidebar-stat">
            <span>Platform status</span>
            <span style="color:{COLORS['success']}">Online</span>
          </div>
          <div class="noc-sidebar-stat"><span>Agents ready</span><span>{agent_count}</span></div>
          <div class="noc-sidebar-stat"><span>Inference</span><span>ROCm / vLLM</span></div>
          <div class="noc-sidebar-stat"><span>Health</span><span>99.9%</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def style_plotly(fig: go.Figure, height: int = 330) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        height=height,
        margin=dict(l=20, r=20, t=38, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=COLORS["muted"], size=11),
        hoverlabel=dict(bgcolor=COLORS["card"], bordercolor=COLORS["primary"]),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=1.08),
    )
    fig.update_xaxes(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"])
    fig.update_yaxes(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"])
    return fig


def render_grid(
    data: pd.DataFrame,
    key: str,
    height: int = 430,
    search_label: str = "Search records",
) -> None:
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

    query = st.text_input(
        search_label,
        key=f"{key}_search",
        placeholder="Search across all columns...",
        label_visibility="collapsed",
    )
    grid_data = data.copy()
    for column in grid_data.columns:
        if pd.api.types.is_datetime64_any_dtype(grid_data[column]):
            grid_data[column] = grid_data[column].dt.strftime("%Y-%m-%d %H:%M:%S")

    builder = GridOptionsBuilder.from_dataframe(grid_data)
    builder.configure_default_column(
        sortable=True,
        filter=True,
        resizable=True,
        floatingFilter=True,
        minWidth=115,
    )
    builder.configure_pagination(enabled=True, paginationPageSize=12)
    builder.configure_grid_options(
        quickFilterText=query,
        animateRows=True,
        suppressCellFocus=True,
        rowHeight=39,
        headerHeight=40,
    )

    badge_style = JsCode(
        """
        function(params) {
          const value = String(params.value || '').toLowerCase();
          const base = {
            'fontWeight': '700',
            'borderRadius': '999px',
            'padding': '2px 8px',
            'display': 'inline-flex',
            'alignItems': 'center'
          };
          if (value.includes('critical') || value.includes('escalated')) {
            return {...base, 'color':'#FCA5A5', 'backgroundColor':'rgba(239,68,68,.16)'};
          }
          if (value.includes('major') || value.includes('pending') || value.includes('progress')) {
            return {...base, 'color':'#FCD34D', 'backgroundColor':'rgba(245,158,11,.16)'};
          }
          if (value.includes('minor') || value.includes('warning')) {
            return {...base, 'color':'#FDE68A', 'backgroundColor':'rgba(234,179,8,.12)'};
          }
          if (value.includes('resolved') || value.includes('closed') || value.includes('online')) {
            return {...base, 'color':'#86EFAC', 'backgroundColor':'rgba(34,197,94,.14)'};
          }
          if (value.includes('open') || value.includes('active')) {
            return {...base, 'color':'#7DD3FC', 'backgroundColor':'rgba(0,200,255,.14)'};
          }
          return null;
        }
        """
    )
    for column in grid_data.columns:
        if column.casefold() in {"severity", "status", "issue_class", "complexity"}:
            builder.configure_column(column, cellStyle=badge_style)

    AgGrid(
        grid_data,
        gridOptions=builder.build(),
        height=height,
        theme="streamlit",
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        custom_css={
            ".ag-root-wrapper": {
                "background-color": COLORS["surface"],
                "border": "1px solid rgba(148,163,184,.16)",
                "border-radius": "10px",
            },
            ".ag-header": {
                "background-color": "#0B1424",
                "border-bottom": "1px solid rgba(148,163,184,.16)",
            },
            ".ag-header-cell-text": {"color": "#CBD5E1", "font-weight": "700"},
            ".ag-row": {
                "background-color": COLORS["surface"],
                "border-color": "rgba(148,163,184,.09)",
                "color": "#CBD5E1",
            },
            ".ag-row-hover": {"background-color": "rgba(0,200,255,.06) !important"},
            ".ag-floating-filter-input": {"color": "#CBD5E1"},
        },
        key=key,
    )


def workflow_stepper(
    steps: list[str],
    active_index: int,
    statuses: list[str] | None = None,
) -> None:
    parts = []
    for index, label in enumerate(steps):
        state = (
            statuses[index]
            if statuses and index < len(statuses)
            else "complete" if index < active_index else "active" if index == active_index else ""
        )
        marker = (
            "✓"
            if state == "complete"
            else "×"
            if state == "failed"
            else "•"
            if state == "active"
            else str(index + 1)
        )
        line = '<div class="noc-step-line"></div>' if index < len(steps) - 1 else ""
        parts.append(
            f'<div class="noc-step {state}">'
            f'<div class="noc-step-node">{marker}</div>'
            f'<div class="noc-step-label">{escape(label)}</div>{line}</div>'
        )
    st.markdown(f'<div class="noc-stepper">{"".join(parts)}</div>', unsafe_allow_html=True)


def timeline(items: Iterable[tuple[str, str, str]]) -> None:
    rendered = []
    for time_label, title, copy in items:
        rendered.append(
            '<div class="noc-timeline-item">'
            f'<div class="noc-timeline-time">{escape(str(time_label))}</div>'
            f'<div class="noc-timeline-title">{escape(str(title))}</div>'
            f'<div class="noc-timeline-copy">{escape(str(copy))}</div>'
            "</div>"
        )
    st.markdown(f'<div class="noc-timeline">{"".join(rendered)}</div>', unsafe_allow_html=True)
