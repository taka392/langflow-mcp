"""Langflow MCP server (FastMCP)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from .client import LangflowClient, LangflowError

mcp = FastMCP("langflow")


def _client() -> LangflowClient:
    try:
        return LangflowClient()
    except LangflowError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool()
def verify() -> Dict[str, Any]:
    """Verify Langflow API connectivity (GET /api/v1/version)."""
    return _client().verify()


@mcp.tool()
def ensure_api_key(name: Optional[str] = None) -> Dict[str, Any]:
    """Create/reuse API key for MCP session to enable flow execution."""
    raw = _client().ensure_api_key(name=name)
    safe = dict(raw)
    key = safe.get("api_key")
    if isinstance(key, str) and key:
        safe["api_key_preview"] = key[:10] + "..."
        safe.pop("api_key", None)
    return safe


@mcp.tool()
def list_flows() -> List[Dict[str, Any]]:
    """List all flows (GET /api/v1/flows/)."""
    return _client().list_flows()


@mcp.tool()
def get_flow(flow_id: str) -> Dict[str, Any]:
    """Get one flow by ID (GET /api/v1/flows/{flow_id})."""
    return _client().get_flow(flow_id)


@mcp.tool()
def run_flow(
    flow_id_or_name: str,
    input_value: str,
    input_type: str = "chat",
    output_type: str = "chat",
    output_component: str = "",
    session_id: Optional[str] = None,
    tweaks: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run a flow with Langflow simplified API (POST /api/v1/run/{flow_id_or_name})."""
    return _client().run_flow(
        flow_id_or_name,
        input_value=input_value,
        input_type=input_type,
        output_type=output_type,
        output_component=output_component,
        session_id=session_id,
        tweaks=tweaks,
    )


@mcp.tool()
def create_flow(
    name: str,
    description: str = "",
    source_flow_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    folder_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new flow in Langflow (POST /api/v1/flows/).

    Args:
        name: New flow name shown in GUI.
        description: Flow description.
        source_flow_id: Optional existing flow ID to clone.
        data: Optional raw flow graph payload (takes precedence over source clone).
        folder_id: Optional folder ID for placement.
    """
    return _client().create_flow(
        name=name,
        description=description,
        source_flow_id=source_flow_id,
        data=data,
        folder_id=folder_id,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
