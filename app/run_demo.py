from __future__ import annotations

from pathlib import Path

from app.agents import run_workflow
from app.data_generation import build_demo_assets
from app.engine import run_root_cause_engine


if __name__ == "__main__":
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    assets = build_demo_assets(str(data_dir))
    print("Generated assets:", assets)
    engine_output = run_root_cause_engine(assets["alarm_path"], output_dir=str(data_dir))
    print("Top candidates:", engine_output["top_candidates"])
    workflow_result = run_workflow(assets["alarm_path"], approval="Approve")
    print("Workflow result:", workflow_result)
