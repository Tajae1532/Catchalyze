# mcp_client/client.py
import asyncio
import itertools
import json
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from jsonschema import validate as jsonschema_validate, ValidationError

load_dotenv()

MCP_BASE_URL = "http://localhost:8000/mcp"
_id_counter = itertools.count(1)
_session_id: Optional[str] = None


# -------------------- Base RPC & Notify Helpers --------------------
async def notify(method: str, params: Dict | List | None = None) -> None:
    payload = {"jsonrpc": "2.0", "method": method, "params": params or {}}
    headers = _get_headers()
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        r = await client.post(MCP_BASE_URL, json=payload, headers=headers)
        r.raise_for_status()


async def rpc(method: str, params: Dict | List | None = None) -> Dict[str, Any]:
    global _session_id
    payload = {"jsonrpc": "2.0", "id": next(_id_counter), "method": method}
    if params is not None:
        payload["params"] = params

    headers = _get_headers()

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        r = await client.post(MCP_BASE_URL, json=payload, headers=headers)
        print(f"POST {r.request.url} → {r.status_code}")

        r.raise_for_status()

        if _session_id is None:
            _session_id = r.headers.get("mcp-session-id")

        if r.headers.get("content-type", "").startswith("text/event-stream"):
            for line in r.text.splitlines():
                if line.startswith("data:"):
                    data = json.loads(line[5:].strip())
                    break
            else:
                raise RuntimeError("No data: line found in SSE response")
        else:
            data = r.json()

        if "error" in data:
            err = data["error"]
            raise RuntimeError(f"RPC error {err.get('code')}: {err.get('message')}")
        return data["result"]


def _get_headers() -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if _session_id:
        headers["mcp-session-id"] = _session_id
    return headers


# -------------------- MCP Tool Call & Schema Validation --------------------
async def tools_list() -> List[Dict[str, Any]]:
    res = await rpc("tools/list")
    return [
        item["tool_definition"]
        for item in res.get("content", [])
        if item.get("type") == "tool_definition"
    ]


async def tools_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    res = await rpc("tools/call", {"name": name, "arguments": arguments})
    text_chunks = [
        item["text"] for item in res.get("content", []) if item.get("type") == "text"
    ]
    if text_chunks:
        joined = "".join(text_chunks)
        try:
            return json.loads(joined)
        except json.JSONDecodeError:
            return {"text_content": joined}
    return res


# -------------------- High-Level MCP Client --------------------
class CustomerWhispererClient:
    def __init__(self):
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
        self._schemas: Dict[str, Dict] = {}

    async def init_session(self):
        await rpc(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "CustomerWhispererClient", "version": "1.0"},
            },
        )
        await notify("notifications/initialized", {})
        print("MCP session initialized.")

    async def get_available_tools(self):
        if self._tools_cache is None:
            res = await rpc("tools/list")

            # Handle current backend format
            if isinstance(res, dict) and "tools" in res and isinstance(res["tools"], list):
                self._tools_cache = res["tools"]
                for t in self._tools_cache:
                    if "outputSchema" in t:
                        self._schemas[t["name"]] = t["outputSchema"]

            # Handle MCP content array format
            elif isinstance(res, dict) and "content" in res:
                self._tools_cache = [
                    item.get("tool_definition", item)
                    for item in res["content"]
                    if item.get("type") == "tool_definition" or "name" in item
                ]
                for t in self._tools_cache:
                    if "schema" in t:
                        self._schemas[t["name"]] = t["schema"]

            # Handle plain list of tools
            elif isinstance(res, list):
                self._tools_cache = res
                for t in self._tools_cache:
                    if "schema" in t:
                        self._schemas[t["name"]] = t["schema"]

            else:
                raise RuntimeError(f"Unexpected tools/list format: {res}")

        return self._tools_cache

    async def call_tool(self, name: str, arguments: Dict[str, Any]):
        result = await tools_call(name, arguments)
        if name in self._schemas:
            try:
                jsonschema_validate(instance=result, schema=self._schemas[name])
                print(f"Output from {name} matches schema.")
            except ValidationError as e:
                print(f"Schema validation failed for {name}: {e.message}")
        else:
            print(f"No schema found for {name}, skipping validation.")
        return result


# -------------------- Smoke Test --------------------
async def main():
    cw = CustomerWhispererClient()

    print("--- Initializing MCP session ---")
    await cw.init_session()

    print("\n--- Fetching Available Tools ---")
    tools = await cw.get_available_tools()
    for t in tools:
        print(f"- {t['name']}: {t.get('description', '')}")

    if tools:
        print("\n--- Calling First Tool for Test ---")
        tool_name = tools[0]["name"]
        result = await cw.call_tool(tool_name, {})
        print(json.dumps(result, indent=2)[:500], "…")


if __name__ == "__main__":
    asyncio.run(main())
