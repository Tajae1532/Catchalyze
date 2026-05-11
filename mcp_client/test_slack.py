#!/usr/bin/env python3
"""
Test script with completely new content - API and Mobile issues + Evidence Details Testing
"""

import asyncio
import httpx
import json
from datetime import datetime, timedelta
import random
import time

BASE_URL = "http://localhost:8000"
CHANNEL_ID = "testinggabriel"  # Target channel for testing

# Sample users for the messages
USERS = [
    "U1234567890",  # Sarah Johnson
    "U2345678901",  # Mike Chen  
    "U3456789012",  # Emily Rodriguez
    "U4567890123",  # David Kim
]

# API timeout issues - COMPLETELY NEW CONTENT
API_ISSUES = [
    "API endpoints are timing out constantly. Getting 504 gateway timeout errors everywhere.",
    "REST API is completely unresponsive. All requests are hanging for minutes before failing.",
    "API rate limiting is broken. Even single requests are being rejected with timeout errors."
]

# Mobile app crash problems - COMPLETELY NEW CONTENT
MOBILE_ISSUES = [
    "Mobile app keeps crashing on startup. Users can't even get past the loading screen.",
    "iOS app is completely broken. Crashes immediately when trying to open any feature.",
    "Android app freezes and crashes constantly. Users are unable to use basic functionality."
]

# NEW: Database connection issues - for testing evidence details
DATABASE_ISSUES = [
    "Database connection keeps failing. Getting connection timeout errors when trying to save data.",
    "PostgreSQL database is unresponsive. All database queries are timing out after 30 seconds.",
    "Database connection pool is exhausted. Unable to get new connections to process requests.",
    "Database performance is terrible. Simple queries are taking minutes to complete."
]

def generate_slack_timestamp():
    """Generate a valid Slack timestamp"""
    current_time = time.time()
    offset = random.uniform(0, 1)
    return str(current_time + offset)

async def send_slack_message(user_id: str, text: str, message_id: str = None):
    """Send a single Slack message to the testinggabriel channel"""
    
    if not message_id:
        message_id = generate_slack_timestamp()
    
    # Create webhook payload
    webhook_data = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "channel": CHANNEL_ID,
            "user": user_id,
            "text": text,
            "ts": message_id,
            "event_ts": message_id,
            "channel_type": "channel"
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/slack/events",
                json=webhook_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Message sent successfully")
                print(f"   User: {user_id}")
                print(f"   Text: {text[:60]}...")
                print(f"   Sentiment: {data.get('sentiment_score', 'N/A')}")
                return True
            else:
                print(f"❌ Message failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Message failed with exception: {e}")
            return False

async def send_api_issues():
    """Send API timeout complaint messages"""
    print("\n🔗 Sending API timeout issue messages...")
    
    success_count = 0
    for i, complaint in enumerate(API_ISSUES):
        user_id = USERS[i % len(USERS)]
        
        success = await send_slack_message(user_id, complaint)
        if success:
            success_count += 1
        
        # Small delay between messages
        await asyncio.sleep(2)
    
    print(f"📊 Sent {success_count}/3 API issue messages")
    return success_count

async def send_mobile_issues():
    """Send mobile app crash complaint messages"""
    print("\n📱 Sending mobile app crash issue messages...")
    
    success_count = 0
    for i, complaint in enumerate(MOBILE_ISSUES):
        user_id = USERS[i % len(USERS)]
        
        success = await send_slack_message(user_id, complaint)
        if success:
            success_count += 1
        
        # Small delay between messages
        await asyncio.sleep(2)
    
    print(f"📊 Sent {success_count}/3 mobile issue messages")
    return success_count

async def send_database_issues():
    """Send database connection complaint messages"""
    print("\n🗄️ Sending database connection issue messages...")
    
    success_count = 0
    for i, complaint in enumerate(DATABASE_ISSUES):
        user_id = USERS[i % len(USERS)]
        
        success = await send_slack_message(user_id, complaint)
        if success:
            success_count += 1
        
        # Small delay between messages
        await asyncio.sleep(2)
    
    print(f"📊 Sent {success_count}/4 database issue messages")
    return success_count

async def test_trending_topics_detection():
    """Test if the issues are detected as trending topics"""
    print("\n📊 Testing trending topics detection...")
    
    # Wait a moment for processing
    await asyncio.sleep(5)
    
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "detect_trending_topics",
            "arguments": {}
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/mcp/rpc",
                json=mcp_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            )
            
            if response.status_code == 200:
                # Handle both JSON and SSE responses
                content_type = response.headers.get('content-type', '')
                
                if 'text/event-stream' in content_type:
                    # Parse SSE response
                    for line in response.text.splitlines():
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])  # Remove 'data: ' prefix
                                if 'result' in data:
                                    trends = data['result'].get('trends', [])
                                    print(f"✅ Found {len(trends)} trending topics")
                                    
                                    # Look for API related topics
                                    api_topics = [t for t in trends if any(
                                        keyword in t.get('title', '').lower() or 
                                        keyword in ' '.join(t.get('keywords', [])).lower()
                                        for keyword in ['api', 'timeout', 'endpoint', 'gateway', 'rate']
                                    )]
                                    
                                    # Look for mobile related topics
                                    mobile_topics = [t for t in trends if any(
                                        keyword in t.get('title', '').lower() or 
                                        keyword in ' '.join(t.get('keywords', [])).lower()
                                        for keyword in ['mobile', 'app', 'crash', 'ios', 'android', 'startup']
                                    )]
                                    
                                    # Look for database related topics
                                    database_topics = [t for t in trends if any(
                                        keyword in t.get('title', '').lower() or 
                                        keyword in ' '.join(t.get('keywords', [])).lower()
                                        for keyword in ['database', 'connection', 'postgresql', 'pool', 'query']
                                    )]
                                    
                                    if api_topics:
                                        print(f"🔗 Found API timeout trending topic!")
                                        for topic in api_topics:
                                            print(f"   Title: {topic.get('title')}")
                                            print(f"   Keywords: {topic.get('keywords')}")
                                            print(f"   Count today: {topic.get('count_today')}")
                                            print(f"   Z-score: {topic.get('z_score')}")
                                            print(f"   Evidence IDs: {topic.get('evidence_ids', {})}")
                                    
                                    if mobile_topics:
                                        print(f"📱 Found mobile app crash trending topic!")
                                        for topic in mobile_topics:
                                            print(f"   Title: {topic.get('title')}")
                                            print(f"   Keywords: {topic.get('keywords')}")
                                            print(f"   Count today: {topic.get('count_today')}")
                                            print(f"   Z-score: {topic.get('z_score')}")
                                            print(f"   Evidence IDs: {topic.get('evidence_ids', {})}")
                                    
                                    if database_topics:
                                        print(f"🗄️ Found database connection trending topic!")
                                        for topic in database_topics:
                                            print(f"   Title: {topic.get('title')}")
                                            print(f"   Keywords: {topic.get('keywords')}")
                                            print(f"   Count today: {topic.get('count_today')}")
                                            print(f"   Z-score: {topic.get('z_score')}")
                                            print(f"   Evidence IDs: {topic.get('evidence_ids', {})}")
                                            
                                            # Test evidence details for this topic
                                            if topic.get('evidence_ids'):
                                                await test_evidence_details(topic.get('evidence_ids'))
                                    
                                    if not api_topics and not mobile_topics and not database_topics:
                                        print("⚠️  No API, mobile, or database trending topics detected yet")
                                        # Print all topics for debugging
                                        for i, topic in enumerate(trends):
                                            print(f"   Topic {i+1}: {topic.get('title', 'No title')}")
                                            print(f"     Keywords: {topic.get('keywords', [])}")
                                            print(f"     Count today: {topic.get('count_today', 'N/A')}")
                                            print(f"     Evidence IDs: {topic.get('evidence_ids', {})}")
                                    
                                    return trends
                            except json.JSONDecodeError:
                                continue
                else:
                    # Parse JSON response
                    data = response.json()
                    trends = data.get('result', {}).get('trends', [])
                    print(f"✅ Found {len(trends)} trending topics")
                    
                    # Look for API related topics
                    api_topics = [t for t in trends if any(
                        keyword in t.get('title', '').lower() or 
                        keyword in ' '.join(t.get('keywords', [])).lower()
                        for keyword in ['api', 'timeout', 'endpoint', 'gateway', 'rate']
                    )]
                    
                    # Look for mobile related topics
                    mobile_topics = [t for t in trends if any(
                        keyword in t.get('title', '').lower() or 
                        keyword in ' '.join(t.get('keywords', [])).lower()
                        for keyword in ['mobile', 'app', 'crash', 'ios', 'android', 'startup']
                    )]
                    
                    # Look for database related topics
                    database_topics = [t for t in trends if any(
                        keyword in t.get('title', '').lower() or 
                        keyword in ' '.join(t.get('keywords', [])).lower()
                        for keyword in ['database', 'connection', 'postgresql', 'pool', 'query']
                    )]
                    
                    if api_topics:
                        print(f"🔗 Found API timeout trending topic!")
                        for topic in api_topics:
                            print(f"   Title: {topic.get('title')}")
                            print(f"   Keywords: {topic.get('keywords')}")
                            print(f"   Count today: {topic.get('count_today')}")
                            print(f"   Evidence IDs: {topic.get('evidence_ids', {})}")
                    
                    if mobile_topics:
                        print(f"📱 Found mobile app crash trending topic!")
                        for topic in mobile_topics:
                            print(f"   Title: {topic.get('title')}")
                            print(f"   Keywords: {topic.get('keywords')}")
                            print(f"   Count today: {topic.get('count_today')}")
                            print(f"   Evidence IDs: {topic.get('evidence_ids', {})}")
                    
                    if database_topics:
                        print(f"🗄️ Found database connection trending topic!")
                        for topic in database_topics:
                            print(f"   Title: {topic.get('title')}")
                            print(f"   Keywords: {topic.get('keywords')}")
                            print(f"   Count today: {topic.get('count_today')}")
                            print(f"   Evidence IDs: {topic.get('evidence_ids', {})}")
                            
                            # Test evidence details for this topic
                            if topic.get('evidence_ids'):
                                await test_evidence_details(topic.get('evidence_ids'))
                    
                    if not api_topics and not mobile_topics and not database_topics:
                        print("⚠️  No API, mobile, or database trending topics detected yet")
                        # Print all topics for debugging
                        for i, topic in enumerate(trends):
                            print(f"   Topic {i+1}: {topic.get('title', 'No title')}")
                            print(f"     Keywords: {topic.get('keywords', [])}")
                            print(f"     Count today: {topic.get('count_today', 'N/A')}")
                            print(f"     Evidence IDs: {topic.get('evidence_ids', {})}")
                    
                    return trends
            else:
                print(f"❌ Trending topics detection failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Trending topics detection failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False

async def test_evidence_details(evidence_ids):
    """Test the get_evidence_details MCP tool"""
    print(f"\n🔍 Testing evidence details for evidence IDs: {evidence_ids}")
    
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get_evidence_details",
            "arguments": {
                "evidence_ids": evidence_ids
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/mcp/rpc",
                json=mcp_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            )
            
            if response.status_code == 200:
                # Handle both JSON and SSE responses
                content_type = response.headers.get('content-type', '')
                
                if 'text/event-stream' in content_type:
                    # Parse SSE response
                    for line in response.text.splitlines():
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])  # Remove 'data: ' prefix
                                if 'result' in data:
                                    evidence = data['result']
                                    print(f"✅ Evidence details retrieved successfully!")
                                    
                                    # Display ticket evidence
                                    tickets = evidence.get('tickets', [])
                                    if tickets:
                                        print(f"   📋 Ticket Evidence ({len(tickets)} tickets):")
                                        for ticket in tickets[:3]:  # Show first 3
                                            print(f"      • Ticket #{ticket.get('zendesk_ticket_id')}: {ticket.get('subject', 'No subject')[:50]}...")
                                            print(f"        Created: {ticket.get('created_at')}")
                                    
                                    # Display Slack message evidence
                                    slack_messages = evidence.get('slack_messages', [])
                                    if slack_messages:
                                        print(f"   💬 Slack Evidence ({len(slack_messages)} messages):")
                                        for message in slack_messages[:3]:  # Show first 3
                                            print(f"      • Channel {message.get('slack_channel_id')}: {message.get('text', 'No text')[:50]}...")
                                            print(f"        Sent: {message.get('created_at')}")
                                    
                                    if not tickets and not slack_messages:
                                        print("   ⚠️ No evidence details found")
                                    
                                    return evidence
                            except json.JSONDecodeError:
                                continue
                else:
                    # Parse JSON response
                    data = response.json()
                    evidence = data.get('result', {})
                    print(f"✅ Evidence details retrieved successfully!")
                    
                    # Display ticket evidence
                    tickets = evidence.get('tickets', [])
                    if tickets:
                        print(f"   📋 Ticket Evidence ({len(tickets)} tickets):")
                        for ticket in tickets[:3]:  # Show first 3
                            print(f"      • Ticket #{ticket.get('zendesk_ticket_id')}: {ticket.get('subject', 'No subject')[:50]}...")
                            print(f"        Created: {ticket.get('created_at')}")
                    
                    # Display Slack message evidence
                    slack_messages = evidence.get('slack_messages', [])
                    if slack_messages:
                        print(f"   💬 Slack Evidence ({len(slack_messages)} messages):")
                        for message in slack_messages[:3]:  # Show first 3
                            print(f"      • Channel {message.get('slack_channel_id')}: {message.get('text', 'No text')[:50]}...")
                            print(f"        Sent: {message.get('created_at')}")
                    
                    if not tickets and not slack_messages:
                        print("   ⚠️ No evidence details found")
                    
                    return evidence
            else:
                print(f"❌ Evidence details request failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Evidence details request failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Send test messages and test trend detection with evidence details"""
    print("📊 API, Mobile & Database Issues Trend Detection + Evidence Test")
    print("=" * 65)
    print(f"Target channel: #{CHANNEL_ID}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Send API issue messages (first trend)
    api_success = await send_api_issues()
    
    # Wait a bit between trends
    await asyncio.sleep(3)
    
    # Send mobile issue messages (second trend)
    mobile_success = await send_mobile_issues()
    
    # Wait a bit between trends
    await asyncio.sleep(3)
    
    # Send database issue messages (third trend) - this will trigger evidence details testing
    database_success = await send_database_issues()
    
    if api_success > 0 or mobile_success > 0 or database_success > 0:
        print("\n⏳ Waiting for processing...")
        await asyncio.sleep(15)  # Wait for processing
        
        # Test trending topics detection (includes evidence details testing)
        trends = await test_trending_topics_detection()
        
        # If no trends found, wait a bit more and try again
        if not trends or len(trends) == 0:
            print("\n⏳ Waiting additional time for topic clustering...")
            await asyncio.sleep(30)
            await test_trending_topics_detection()
    
    print("\n" + "=" * 65)
    print("✅ Test completed!")
    print("Check your dashboard to see if the API, mobile, and database issues appear as trending topics")
    print("Evidence details should have been tested for any detected database trends")

if __name__ == "__main__":
    asyncio.run(main())