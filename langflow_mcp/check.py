"""Smoke test for langflow-mcp."""
from __future__ import annotations

import json
import sys

from .client import LangflowClient, LangflowError


def _dump(label: str, payload: object) -> None:
    print(f"\n=== {label} ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2)[:4000])


def main() -> int:
    try:
        client = LangflowClient()
    except LangflowError as exc:
        print(f"Setup error: {exc}", file=sys.stderr)
        return 1

    try:
        _dump("verify", client.verify())
        key = client.ensure_api_key()
        masked = dict(key)
        if "api_key" in masked:
            api_key = str(masked["api_key"])
            masked["api_key"] = api_key[:10] + "..." if len(api_key) > 10 else "***"
        _dump("ensure_api_key", masked)
        flows = client.list_flows()
        _dump("list_flows", flows[:5])
    except LangflowError as exc:
        print(f"API error: {exc}", file=sys.stderr)
        return 1

    print("\nOK: end-to-end Langflow API access works.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
