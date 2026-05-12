# langflow-mcp

MCP server for **Langflow API v1**. It can verify API connectivity, create/use API keys, list flows, and execute flows.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LANGFLOW_BASE_URL` | yes | Langflow URL, e.g. `http://192.168.11.34:7860` |
| `LANGFLOW_API_KEY` | no | Existing Langflow API key. If omitted, MCP auto-creates one via auto-login. |
| `LANGFLOW_AUTO_LOGIN` | no | `true` (default) to call `/api/v1/auto_login` and bootstrap API key. |
| `LANGFLOW_AUTO_API_KEY_NAME` | no | Name for auto-generated key (default `cursor-mcp`). |

## Tools

- `verify` — `GET /api/v1/version`
- `ensure_api_key` — `POST /api/v1/api_key/` (or reuse env key)
- `list_flows` — `GET /api/v1/flows/`
- `get_flow` — `GET /api/v1/flows/{flow_id}`
- `run_flow` — `POST /api/v1/run/{flow_id_or_name}`
- `create_flow` — `POST /api/v1/flows/` (clone existing flow or pass raw graph data)

## Cursor (`mcp.json`) example

See `examples/cursor_mcp_config.example.json`.

## Check script

```bash
cd projects/langflow-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e .
export LANGFLOW_BASE_URL="http://192.168.11.34:7860"
python -m langflow_mcp.check
```
