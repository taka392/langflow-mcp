"""Langflow HTTP API client for MCP tools."""
from __future__ import annotations

import os
import urllib.parse
from typing import Any, Dict, List, Optional

import requests

REQUEST_TIMEOUT = 30
DEFAULT_BASE_URL = "http://127.0.0.1:7860"


class LangflowError(RuntimeError):
    """Raised when Langflow API returns an error or invalid response."""


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()


class LangflowClient:
    """Langflow API v1 client.

    Environment variables (via MCP env block):
    - LANGFLOW_BASE_URL: e.g. http://192.168.11.34:7860
    - LANGFLOW_API_KEY: optional; if absent, auto-generate per session
    - LANGFLOW_AUTO_LOGIN: true/false (default true)
    - LANGFLOW_AUTO_API_KEY_NAME: API key label to create (default cursor-mcp)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        auto_login: Optional[bool] = None,
    ) -> None:
        self.base_url = (base_url or _env("LANGFLOW_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        if not self.base_url:
            raise LangflowError("LANGFLOW_BASE_URL must be set.")

        if auto_login is None:
            auto_login = _env("LANGFLOW_AUTO_LOGIN", "true").lower() in ("1", "true", "yes")
        self.auto_login = bool(auto_login)

        self._session = requests.Session()
        self._bearer_token: Optional[str] = None
        self._api_key = api_key or _env("LANGFLOW_API_KEY") or None
        self._auto_api_key_name = _env("LANGFLOW_AUTO_API_KEY_NAME", "cursor-mcp") or "cursor-mcp"

        if self._api_key:
            self._session.headers["x-api-key"] = self._api_key

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        if not path.startswith("/"):
            path = "/" + path
        url = f"{self.base_url}{path}"

        merged_headers: Dict[str, str] = {}
        if headers:
            merged_headers.update(headers)

        try:
            resp = self._session.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=merged_headers or None,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise LangflowError(f"Network error on {method} {path}: {exc}") from exc

        content_type = resp.headers.get("content-type", "")
        payload: Any
        if "application/json" in content_type:
            try:
                payload = resp.json()
            except ValueError as exc:
                raise LangflowError(
                    f"Invalid JSON response ({resp.status_code}) on {path}: {resp.text[:800]}"
                ) from exc
        else:
            payload = resp.text

        if resp.status_code >= 400:
            raise LangflowError(f"{resp.status_code} on {method} {path}: {payload}")

        return payload

    def _auto_login_token(self) -> str:
        if self._bearer_token:
            return self._bearer_token

        if not self.auto_login:
            raise LangflowError(
                "No LANGFLOW_API_KEY provided and LANGFLOW_AUTO_LOGIN=false; cannot authenticate."
            )

        payload = self._request("GET", "/api/v1/auto_login")
        if not isinstance(payload, dict):
            raise LangflowError(f"Unexpected /api/v1/auto_login payload: {payload!r}")

        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise LangflowError(f"Missing access_token in /api/v1/auto_login payload: {payload!r}")

        self._bearer_token = token
        return token

    def ensure_api_key(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Ensure API key is available for run/process endpoints."""
        if self._api_key:
            return {"api_key": self._api_key, "source": "env"}

        token = self._auto_login_token()
        key_name = name or self._auto_api_key_name
        payload = self._request(
            "POST",
            "/api/v1/api_key/",
            json_body={"name": key_name},
            headers={"Authorization": f"Bearer {token}"},
        )
        if not isinstance(payload, dict) or not payload.get("api_key"):
            raise LangflowError(f"Unexpected API key create payload: {payload!r}")

        self._api_key = str(payload["api_key"])
        self._session.headers["x-api-key"] = self._api_key
        return payload

    def verify(self) -> Dict[str, Any]:
        """Return Langflow version and package information."""
        payload = self._request("GET", "/api/v1/version")
        if isinstance(payload, dict):
            return payload
        raise LangflowError(f"Unexpected /api/v1/version payload: {payload!r}")

    def list_flows(self) -> List[Dict[str, Any]]:
        """List available flows (requires API key or auto-login bootstrap)."""
        if not self._api_key:
            self.ensure_api_key()
        payload = self._request("GET", "/api/v1/flows/")
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            return payload["items"]
        raise LangflowError(f"Unexpected /api/v1/flows payload: {payload!r}")

    def get_flow(self, flow_id: str) -> Dict[str, Any]:
        """Get one flow by ID."""
        if not self._api_key:
            self.ensure_api_key()
        flow_id_enc = urllib.parse.quote(flow_id, safe="")
        payload = self._request("GET", f"/api/v1/flows/{flow_id_enc}")
        if isinstance(payload, dict):
            return payload
        raise LangflowError(f"Unexpected flow payload: {payload!r}")

    def run_flow(
        self,
        flow_id_or_name: str,
        *,
        input_value: str,
        input_type: str = "chat",
        output_type: str = "chat",
        output_component: str = "",
        session_id: Optional[str] = None,
        tweaks: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run a flow via simplified run endpoint."""
        if not self._api_key:
            self.ensure_api_key()
        flow_enc = urllib.parse.quote(flow_id_or_name, safe="")
        payload = self._request(
            "POST",
            f"/api/v1/run/{flow_enc}",
            json_body={
                "input_value": input_value,
                "input_type": input_type,
                "output_type": output_type,
                "output_component": output_component,
                "session_id": session_id,
                "tweaks": tweaks,
            },
        )
        if isinstance(payload, dict):
            return payload
        raise LangflowError(f"Unexpected run payload: {payload!r}")

    def create_flow(
        self,
        *,
        name: str,
        description: str = "",
        source_flow_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        folder_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new flow (POST /api/v1/flows/).

        Either ``source_flow_id`` (clone) or ``data`` (raw flow graph) should be
        provided. When both are provided, ``data`` takes precedence.
        """
        if not self._api_key:
            self.ensure_api_key()

        payload: Dict[str, Any]
        if data is not None:
            payload = {
                "name": name,
                "description": description,
                "data": data,
                "is_component": False,
                "webhook": False,
                "endpoint_name": None,
                "folder_id": folder_id,
            }
        elif source_flow_id:
            original = self.get_flow(source_flow_id)
            payload = {
                "name": name,
                "description": description or str(original.get("description") or ""),
                "data": original.get("data"),
                "is_component": bool(original.get("is_component", False)),
                "webhook": bool(original.get("webhook", False)),
                "endpoint_name": original.get("endpoint_name"),
                "folder_id": folder_id if folder_id is not None else original.get("folder_id"),
            }
        else:
            raise LangflowError("Either source_flow_id or data is required for create_flow.")

        created = self._request("POST", "/api/v1/flows/", json_body=payload)
        if isinstance(created, dict):
            return created
        raise LangflowError(f"Unexpected create flow payload: {created!r}")
