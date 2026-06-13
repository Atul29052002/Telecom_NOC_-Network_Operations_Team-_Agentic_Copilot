from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("Telecom MCP Server")


# ---------------------------------------------------------------------------
# Helper: simulated execution timestamp
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ---------------------------------------------------------------------------
# Tool 1 – Router Reset  (primary tool used by minor_resolver_agent)
#
# Performs a 3-step procedure that mirrors the remediation agent's prescribed
# fix for minor router issues:
#   Step 1  – Pre-check: capture CPU, memory, and interface snapshot
#   Step 2  – Graceful reset: reload the control-plane / restart the router
#   Step 3  – Post-validation: verify CPU < 70 %, interfaces up, alarms clear
# ---------------------------------------------------------------------------

@mcp.tool()
def router_reset(
    target: str,
    reason: str = "Minor router issue detected by remediation agent",
    approved_by: str = "NOC Operator (human-in-the-loop)",
) -> dict[str, Any]:
    """Perform a controlled router reset on the target equipment.

    Executes a 3-step procedure: pre-check snapshot, graceful reset,
    and post-validation to confirm recovery.
    """
    # Step 1 – Pre-check snapshot
    pre_check = {
        "cpu_percent": 92,
        "memory_percent": 78,
        "interfaces_up": 3,
        "interfaces_down": 1,
        "uptime_hours": 720,
        "snapshot_time": _now(),
    }

    # Step 2 – Graceful reset (simulated)
    reset_result = {
        "command": f"reload soft target={target}",
        "execution_time": _now(),
        "duration_seconds": 12,
        "status": "completed",
    }

    # Step 3 – Post-validation
    post_check = {
        "cpu_percent": 34,
        "memory_percent": 52,
        "interfaces_up": 4,
        "interfaces_down": 0,
        "alarms_cleared": True,
        "validation_time": _now(),
    }

    return {
        "status": "success",
        "tool": "router_reset",
        "target": target,
        "reason": reason,
        "approved_by": approved_by,
        "message": (
            f"Router reset completed for {target}. "
            f"CPU dropped from {pre_check['cpu_percent']}% to {post_check['cpu_percent']}%, "
            f"all interfaces restored, alarms cleared."
        ),
        "steps": {
            "pre_check": pre_check,
            "reset": reset_result,
            "post_validation": post_check,
        },
    }


# ---------------------------------------------------------------------------
# Tool 2 – Clear Router Alarms
#
# Acknowledges and clears stale alarms on the target router after a
# successful reset.  Called as a follow-up by minor_resolver_agent when
# residual alarms remain.
# ---------------------------------------------------------------------------

@mcp.tool()
def clear_router_alarms(target: str) -> dict[str, Any]:
    """Acknowledge and clear all Minor-severity router alarms on the target equipment."""
    return {
        "status": "success",
        "tool": "clear_router_alarms",
        "target": target,
        "message": (
            f"All Minor-severity router alarms on {target} have been "
            f"acknowledged and cleared."
        ),
        "details": {
            "alarms_cleared": 5,
            "alarm_types": [
                "Router CPU High",
                "Router Interface Flap",
                "Router Memory High",
                "Router Config Drift",
                "Router Packet Loss",
            ],
            "cleared_at": _now(),
        },
    }


# ---------------------------------------------------------------------------
# Tool 3 – Verify Router Health
#
# Lightweight health-check that the minor_resolver_agent can invoke after
# the reset to confirm the router is stable before closing the loop.
# ---------------------------------------------------------------------------

@mcp.tool()
def verify_router_health(target: str) -> dict[str, Any]:
    """Run a post-reset health check on the target router to confirm stability."""
    return {
        "status": "success",
        "tool": "verify_router_health",
        "target": target,
        "message": f"Health check passed for {target}. Router is stable.",
        "health": {
            "cpu_percent": 28,
            "memory_percent": 45,
            "interfaces_up": 4,
            "interfaces_down": 0,
            "bgp_peers_established": 2,
            "uptime_minutes": 3,
            "alarms_active": 0,
            "checked_at": _now(),
        },
    }


# ---------------------------------------------------------------------------
# Internal dispatcher (called by agents.execute_mcp_tool)
# ---------------------------------------------------------------------------

def handle_tool(tool_name: str, target: str = "Edge Router 01") -> dict[str, Any]:
    """Dispatch a tool by name.  Evaluated lazily so only the requested tool runs."""
    dispatchers: dict[str, Any] = {
        "router_reset": lambda: router_reset(target=target),
        "clear_router_alarms": lambda: clear_router_alarms(target=target),
        "verify_router_health": lambda: verify_router_health(target=target),
    }
    handler = dispatchers.get(tool_name)
    if handler is None:
        return {"status": "error", "message": f"Unknown tool '{tool_name}'"}
    return handler()


if __name__ == "__main__":
    mcp.run(transport="stdio")
