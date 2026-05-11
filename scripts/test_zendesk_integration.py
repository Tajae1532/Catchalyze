#!/usr/bin/env python3
"""
Test script for Zendesk integration endpoints
Tests both historical sync and webhook processing
"""

import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"


async def test_health_endpoint():
    """Test health endpoint to verify Zendesk configuration"""
    print("Testing health endpoint...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed")
            print(f"   - Zendesk configured: {data.get('zendesk_configured', False)}")
            print(f"   - Supabase connected: {data.get('supabase_connected', False)}")
            print(f"   - Available tools: {len(data.get('available_tools', []))}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False


async def test_zendesk_sync():
    """Test Zendesk historical sync endpoint"""
    print("\nTesting Zendesk historical sync...")
    
    async with httpx.AsyncClient() as client:
        # Test with a small number of days for quick testing
        response = await client.get(f"{BASE_URL}/zendesk/sync/start?days_back=30")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Zendesk sync started successfully")
            print(f"   Status: {data.get('status')}")
            print(f"   Message: {data.get('message')}")
            print(f"   Started at: {data.get('started_at')}")
            return True
        else:
            print(f"❌ Zendesk sync failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False


async def test_zendesk_webhook():
    """Test Zendesk webhook endpoint with sample data"""
    print("\nTesting Zendesk webhook processing...")
    
    # Sample Zendesk webhook payload
    sample_webhook_data = {
        "ticket": {
            "id": 12345,
            "subject": "Test ticket from webhook",
            "description": "This is a test ticket created to verify webhook processing. The customer seems frustrated with the service.",
            "status": "open",
            "priority": "high",
            "requester_id": 67890,
            "requester": {
                "id": 67890,
                "email": "test.customer@example.com",
                "name": "Test Customer"
            },
            "tags": ["test", "webhook", "urgent"],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/zendesk/webhooks/tickets",
            json=sample_webhook_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Zendesk webhook processed successfully")
            print(f"   Status: {data.get('status')}")
            print(f"   Ticket ID: {data.get('ticket_id')}")
            print(f"   Customer ID: {data.get('customer_id')}")
            print(f"   Sentiment Score: {data.get('sentiment_score')}")
            return True
        else:
            print(f"❌ Zendesk webhook failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False


import json # Ensure the json module is imported

async def test_ticket_analysis():
    """Test the analyze_zendesk_tickets MCP tool via HTTP"""
    print("\nTesting ticket analysis...")
    
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "session": {
                "id": "test-session",
                "name": "test-session"
            },
            "name": "analyze_zendesk_tickets",
            "arguments": {
                "days_back": 30 # Keep as integer
            }
        }
    }
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.post(
            f"{BASE_URL}/mcp/",
            json=mcp_request,
            headers={
                "Content-Type": "application/json",
                # <--- PUT BACK BOTH ACCEPT TYPES AS THE SERVER REQUIRES IT
                "Accept": "application/json, text/event-stream" 
            }
        )

        if response.status_code == 200:
            try:
                json_payload_str = None
                for line in response.text.splitlines():
                    if line.startswith("data: "):
                        json_payload_str = line[len("data: "):]
                        break
                
                if not json_payload_str:
                    print(f"❌ Ticket analysis failed: No 'data:' line found in SSE response.")
                    print(f"   Full response text: '{response.text}'")
                    return False

                data = json.loads(json_payload_str) # Parse the extracted JSON string
                
                # Check for a JSON-RPC error field first within the parsed data
                if "error" in data:
                    print(f"❌ Ticket analysis failed (JSON-RPC error): {data.get('error')}")
                    return False
                
                # The actual tool result is still nested under 'result.structuredContent'
                result = data.get("result", {}).get("structuredContent", {})
                
                if not result:
                    print(f"❌ Ticket analysis failed: 'structuredContent' not found or empty in response.")
                    print(f"   Full response data: {data}")
                    return False

                print(f"✅ Ticket analysis completed")
                print(f"   Total tickets: {result.get('total_tickets', 0)}")
                print(f"   Average sentiment: {result.get('average_sentiment', 0)}")
                print(f"   Status breakdown: {result.get('status_breakdown', {})}")
                print(f"   Priority breakdown: {result.get('priority_breakdown', {})}")
                return True
            except json.JSONDecodeError as e:
                print(f"❌ Ticket analysis failed: JSONDecodeError - {e}")
                print(f"   Response text was: '{response.text}'")
                return False
        else:
            print(f"❌ Ticket analysis request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False


async def main():
    """Run all Zendesk integration tests"""
    print("🧪 Starting Zendesk Integration Tests")
    print("=" * 50)
    
    tests = [
        test_health_endpoint,
        test_zendesk_sync,
        test_zendesk_webhook,
        test_ticket_analysis
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All Zendesk integration tests passed!")
    else:
        print("⚠️  Some tests failed. Check configuration and logs.")
    
    return all(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)