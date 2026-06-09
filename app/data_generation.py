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
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


RANDOM_SEED = 42
random.seed(RANDOM_SEED)


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
        ("Fiber Cut", 0.55, "Critical"),
        ("Link Down", 0.20, "Major"),
        ("Router CPU High", 0.15, "Major"),
        ("Power Failure", 0.10, "Critical"),
        ("Backhaul Failure", 0.18, "Major"),
        ("Tower Down", 0.25, "Critical"),
        ("Packet Loss", 0.12, "Minor"),
        ("BGP Failure", 0.16, "Major"),
        ("Interface Down", 0.14, "Major"),
        ("Service Degradation", 0.11, "Minor"),
    ]

    rows = []
    alert_counter = 1
    root_cause_equipment = "EDGE-01"
    root_cause_name = "Fiber Cut"

    for idx in range(num_alarms):
        if idx < 80:
            alarm_name = root_cause_name
            equipment_id = root_cause_equipment
            equipment_name = "Edge Router"
            equipment_vendor = "Cisco"
            severity = "Critical"
            time_offset = timedelta(seconds=idx * 0.8)
            lat = 12.9672 + random.uniform(-0.0016, 0.0014)
            lon = 77.6001 + random.uniform(-0.0015, 0.0015)
        elif idx < 230:
            alarm_name = random.choice(["Link Down", "Interface Down", "BGP Failure", "Service Degradation"])
            equipment_id, equipment_name, equipment_vendor, lat, lon = random.choice(equipment_nodes)
            severity = random.choice(["Major", "Critical"])
            time_offset = timedelta(seconds=30 + idx * 0.7)
        elif idx < 520:
            alarm_name = random.choice(["Router CPU High", "Backhaul Failure", "Packet Loss", "Power Failure"])
            equipment_id, equipment_name, equipment_vendor, lat, lon = random.choice(equipment_nodes)
            severity = random.choice(["Major", "Minor"])
            time_offset = timedelta(seconds=60 + idx * 0.9)
        else:
            alarm_name, _, severity = random.choice(alarm_catalog)
            equipment_id, equipment_name, equipment_vendor, lat, lon = random.choice(equipment_nodes)
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
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    manual_entries = [
        {
            "alarm_type": "Fiber Cut",
            "root_cause": "Backhoe damage or cable sheath breach on the primary feeder path",
            "troubleshooting": "Check optical power levels, inspect last-mile route, verify OTDR traces",
            "fix_procedure": "Dispatch field crew, replace damaged fiber, restore service and re-test path",
            "resolution_category": "Major Fix",
        },
        {
            "alarm_type": "Router CPU High",
            "root_cause": "Unexpected traffic spike or process leak on the edge router",
            "troubleshooting": "Inspect process utilization, queue depth, and interface counters",
            "fix_procedure": "Reboot the router or clear the misbehaving process",
            "resolution_category": "Minor Fix",
        },
        {
            "alarm_type": "Interface Down",
            "root_cause": "Physical disconnect or line protocol flap",
            "troubleshooting": "Verify cable status, optical levels, and port admin state",
            "fix_procedure": "Reset the interface and validate link restoration",
            "resolution_category": "Minor Fix",
        },
        {
            "alarm_type": "Power Failure",
            "root_cause": "Local power loss at the shelter or backup battery issue",
            "troubleshooting": "Check rectifier health, battery voltage, and breaker status",
            "fix_procedure": "Restore AC/DC power and verify backup systems",
            "resolution_category": "Major Fix",
        },
        {
            "alarm_type": "Backhaul Failure",
            "root_cause": "Microwave or transit path degradation between sites",
            "troubleshooting": "Check link budget, E1/T1 status, and transport alarms",
            "fix_procedure": "Re-route or re-establish the backhaul link",
            "resolution_category": "Major Fix",
        },
        {
            "alarm_type": "BGP Failure",
            "root_cause": "Routing policy mismatch or neighbor session instability",
            "troubleshooting": "Review BGP sessions, prefix advertisements, and route reflectors",
            "fix_procedure": "Reset BGP session and validate convergence",
            "resolution_category": "Minor Fix",
        },
        {
            "alarm_type": "Tower Down",
            "root_cause": "Power or site equipment outage at the tower site",
            "troubleshooting": "Review site alarms, generator status, and environmental sensors",
            "fix_procedure": "Dispatch site engineer and restore power or equipment",
            "resolution_category": "Major Fix",
        },
        {
            "alarm_type": "Packet Loss",
            "root_cause": "Congestion or unstable radio/transport conditions",
            "troubleshooting": "Inspect interface counters and queue utilization",
            "fix_procedure": "Adjust traffic shaping or change the impacted path",
            "resolution_category": "Minor Fix",
        },
        {
            "alarm_type": "Link Down",
            "root_cause": "Physical link or optical path failure",
            "troubleshooting": "Verify alarms, optics, and neighboring device state",
            "fix_procedure": "Re-seat the fiber patch or replace the damaged span",
            "resolution_category": "Major Fix",
        },
        {
            "alarm_type": "Service Degradation",
            "root_cause": "Network congestion or temporary capacity saturation",
            "troubleshooting": "Check throughput, congestion counters, and utilization thresholds",
            "fix_procedure": "Re-balance capacity and monitor for recovery",
            "resolution_category": "Minor Fix",
        },
    ]

    styles = getSampleStyleSheet()
    story = []
    title_style = styles["Title"]
    body_style = styles["BodyText"]

    for index, entry in enumerate(manual_entries, start=1):
        story.append(Paragraph(f"Page {index}: {entry['alarm_type']}", title_style))
        story.append(Spacer(1, 0.12 * inch))
        story.append(Paragraph(f"Root Cause: {entry['root_cause']}", body_style))
        story.append(Paragraph(f"Troubleshooting: {entry['troubleshooting']}", body_style))
        story.append(Paragraph(f"Fix Procedure: {entry['fix_procedure']}", body_style))
        story.append(Paragraph(f"Resolution Category: {entry['resolution_category']}", body_style))
        story.append(Spacer(1, 0.2 * inch))

    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    doc.build(story)

    text_lines = []
    for entry in manual_entries:
        text_lines.append(f"Alarm Type: {entry['alarm_type']}")
        text_lines.append(f"Root Cause: {entry['root_cause']}")
        text_lines.append(f"Troubleshooting: {entry['troubleshooting']}")
        text_lines.append(f"Fix Procedure: {entry['fix_procedure']}")
        text_lines.append(f"Resolution Category: {entry['resolution_category']}")
        text_lines.append("")
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
