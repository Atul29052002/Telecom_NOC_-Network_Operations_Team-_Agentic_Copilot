from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd


def parse_timestamp(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%Y-%m-%d %H:%M:%S", errors="coerce")


def load_or_stream_alarm_logs(path: str | os.PathLike[str]) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["alarm_raised_time"] = parse_timestamp(df["alarm_raised_time"])
    return df.sort_values("alarm_raised_time").reset_index(drop=True)


def compute_alarms_per_minute(df: pd.DataFrame) -> pd.Series:
    minute_bucket = df["alarm_raised_time"].dt.floor("min")
    return minute_bucket.value_counts().sort_index()


def detect_alarm_storm(df: pd.DataFrame, threshold: int = 20) -> pd.DataFrame:
    rates = compute_alarms_per_minute(df)
    if rates.empty:
        return df.head(50).copy()
    trigger_minute = None
    for minute, count in rates.items():
        if count > threshold:
            trigger_minute = minute
            break
    if trigger_minute is None:
        return df.head(50).copy()
    window_start = trigger_minute - pd.Timedelta(seconds=30)
    window_end = trigger_minute + pd.Timedelta(seconds=40)
    return df[(df["alarm_raised_time"] >= window_start) & (df["alarm_raised_time"] <= window_end)].copy()


def clean_alarm_data(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.sort_values("alarm_raised_time").reset_index(drop=True)
    df = df.drop_duplicates(subset=["alarm_name", "equipment_id", "severity", "alarm_raised_time"], keep="first")

    cleaned: list[dict[str, Any]] = []
    recent_windows: dict[tuple[str, str], list[pd.Timestamp]] = {}
    for _, row in df.iterrows():
        key = (str(row["equipment_id"]), str(row["alarm_name"]))
        occurrences = recent_windows.get(key, [])
        now = row["alarm_raised_time"]
        occurrences = [ts for ts in occurrences if now - ts <= pd.Timedelta(seconds=90)]
        if len(occurrences) >= 3:
            continue
        occurrences.append(now)
        recent_windows[key] = occurrences
        cleaned.append(row.to_dict())

    return pd.DataFrame(cleaned)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def dbscan_cluster(df: pd.DataFrame, eps_km: float = 1.2, min_samples: int = 3) -> pd.DataFrame:
    if df.empty:
        return df.assign(cluster=-1)

    labels = [-1] * len(df)
    cluster_id = 0
    visited = set()

    def region_query(index: int) -> list[int]:
        point = df.iloc[index]
        neighbors = []
        for candidate_idx, candidate in df.iterrows():
            if haversine_km(point["latitude"], point["longitude"], candidate["latitude"], candidate["longitude"]) <= eps_km:
                neighbors.append(candidate_idx)
        return neighbors

    for index in range(len(df)):
        if index in visited:
            continue
        visited.add(index)
        neighbors = region_query(index)
        if len(neighbors) < min_samples:
            labels[index] = -1
            continue
        labels[index] = cluster_id
        cluster_queue = set(neighbors) - {index}
        while cluster_queue:
            current = cluster_queue.pop()
            if current not in visited:
                visited.add(current)
                current_neighbors = region_query(current)
                if len(current_neighbors) >= min_samples:
                    cluster_queue.update(current_neighbors)
            if labels[current] == -1:
                labels[current] = cluster_id
            if labels[current] != cluster_id:
                labels[current] = cluster_id
        cluster_id += 1

    df = df.copy()
    df["cluster"] = labels
    return df


def build_alarm_graph(df: pd.DataFrame) -> tuple[nx.DiGraph, list[dict[str, Any]]]:
    graph = nx.DiGraph()
    for idx, row in df.iterrows():
        graph.add_node(idx, **row.to_dict())

    severity_rank = {"Minor": 1, "Major": 2, "Critical": 3}
    for i, row_a in df.iterrows():
        for j, row_b in df.iterrows():
            if i == j:
                continue
            time_delta = abs((row_a["alarm_raised_time"] - row_b["alarm_raised_time"]).total_seconds())
            geo_delta = haversine_km(row_a["latitude"], row_a["longitude"], row_b["latitude"], row_b["longitude"])
            same_equipment = row_a["equipment_id"] == row_b["equipment_id"]
            dependency = row_a["alarm_name"] in {"Fiber Cut", "Link Down", "BGP Failure"} or row_b["alarm_name"] in {"Fiber Cut", "Link Down", "BGP Failure"}
            if time_delta <= 120 and geo_delta <= 2.5 and (same_equipment or dependency):
                weight = 0.4 * severity_rank.get(str(row_b["severity"]), 1) + 0.3 * (1 / (time_delta / 30 + 1)) + 0.3 * (1 / (geo_delta + 1))
                if row_a["alarm_name"] == "Fiber Cut" or row_b["alarm_name"] == "Fiber Cut":
                    weight += 1.0
                graph.add_edge(i, j, weight=round(weight, 3))

    ranked_nodes = []
    for node, attrs in graph.nodes(data=True):
        outgoing = sum(data.get("weight", 0) for _, _, data in graph.out_edges(node, data=True))
        ranked_nodes.append({"node": node, "score": outgoing, **attrs})
    ranked_nodes = sorted(ranked_nodes, key=lambda item: item["score"], reverse=True)
    return graph, ranked_nodes


def save_subgraph_image(graph: nx.DiGraph, ranked_nodes: list[dict[str, Any]], alarm_df: pd.DataFrame, output_path: str) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    top_nodes = [item["node"] for item in ranked_nodes[:6]]
    subgraph = graph.subgraph(top_nodes).copy()
    if not subgraph.nodes:
        subgraph = graph.copy()

    pos = nx.spring_layout(subgraph, seed=43)
    fig, ax = plt.subplots(figsize=(8, 6))
    nx.draw_networkx_nodes(subgraph, pos, node_color="#ff7f0e", node_size=800, ax=ax)
    nx.draw_networkx_edges(subgraph, pos, arrowstyle="->", arrowsize=10, alpha=0.7, ax=ax)
    labels = {
        node: f"{alarm_df.loc[node, 'alarm_id']}\n{alarm_df.loc[node, 'alarm_name']}\n{alarm_df.loc[node, 'equipment_name']}\n{alarm_df.loc[node, 'alarm_raised_time'].strftime('%H:%M:%S')}"
        for node in subgraph.nodes
    }
    nx.draw_networkx_labels(subgraph, pos, labels=labels, font_size=8, ax=ax)
    ax.set_title("Root Cause Subgraph")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=220)
    plt.close(fig)


def run_root_cause_engine(alarm_path: str, output_dir: str = "data") -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    alarm_df = load_or_stream_alarm_logs(alarm_path)
    storm_df = detect_alarm_storm(alarm_df)
    cleaned_df = clean_alarm_data(storm_df)
    clustered_df = dbscan_cluster(cleaned_df)
    cluster_path = output_dir / "alarm_clusters.jpg"
    fig, ax = plt.subplots(figsize=(7, 5))
    for cluster_id in sorted(clustered_df["cluster"].unique()):
        subset = clustered_df[clustered_df["cluster"] == cluster_id]
        if cluster_id == -1:
            ax.scatter(subset["longitude"], subset["latitude"], color="gray", s=20, label="Noise")
        else:
            ax.scatter(subset["longitude"], subset["latitude"], s=24, label=f"Cluster {cluster_id}")
    ax.set_title("Alarm Clusters")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend(loc="best")
    plt.tight_layout()
    plt.savefig(cluster_path, dpi=220)
    plt.close(fig)

    graph, ranked_nodes = build_alarm_graph(clustered_df)
    subgraph_path = output_dir / "root_cause_subgraph.jpg"
    save_subgraph_image(graph, ranked_nodes, clustered_df, str(subgraph_path))

    candidate_rows = []
    for item in ranked_nodes[:2]:
        candidate_rows.append({
            "alarm_id": clustered_df.loc[item["node"], "alarm_id"],
            "alarm_name": clustered_df.loc[item["node"], "alarm_name"],
            "equipment": clustered_df.loc[item["node"], "equipment_name"],
            "timestamp": clustered_df.loc[item["node"], "alarm_raised_time"].strftime("%Y-%m-%d %H:%M:%S"),
            "severity": clustered_df.loc[item["node"], "severity"],
            "score": item["score"],
        })

    return {
        "storm_window": storm_df.to_dict(orient="records"),
        "clustered": clustered_df.to_dict(orient="records"),
        "top_candidates": candidate_rows,
        "cluster_image": str(cluster_path),
        "subgraph_image": str(subgraph_path),
    }
