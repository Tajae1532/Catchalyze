# seed.py
import json, requests, time
from datetime import datetime, timezone

MCP_URL = "http://localhost:8000/mcp"

def _parse_sse(text: str):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    data_lines = [ln[6:].strip() for ln in lines if ln.startswith("data: ")]
    if not data_lines:
        return None
    try:
        return json.loads(data_lines[-1])
    except Exception:
        return None

def rpc(method, params=None, _id=1):
    headers = {
        "Accept": "text/event-stream, application/json",
        "Content-Type": "application/json",
    }
    payload = {"jsonrpc": "2.0", "id": _id, "method": method}
    if params is not None:
        payload["params"] = params
    r = requests.post(MCP_URL, headers=headers, json=payload, timeout=45)
    body = _parse_sse(r.text) or (r.json() if r.headers.get("content-type","").lower().startswith("application/json") else None)
    if body is None:
        raise RuntimeError(f"Bad response: {r.status_code}\n{r.text[:400]}")
    if "error" in body:
        raise RuntimeError(json.dumps(body["error"], indent=2))
    return body["result"]

now_iso = datetime.now(timezone.utc).isoformat()

# 1) Seed a Zendesk ticket through your tool
ticket_payload = {
    "ticket": {
        "id": "ZD-DEMO-1",
        "title": "Billing page error on checkout",
        "description": "Customers report a bad experience and are frustrated: cannot apply coupon.",
        "latest_public_comment": "Still broken for EU users — awful flow.",
        "status": "open",
        "priority": "high",
        "requester": {"id": "cust-101", "email": "demo@example.com", "name": "Demo User"},
        "tags": ["billing","coupon","checkout"],
        "created_at": now_iso,
        "updated_at": now_iso
    }
}

print("Seeding Zendesk ticket…")
print(
    rpc("tools/call", {
        "name": "process_zendesk_webhook",
        "arguments": {"webhook_data": ticket_payload}
    })
)

# 2) Seed a Slack message through your tool
ts = str(time.time())  # Slack message id format
slack_payload = {
    "type": "event_callback",
    "event": {
        "type": "message",
        "channel": "C-DEMO",
        "ts": ts,
        "user": "U-DEMO",
        "text": "This release feels terrible, users hate the new billing UX.",
    }
}

print("Seeding Slack message…")
print(
    rpc("tools/call", {
        "name": "process_slack_webhook",
        "arguments": {"webhook_data": slack_payload}
    })
)

print("Done.")
