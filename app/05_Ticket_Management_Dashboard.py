from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.noc_ui import (
    kpi_card,
    page_header,
    render_grid,
    section_header,
    timeline,
    workflow_stepper,
)


DATA_DIR = PROJECT_ROOT / "data"
DEFECT_LOG = DATA_DIR / "defect_log.csv"

page_header(
    "Ticket Management",
    "ServiceNow-style incident operations with searchable records and lifecycle context.",
    "IT Service Management",
)

if DEFECT_LOG.exists():
    tickets = pd.read_csv(DEFECT_LOG)
    status = tickets["status"].astype(str).str.casefold() if "status" in tickets else pd.Series(dtype=str)
    severity = (
        tickets["severity"].astype(str).str.casefold()
        if "severity" in tickets
        else pd.Series(dtype=str)
    )
    open_count = int(status.isin(["open", "pending", "in progress"]).sum())
    resolved_count = int(status.isin(["resolved", "closed"]).sum())
    escalated_count = int(severity.isin(["critical", "major"]).sum())
    pending_count = int(status.eq("pending").sum())

    kpi_cols = st.columns(5)
    cards = [
        ("Open tickets", open_count, "Active incident queue", "primary", "O"),
        ("In progress", pending_count, "Awaiting next action", "warning", "▶"),
        ("Escalated", escalated_count, "Major or critical", "danger", "!"),
        ("Resolved", resolved_count, "Completed incidents", "success", "✓"),
        ("Total records", len(tickets), "All lifecycle states", "primary", "#"),
    ]
    for column, card in zip(kpi_cols, cards):
        with column:
            kpi_card(*card)

    table_col, lifecycle_col = st.columns([0.72, 0.28])
    with table_col:
        with st.container(border=True):
            section_header("All Tickets", "Search, filter, sort, and paginate")
            render_grid(
                tickets,
                key="ticket_management_grid",
                height=540,
                search_label="Search tickets",
            )
    with lifecycle_col:
        with st.container(border=True):
            section_header("Incident Lifecycle", "Standard response path")
            workflow_stepper(
                ["Reported", "RCA", "Remediation", "Approval", "Resolved"],
                active_index=4 if resolved_count else 2,
            )
            latest = tickets.iloc[-1]
            st.markdown(f"**Latest incident: `{latest.get('ticket_id', 'N/A')}`**")
            timeline(
                [
                    (
                        str(latest.get("created_at", "Created")),
                        "Ticket created",
                        f"{latest.get('root_cause', 'Unknown')} entered the operations queue.",
                    ),
                    (
                        "RCA",
                        "Cause classified",
                        f"Severity assigned as {latest.get('severity', 'Unknown')}.",
                    ),
                    (
                        "Current",
                        f"Status: {latest.get('status', 'Unknown')}",
                        "The incident remains visible until operational closure.",
                    ),
                ]
            )
else:
    with st.container(border=True):
        st.info(
            "No tickets created yet. Run the workflow and create a defect entry to populate this pane."
        )
