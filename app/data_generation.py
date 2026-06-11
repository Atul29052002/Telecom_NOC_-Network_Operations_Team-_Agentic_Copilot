from __future__ import annotations

import os
import random
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


RANDOM_SEED = 42
random.seed(RANDOM_SEED)


def _select_topology_equipment(alarm_name: str) -> tuple[str, str, str, float, float]:
    topology_map = {
        "Fiber Cut": [("EDGE-01", "Edge Router", "Cisco", 12.9660, 77.6020)],
        "Link Down": [("TWR-1001", "Tower 1001", "Ericsson", 12.9685, 77.5965), ("TWR-1002", "Tower 1002", "Huawei", 12.9710, 77.6050), ("TWR-1003", "Tower 1003", "ZTE", 12.9648, 77.6078)],
        "Router CPU High": [("CORE-01", "Core Router", "Nokia", 12.9726, 77.5933), ("AGG-01", "Aggregation Router", "Juniper", 12.9704, 77.5984), ("EDGE-01", "Edge Router", "Cisco", 12.9660, 77.6020)],
        "Power Failure": [("TWR-1004", "Tower 1004", "Nokia", 12.9730, 77.6110), ("TWR-1005", "Tower 1005", "Ericsson", 12.9678, 77.5902)],
        "Backhaul Failure": [("AGG-01", "Aggregation Router", "Juniper", 12.9704, 77.5984), ("EDGE-01", "Edge Router", "Cisco", 12.9660, 77.6020)],
        "Tower Down": [("TWR-1001", "Tower 1001", "Ericsson", 12.9685, 77.5965), ("TWR-1002", "Tower 1002", "Huawei", 12.9710, 77.6050), ("TWR-1004", "Tower 1004", "Nokia", 12.9730, 77.6110)],
        "Packet Loss": [("TWR-1001", "Tower 1001", "Ericsson", 12.9685, 77.5965), ("TWR-1002", "Tower 1002", "Huawei", 12.9710, 77.6050), ("EDGE-01", "Edge Router", "Cisco", 12.9660, 77.6020)],
        "BGP Failure": [("CORE-01", "Core Router", "Nokia", 12.9726, 77.5933), ("AGG-01", "Aggregation Router", "Juniper", 12.9704, 77.5984)],
        "Interface Down": [("EDGE-01", "Edge Router", "Cisco", 12.9660, 77.6020), ("AGG-01", "Aggregation Router", "Juniper", 12.9704, 77.5984), ("TWR-1001", "Tower 1001", "Ericsson", 12.9685, 77.5965)],
        "Service Degradation": [("TWR-1004", "Tower 1004", "Nokia", 12.9730, 77.6110), ("TWR-1005", "Tower 1005", "Ericsson", 12.9678, 77.5902), ("EDGE-01", "Edge Router", "Cisco", 12.9660, 77.6020)],
    }
    return random.choice(topology_map.get(alarm_name, [("EDGE-01", "Edge Router", "Cisco", 12.9660, 77.6020)]))


def generate_alarm_logs(output_path: str = "data/alarm_logs.csv", num_alarms: int = 1100) -> pd.DataFrame:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    incident_time = datetime(2026, 6, 9, 20, 0, 0)
    equipment_nodes = [
        ("CORE-01", "Core Router", "Nokia", 12.9726, 77.5933),
        ("AGG-01", "Aggregation Router", "Juniper", 12.9704, 77.5984),
        ("EDGE-01", "Edge Router", "Cisco", 12.9660, 77.6020),
        ("TWR-1001", "Tower 1001", "Ericsson", 12.9685, 77.5965),
        ("TWR-1002", "Tower 1002", "Huawei", 12.9710, 77.6050),
        ("TWR-1003", "Tower 1003", "ZTE", 12.9648, 77.6078),
        ("TWR-1004", "Tower 1004", "Nokia", 12.9730, 77.6110),
        ("TWR-1005", "Tower 1005", "Ericsson", 12.9678, 77.5902),
    ]

    alarm_catalog = [
        ("Fiber Cut", 0.28, "Critical"),
        ("Link Down", 0.14, "Major"),
        ("Router CPU High", 0.12, "Major"),
        ("Power Failure", 0.08, "Critical"),
        ("Backhaul Failure", 0.10, "Major"),
        ("Tower Down", 0.08, "Critical"),
        ("Packet Loss", 0.14, "Minor"),
        ("BGP Failure", 0.08, "Major"),
        ("Interface Down", 0.10, "Major"),
        ("Service Degradation", 0.12, "Minor"),
    ]

    rows = []
    alert_counter = 1
    root_cause_equipment = "EDGE-01"
    root_cause_name = "Fiber Cut"

    for idx in range(num_alarms):
        if idx < 60:
            alarm_name = root_cause_name
            equipment_id = root_cause_equipment
            equipment_name = "Edge Router"
            equipment_vendor = "Cisco"
            severity = "Critical"
            time_offset = timedelta(seconds=idx * 0.8)
            lat = 12.9672 + random.uniform(-0.0016, 0.0014)
            lon = 77.6001 + random.uniform(-0.0015, 0.0015)
        elif idx < 220:
            alarm_name = random.choice(["Link Down", "Interface Down", "Packet Loss", "Service Degradation"])
            equipment_id, equipment_name, equipment_vendor, lat, lon = _select_topology_equipment(alarm_name)
            severity = "Minor" if alarm_name in {"Packet Loss", "Service Degradation"} else random.choice(["Major", "Minor"])
            time_offset = timedelta(seconds=30 + idx * 0.7)
        elif idx < 520:
            alarm_name = random.choice(["Router CPU High", "Backhaul Failure", "Packet Loss", "Power Failure", "BGP Failure"])
            equipment_id, equipment_name, equipment_vendor, lat, lon = _select_topology_equipment(alarm_name)
            severity = "Minor" if alarm_name in {"Packet Loss", "Service Degradation"} else random.choice(["Major", "Minor"])
            time_offset = timedelta(seconds=60 + idx * 0.9)
        else:
            alarm_name, _, severity = random.choice(alarm_catalog)
            equipment_id, equipment_name, equipment_vendor, lat, lon = _select_topology_equipment(alarm_name)
            if alarm_name in {"Packet Loss", "Service Degradation"}:
                severity = "Minor"
            time_offset = timedelta(seconds=85 + idx * 1.2)

        event_time = incident_time + time_offset
        rows.append(
            {
                "alarm_id": f"ALM-{alert_counter:04d}",
                "alarm_name": alarm_name,
                "equipment_id": equipment_id,
                "equipment_name": equipment_name,
                "equipment_vendor": equipment_vendor,
                "alarm_raised_time": event_time.strftime("%Y-%m-%d %H:%M:%S"),
                "duration_seconds": int(random.randint(30, 900)),
                "severity": severity,
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
            }
        )
        alert_counter += 1

    df = pd.DataFrame(rows)
    df = df.sort_values("alarm_raised_time").reset_index(drop=True)
    df.to_csv(output_path, index=False)
    return df


def generate_topology_image(output_path: str = "data/network_topology.jpg") -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    g = nx.Graph()
    g.add_node("Core Router", type="core")
    g.add_node("Aggregation Router", type="aggregation")
    g.add_node("Edge Router", type="edge")
    for tower_id in ["Tower 1001", "Tower 1002", "Tower 1003", "Tower 1004", "Tower 1005"]:
        g.add_node(tower_id, type="tower")

    g.add_edge("Core Router", "Aggregation Router", link_type="fiber")
    g.add_edge("Aggregation Router", "Edge Router", link_type="fiber")
    g.add_edge("Edge Router", "Tower 1001", link_type="fiber")
    g.add_edge("Edge Router", "Tower 1002", link_type="fiber")
    g.add_edge("Edge Router", "Tower 1003", link_type="fiber")
    g.add_edge("Aggregation Router", "Tower 1004", link_type="microwave")
    g.add_edge("Aggregation Router", "Tower 1005", link_type="microwave")

    pos = {
        "Core Router": (0.2, 0.8),
        "Aggregation Router": (0.4, 0.65),
        "Edge Router": (0.6, 0.55),
        "Tower 1001": (0.75, 0.8),
        "Tower 1002": (0.82, 0.65),
        "Tower 1003": (0.79, 0.45),
        "Tower 1004": (0.4, 0.3),
        "Tower 1005": (0.2, 0.4),
    }

    fig, ax = plt.subplots(figsize=(10, 7))
    fiber_edges = [(u, v) for u, v, d in g.edges(data=True) if d["link_type"] == "fiber"]
    microwave_edges = [(u, v) for u, v, d in g.edges(data=True) if d["link_type"] == "microwave"]
    nx.draw_networkx_edges(g, pos, edgelist=fiber_edges, edge_color="royalblue", width=2.2)
    nx.draw_networkx_edges(g, pos, edgelist=microwave_edges, edge_color="orange", width=1.8, style="dashed")
    nx.draw_networkx_nodes(g, pos, node_color=["#1f77b4" if n == "Core Router" else "#ff7f0e" if n == "Aggregation Router" else "#2ca02c" if n == "Edge Router" else "#d62728" for n in g.nodes()], node_size=900)
    nx.draw_networkx_labels(g, pos, font_size=10)
    ax.set_title("Telecom Network Topology")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=250)
    plt.close(fig)


def generate_solution_manual(output_path: str = "data/solution_manual.pdf", text_output_path: str = "data/solution_manual.txt") -> None:
    """Generate the controlled two-page NOC runbook used by remediation retrieval."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    runbooks = [
        {
            "alarm": "Fiber Cut",
            "priority": "P1 Critical",
            "scope": "EDGE-01 and downstream tower transport",
            "validate": "Correlate link alarms; check optical receive power and OTDR fault distance.",
            "action": "Protect traffic, dispatch the fiber crew, and splice or replace the damaged span.",
            "verify": "Optical levels in range; interfaces stable; packet loss cleared for 15 minutes.",
            "owner": "Transport NOC / Field Fiber",
            "escalate": "Open incident bridge immediately; notify carrier when redundancy is unavailable.",
        },
        {
            "alarm": "Link Down / Interface Down",
            "priority": "P2 Major",
            "scope": "Core, aggregation, edge, and tower uplinks",
            "validate": "Check admin and operational state, optics, CRC errors, and peer logs.",
            "action": "Re-seat optics or cable, perform one controlled reset, then use the backup path.",
            "verify": "Protocol up; error counters stable; neighbor adjacency restored.",
            "owner": "IP NOC / Field Operations",
            "escalate": "Escalate after two failed recoveries or loss of primary and backup links.",
        },
        {
            "alarm": "Packet Loss",
            "priority": "P3 Minor",
            "scope": "Tower access and edge transport",
            "validate": "Measure loss, latency, queue drops, radio quality, and path utilization.",
            "action": "Rebalance traffic, correct QoS, or move service to a healthy path.",
            "verify": "Loss below 1 percent and latency within SLA for 15 minutes.",
            "owner": "Performance NOC",
            "escalate": "Escalate above 3 percent loss for 10 minutes or on priority-service impact.",
        },
        {
            "alarm": "Router CPU High",
            "priority": "P2 Major",
            "scope": "CORE-01, AGG-01, or EDGE-01",
            "validate": "Identify top processes, traffic spikes, route churn, and control-plane events.",
            "action": "Rate-limit abusive traffic, clear the process, or execute an approved restart.",
            "verify": "CPU below 70 percent; adjacencies stable; no process restart loop.",
            "owner": "IP Core NOC",
            "escalate": "Escalate above 90 percent for 5 minutes or on control-plane instability.",
        },
        {
            "alarm": "Power Failure / Tower Down",
            "priority": "P1 Critical",
            "scope": "TWR-1001 through TWR-1005",
            "validate": "Check mains, rectifier, battery, generator, site access, and dependent alarms.",
            "action": "Start backup power, dispatch site team, and isolate failed power modules.",
            "verify": "Voltage stable; batteries charging; tower reachable; services restored.",
            "owner": "Site Operations / Energy",
            "escalate": "Escalate when autonomy is under 60 minutes or multiple sites are affected.",
        },
        {
            "alarm": "Backhaul Failure",
            "priority": "P2 Major",
            "scope": "AGG-01 to EDGE-01 transport",
            "validate": "Check fiber or microwave state, errors, capacity, and protection availability.",
            "action": "Switch to protection, restore the bearer, and repair the failed medium.",
            "verify": "Backhaul stable; utilization balanced; downstream alarms cleared.",
            "owner": "Transport NOC",
            "escalate": "Escalate when protection fails or remaining capacity is insufficient.",
        },
        {
            "alarm": "BGP Failure",
            "priority": "P2 Major",
            "scope": "CORE-01 and AGG-01 routing peers",
            "validate": "Check reachability, authentication, timers, policy changes, and route limits.",
            "action": "Correct configuration or reachability, then reset the neighbor under change control.",
            "verify": "Session Established; expected prefixes received; no route oscillation.",
            "owner": "IP Core NOC",
            "escalate": "Escalate immediately for route leakage, dual-peer loss, or mass withdrawal.",
        },
        {
            "alarm": "Service Degradation",
            "priority": "P3 Minor",
            "scope": "Tower and edge service paths",
            "validate": "Correlate latency, loss, utilization, radio KPIs, and customer impact.",
            "action": "Remove the impaired path, tune capacity or QoS, and clear the root alarm.",
            "verify": "KPIs at SLA baseline and no correlated major alarm remains.",
            "owner": "Service Assurance NOC",
            "escalate": "Escalate after 15 minutes or when multiple towers are affected.",
        },
    ]

    styles = getSampleStyleSheet()
    navy = colors.HexColor("#0F172A")
    blue = colors.HexColor("#1D4ED8")
    slate = colors.HexColor("#475569")
    pale_blue = colors.HexColor("#EFF6FF")
    pale_slate = colors.HexColor("#F8FAFC")
    border = colors.HexColor("#CBD5E1")
    title = ParagraphStyle(
        "ManualTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=23,
        textColor=navy,
        alignment=0,
        spaceAfter=5,
    )
    subtitle = ParagraphStyle(
        "ManualSubtitle",
        parent=styles["BodyText"],
        fontSize=8.3,
        leading=10.5,
        textColor=slate,
        spaceAfter=7,
    )
    section = ParagraphStyle(
        "ManualSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=13,
        textColor=blue,
        spaceBefore=5,
        spaceAfter=4,
    )
    body = ParagraphStyle(
        "ManualBody",
        parent=styles["BodyText"],
        fontSize=7.8,
        leading=10,
        textColor=navy,
    )
    small = ParagraphStyle(
        "ManualSmall",
        parent=body,
        fontSize=6.5,
        leading=7.8,
    )
    header = ParagraphStyle(
        "ManualHeader",
        parent=small,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=1,
    )

    def p(value: str, style: ParagraphStyle = small) -> Paragraph:
        return Paragraph(value, style)

    def styled_table(rows: list[list[str]], widths: list[float], header_color=navy, text_style=body) -> Table:
        data = [
            [p(value, header if row_index == 0 else text_style) for value in row]
            for row_index, row in enumerate(rows)
        ]
        table = Table(data, colWidths=widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), header_color),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, pale_slate]),
                    ("BOX", (0, 0), (-1, -1), 0.6, border),
                    ("INNERGRID", (0, 0), (-1, -1), 0.35, border),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return table

    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(border)
        canvas.line(0.55 * inch, 0.48 * inch, 7.95 * inch, 0.48 * inch)
        canvas.setFillColor(slate)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(0.55 * inch, 0.31 * inch, "Telecom NOC | Controlled Operations Reference | Internal Use")
        canvas.drawRightString(7.95 * inch, 0.31 * inch, f"Page {doc.page}")
        canvas.restoreState()

    overview = Table(
        [
            [p("Operational scope", header), p("Dataset profile", header), p("Control objective", header)],
            [
                p("CORE-01, AGG-01, EDGE-01 and TWR-1001 to TWR-1005", body),
                p("1,100 alarms across Critical, Major and Minor severities", body),
                p("Restore safely, preserve evidence, and verify SLA recovery", body),
            ],
        ],
        colWidths=[2.42 * inch] * 3,
    )
    overview.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), blue),
                ("BACKGROUND", (0, 1), (-1, 1), pale_blue),
                ("BOX", (0, 0), (-1, -1), 0.6, border),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, border),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    governance = styled_table(
        [
            ["Priority", "Acknowledge", "Command and communication"],
            ["P1 Critical", "5 minutes", "Open incident bridge; notify Incident Commander, field owner, and service management."],
            ["P2 Major", "10 minutes", "Assign technical owner; correlate dependent alarms; update every 30 minutes."],
            ["P3 Minor", "30 minutes", "Track in NOC queue; resolve before SLA breach; escalate on growing impact."],
        ],
        [1.15 * inch, 1.45 * inch, 4.66 * inch],
    )
    fiber = runbooks[0]
    fiber_playbook = styled_table(
        [
            ["Stage", "Required action"],
            ["Detect and contain", f"{fiber['validate']} Protect customer traffic and freeze unrelated changes."],
            ["Diagnose", "Confirm the failed span and affected towers. Capture interfaces, optical readings, timestamps, topology, and change history."],
            ["Restore", fiber["action"]],
            ["Validate", fiber["verify"]],
            ["Close", "Attach test results, impact, repair details, outage duration, approvals, and preventive actions to the incident."],
        ],
        [1.35 * inch, 5.91 * inch],
        header_color=blue,
    )

    story = [
        Paragraph("Telecom NOC Incident Response Manual", title),
        Paragraph("Enterprise runbook for the generated alarm dataset | Version 1.0 | Owner: Network Operations", subtitle),
        overview,
        Paragraph("Incident Governance", section),
        governance,
        Paragraph("P1 Playbook: Fiber Cut", section),
        fiber_playbook,
        Spacer(1, 0.07 * inch),
        Paragraph(
            "<b>Safety gate:</b> No fiber handling, electrical work, tower access, or device restart without an approved change, qualified personnel, and a tested rollback plan.",
            body,
        ),
        PageBreak(),
        Paragraph("Alarm Response Matrix", title),
        Paragraph(
            "Correlate alarms before action. Treat downstream symptoms as dependent until the highest-impact upstream fault is cleared.",
            subtitle,
        ),
    ]
    matrix_rows = [["Alarm / priority / owner", "Validation", "Controlled action", "Recovery and escalation"]]
    for item in runbooks[1:]:
        matrix_rows.append(
            [
                f"<b>{item['alarm']}</b><br/>{item['priority']}<br/>{item['owner']}",
                item["validate"],
                item["action"],
                f"<b>Verify:</b> {item['verify']}<br/><b>Escalate:</b> {item['escalate']}",
            ]
        )
    story.extend(
        [
            styled_table(
                matrix_rows,
                [1.42 * inch, 1.82 * inch, 1.92 * inch, 2.10 * inch],
                text_style=small,
            ),
            Paragraph("Closure and Evidence Standard", section),
            Paragraph(
                "Confirm service KPIs; clear or explain correlated alarms; record commands and approvals; attach before-and-after evidence; document customer impact; and open a problem record for recurring or P1 incidents.",
                body,
            ),
        ]
    )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.48 * inch,
        bottomMargin=0.58 * inch,
        title="Telecom NOC Incident Response Manual",
        author="Network Operations",
        subject="Enterprise remediation runbook for the telecom alarm dataset",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)

    text_lines = [
        "TELECOM NOC INCIDENT RESPONSE MANUAL",
        "Version 1.0 | Owner: Network Operations | Internal Use",
        "",
        "INCIDENT GOVERNANCE",
        "P1 Critical: acknowledge in 5 minutes; open incident bridge.",
        "P2 Major: acknowledge in 10 minutes; assign owner and update every 30 minutes.",
        "P3 Minor: acknowledge in 30 minutes; track in the NOC queue.",
        "",
    ]
    for item in runbooks:
        text_lines.extend(
            [
                f"Alarm Type: {item['alarm']}",
                f"Priority: {item['priority']}",
                f"Scope: {item['scope']}",
                f"Validation: {item['validate']}",
                f"Fix Procedure: {item['action']}",
                f"Recovery Verification: {item['verify']}",
                f"Owner: {item['owner']}",
                f"Escalation: {item['escalate']}",
                "",
            ]
        )
    Path(text_output_path).write_text("\n".join(text_lines), encoding="utf-8")


def build_demo_assets(output_dir: str = "data") -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    alarm_path = output_dir / "alarm_logs.csv"
    topology_path = output_dir / "network_topology.jpg"
    manual_pdf = output_dir / "solution_manual.pdf"
    manual_text = output_dir / "solution_manual.txt"
    defect_log = output_dir / "defect_log.csv"
    if not defect_log.exists():
        pd.DataFrame(columns=["ticket_id", "root_cause", "severity", "status", "created_at"]).to_csv(defect_log, index=False)

    generate_alarm_logs(str(alarm_path))
    generate_topology_image(str(topology_path))
    generate_solution_manual(str(manual_pdf), str(manual_text))
    return {
        "alarm_path": str(alarm_path),
        "topology_path": str(topology_path),
        "manual_pdf": str(manual_pdf),
        "manual_text": str(manual_text),
        "defect_log": str(defect_log),
    }