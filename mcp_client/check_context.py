# mcp_client/check_context.py
import json, requests
MCP_URL = "http://localhost:8000/mcp"
HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}

def rpc(method, params=None, _id=1):
    payload = {"jsonrpc":"2.0","id":_id,"method":method}
    if params is not None: payload["params"]=params
    r = requests.post(MCP_URL, headers=HEADERS, json=payload, timeout=30)
    t = r.text.strip()
    if t.startswith("event:"):
        data_line = [ln for ln in t.splitlines() if ln.startswith("data: ")]
        body = json.loads(data_line[0][6:]) if data_line else {}
    else:
        body = r.json()
    if "error" in body: raise RuntimeError(body["error"])
    return body["result"]

print("--- analyze_zendesk_tickets (7d) ---")
print(rpc("tools/call", {"name":"analyze_zendesk_tickets","arguments":{"days_back":7}}))

print("\n--- analyze_slack_messages (7d) ---")
print(rpc("tools/call", {"name":"analyze_slack_messages","arguments":{"days_back":7}}))
