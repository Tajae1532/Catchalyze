import requests
import json
import uuid

MCP_URL = "http://localhost:8000"  # unchanged
MODEL_MINI = "gpt-4o-mini"
MODEL_GPT5 = "gpt-5"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"
}

def rpc(method, params):
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": method,
        "params": params
    }

    r = requests.post(f"{MCP_URL}/mcp", json=payload, headers=HEADERS)
    txt = r.text.strip()

    # Detect SSE anywhere, not just at start
    if "event: message" in txt and "data:" in txt:
        data_line = next((line for line in txt.splitlines() if line.startswith("data: ")), None)
        if not data_line:
            raise RuntimeError(f"Unexpected SSE body:\n{txt}")
        return json.loads(data_line[6:])

    # Otherwise, try normal JSON
    try:
        return r.json()
    except Exception:
        print("\n--- RAW RESPONSE ---")
        print(r.status_code, r.headers)
        print(txt)
        raise

def call_generate(model):
    return rpc("tools/call", {
        "name": "generate_customer_insights",
        "arguments": {
            "llm_model": model,  # matches server signature
            "time_range": "7d"
        }
    })

if __name__ == "__main__":
    print(f"--- Running with {MODEL_MINI} ---")
    mini = call_generate(MODEL_MINI)
    print(json.dumps(mini, indent=2))

    print(f"\n--- Running with {MODEL_GPT5} ---")
    g5 = call_generate(MODEL_GPT5)
    print(json.dumps(g5, indent=2))

    print("\n=== Side-by-side titles ===")
    if not mini.get("no_insight") and not g5.get("no_insight"):
        for m_title, g5_title in zip(mini.get("titles", []), g5.get("titles", [])):
            print(f"{m_title}  |  {g5_title}")
