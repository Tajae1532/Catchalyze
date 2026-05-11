#!/usr/bin/env python3
"""
Test script for Slack integration functionality
"""

import asyncio
import httpx
import json
from datetime import datetime


async def test_slack_endpoints():
    """Test the Slack OAuth and Events API endpoints"""
    base_url = "http://localhost:8000"
    
    print("🔍 Testing Slack Integration Endpoints")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Test health endpoint to check Slack configuration
        try:
            print("1. Testing health endpoint...")
            response = await client.get(f"{base_url}/health")
            health_data = response.json()
            
            print(f"   Status: {response.status_code}")
            print(f"   Slack configured: {health_data.get('slack_configured', False)}")
            
            if not health_data.get('slack_configured'):
                print("   ⚠️  Slack not configured - check environment variables")
            else:
                print("   ✅ Slack configuration detected")
            
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
        
        # Test OAuth start endpoint (should redirect)
        try:
            print("\n2. Testing OAuth start endpoint...")
            response = await client.get(f"{base_url}/slack/oauth/start", follow_redirects=False)
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 307:
                redirect_url = response.headers.get('location', '')
                if 'slack.com/oauth/v2/authorize' in redirect_url:
                    print("   ✅ OAuth redirect URL looks correct")
                    print(f"   Redirect to: {redirect_url[:80]}...")
                else:
                    print(f"   ⚠️  Unexpected redirect: {redirect_url}")
            else:
                print(f"   ❌ Expected redirect (307), got {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ OAuth start test failed: {e}")
        
        # Test Events API endpoint with URL verification
        try:
            print("\n3. Testing Events API endpoint (URL verification)...")
            
            verification_payload = {
                "token": "test_token",
                "challenge": "test_challenge_123",
                "type": "url_verification"
            }
            
            # Note: This will fail signature verification in real scenarios
            # but should still handle the JSON parsing

            current_timestamp = int(datetime.now().timestamp())
            headers = {
                "Content-Type": "application/json",
                "X-Slack-Request-Timestamp": str(current_timestamp),
                "X-Slack-Signature": "v0=dummy_signature_for_test" # This will cause a 401 as expected
            }
            response = await client.post(
                f"{base_url}/slack/events",
                json=verification_payload,
                headers=headers
            )
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 401:
                print("   ✅ Signature verification working (expected 401)")
            else:
                print(f"   Response: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Events API test failed: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")
    print("\nNext steps:")
    print("1. Update .env with your actual Slack app credentials")
    print("2. Start the server: uvicorn mcp_server.main:app --reload --port 8000")
    print("3. Visit http://localhost:8000/slack/oauth/start to begin OAuth flow")
    print("4. Configure your Slack app's Event Subscriptions to point to:")
    print("   http://your-domain.com/slack/events")


if __name__ == "__main__":
    asyncio.run(test_slack_endpoints())