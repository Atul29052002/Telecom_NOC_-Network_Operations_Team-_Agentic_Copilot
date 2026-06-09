from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn


app = FastAPI(title="Telecom MCP Server")


class ToolRequest(BaseModel):
    target: str
    action: str


@app.post("/router_reset")
def router_reset(req: ToolRequest) -> dict[str, Any]:
    return {"status": "success", "tool": "router_reset", "target": req.target, "message": f"Router reset completed for {req.target}"}


@app.post("/interface_bounce")
def interface_bounce(req: ToolRequest) -> dict[str, Any]:
    return {"status": "success", "tool": "interface_bounce", "target": req.target, "message": f"Interface bounce completed for {req.target}"}


@app.post("/service_restart")
def service_restart(req: ToolRequest) -> dict[str, Any]:
    return {"status": "success", "tool": "service_restart", "target": req.target, "message": f"Service restart completed for {req.target}"}


def handle_tool(tool_name: str, target: str = "Edge Router") -> dict[str, Any]:
    mapping = {
        "router_reset": router_reset(ToolRequest(target=target, action="reset")),
        "interface_bounce": interface_bounce(ToolRequest(target=target, action="bounce")),
        "service_restart": service_restart(ToolRequest(target=target, action="restart")),
    }
    return mapping.get(tool_name, {"status": "error", "message": f"Unknown tool {tool_name}"})


if __name__ == "__main__":
    uvicorn.run("app.mcp_server:app", host="0.0.0.0", port=9000, reload=False)
