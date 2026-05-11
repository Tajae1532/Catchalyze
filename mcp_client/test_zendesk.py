#!/usr/bin/env python3
"""
Test script to create Zendesk tickets for refund issues and shoe page problems
"""

import asyncio
import httpx
import json
from datetime import datetime, timedelta
import random
import time

BASE_URL = "http://localhost:8000"

# Refund Issues - Customer service problems
REFUND_ISSUES = [
    {
        "subject": "Refund request denied without proper explanation",
        "description": "Customer requested a refund for defective product but was denied without any clear reason. The item arrived damaged and doesn't match the description. Customer service is being unhelpful and refusing to process legitimate refund requests.",
        "priority": "high"
    },
    {
        "subject": "Refund processing taking over 30 days - unacceptable",
        "description": "Submitted refund request over a month ago and still haven't received the money back. This is way beyond the promised 5-7 business days. Multiple follow-ups with support team have yielded no results.",
        "priority": "urgent"
    },
    {
        "subject": "Partial refund issued instead of full amount requested",
        "description": "Requested full refund for returned item but only received partial amount. No explanation provided for the deduction. The item was returned in original condition with all packaging and tags intact.",
        "priority": "high"
    },
    {
        "subject": "Refund button not working on order confirmation page",
        "description": "Unable to initiate refund request through the website. The refund button appears to be broken - clicking it does nothing. Have to contact support manually which delays the entire process unnecessarily.",
        "priority": "normal"
    }
]

# Shoe Page Issues - E-commerce problems
SHOE_PAGE_ISSUES = [
    {
        "subject": "Shoe product page completely broken - images not loading",
        "description": "All shoe product pages are displaying broken image placeholders. Cannot see any product photos which makes it impossible to make purchasing decisions. This is affecting the entire footwear category on the website.",
        "priority": "urgent"
    },
    {
        "subject": "Shoe size selector not working - cannot add to cart",
        "description": "Size dropdown menu on shoe pages is non-functional. Cannot select shoe size which prevents adding items to cart. This is blocking all shoe purchases and causing lost sales.",
        "priority": "urgent"
    },
    {
        "subject": "Shoe page showing wrong prices - displaying old sale prices",
        "description": "Shoe product pages are showing outdated sale prices instead of current pricing. Customers are getting confused at checkout when prices change. This pricing inconsistency is causing trust issues.",
        "priority": "high"
    },
    {
        "subject": "Shoe page reviews section completely missing",
        "description": "Customer reviews section has disappeared from all shoe product pages. Reviews are crucial for footwear purchases and customers are complaining about not being able to see feedback from other buyers.",
        "priority": "normal"
    }
]

# Sample customer data
CUSTOMERS = [
    {"name": "Sarah Johnson", "email": "sarah.johnson@acme.com"},
    {"name": "Mike Chen", "email": "mike.chen@techcorp.com"},
    {"name": "Emily Rodriguez", "email": "emily.r@startup.io"},
    {"name": "David Kim", "email": "david.kim@enterprise.net"},
    {"name": "Lisa Thompson", "email": "lisa.t@company.org"},
    {"name": "Alex Wong", "email": "alex.wong@business.co"},
]

async def create_zendesk_ticket(ticket_data: dict, customer_data: dict):
    """Create a single Zendesk ticket via webhook simulation"""
    
    # Generate a unique ticket ID
    ticket_id = random.randint(10000, 99999)
    
    # Create webhook payload that matches Zendesk format
    webhook_data = {
        "ticket": {
            "id": ticket_id,
            "subject": ticket_data["subject"],
            "description": ticket_data["description"],
            "priority": ticket_data["priority"],
            "status": "new",
            "requester": {
                "name": customer_data["name"],
                "email": customer_data["email"]
            },
            "created_at": datetime.now().isoformat() + "Z",
            "updated_at": datetime.now().isoformat() + "Z"
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/zendesk/webhooks/tickets",
                json=webhook_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print(f"✅ Ticket created successfully")
                print(f"   ID: #{ticket_id}")
                print(f"   Subject: {ticket_data['subject'][:60]}...")
                print(f"   Priority: {ticket_data['priority']}")
                print(f"   Customer: {customer_data['name']}")
                return True
            else:
                print(f"❌ Ticket creation failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Ticket creation failed with exception: {e}")
            return False

async def create_refund_issue_tickets():
    """Create refund issue tickets"""
    print("\n💰 Creating refund issue tickets...")
    
    success_count = 0
    for i, ticket_data in enumerate(REFUND_ISSUES):
        customer_data = CUSTOMERS[i % len(CUSTOMERS)]
        
        success = await create_zendesk_ticket(ticket_data, customer_data)
        if success:
            success_count += 1
        
        # Small delay between tickets
        await asyncio.sleep(3)
    
    print(f"📊 Created {success_count}/4 refund issue tickets")
    return success_count

async def create_shoe_page_tickets():
    """Create shoe page issue tickets"""
    print("\n👟 Creating shoe page issue tickets...")
    
    success_count = 0
    for i, ticket_data in enumerate(SHOE_PAGE_ISSUES):
        customer_data = CUSTOMERS[i % len(CUSTOMERS)]
        
        success = await create_zendesk_ticket(ticket_data, customer_data)
        if success:
            success_count += 1
        
        # Small delay between tickets
        await asyncio.sleep(3)
    
    print(f"📊 Created {success_count}/4 shoe page issue tickets")
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
            "arguments": {
                "time_window_minutes": 30  # Longer window for Zendesk tickets
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
                                    trends = data['result'].get('trends', [])
                                    print(f"✅ Found {len(trends)} trending topics")
                                    
                                    # Look for refund related topics
                                    refund_topics = [t for t in trends if any(
                                        keyword in t.get('title', '').lower() or 
                                        keyword in ' '.join(t.get('keywords', [])).lower()
                                        for keyword in ['refund', 'money', 'denied', 'processing', 'return', 'payment']
                                    )]
                                    
                                    # Look for shoe page related topics
                                    shoe_topics = [t for t in trends if any(
                                        keyword in t.get('title', '').lower() or 
                                        keyword in ' '.join(t.get('keywords', [])).lower()
                                        for keyword in ['shoe', 'page', 'broken', 'images', 'size', 'footwear', 'product']
                                    )]
                                    
                                    if refund_topics:
                                        print(f"💰 Found refund issue trending topic!")
                                        for topic in refund_topics:
                                            print(f"   Title: {topic.get('title')}")
                                            print(f"   Keywords: {topic.get('keywords')}")
                                            print(f"   Count: {topic.get('count_in_window')}")
                                            print(f"   Evidence: {topic.get('evidence_ids', {})}")
                                    
                                    if shoe_topics:
                                        print(f"👟 Found shoe page trending topic!")
                                        for topic in shoe_topics:
                                            print(f"   Title: {topic.get('title')}")
                                            print(f"   Keywords: {topic.get('keywords')}")
                                            print(f"   Count: {topic.get('count_in_window')}")
                                            print(f"   Evidence: {topic.get('evidence_ids', {})}")
                                    
                                    if not refund_topics and not shoe_topics:
                                        print("⚠️  No refund or shoe page trending topics detected yet")
                                        # Print all topics for debugging
                                        for i, topic in enumerate(trends):
                                            print(f"   Topic {i+1}: {topic.get('title', 'No title')}")
                                            print(f"     Keywords: {topic.get('keywords', [])}")
                                            print(f"     Count: {topic.get('count_in_window', 'N/A')}")
                                    
                                    return trends
                            except json.JSONDecodeError:
                                continue
                else:
                    # Parse JSON response
                    data = response.json()
                    trends = data.get('result', {}).get('trends', [])
                    print(f"✅ Found {len(trends)} trending topics")
                    
                    # Same logic for JSON response
                    refund_topics = [t for t in trends if any(
                        keyword in t.get('title', '').lower() or 
                        keyword in ' '.join(t.get('keywords', [])).lower()
                        for keyword in ['refund', 'money', 'denied', 'processing', 'return', 'payment']
                    )]
                    
                    shoe_topics = [t for t in trends if any(
                        keyword in t.get('title', '').lower() or 
                        keyword in ' '.join(t.get('keywords', [])).lower()
                        for keyword in ['shoe', 'page', 'broken', 'images', 'size', 'footwear', 'product']
                    )]
                    
                    if refund_topics:
                        print(f"💰 Found refund issue trending topic!")
                        for topic in refund_topics:
                            print(f"   Title: {topic.get('title')}")
                            print(f"   Keywords: {topic.get('keywords')}")
                            print(f"   Count: {topic.get('count_in_window')}")
                            print(f"   Evidence: {topic.get('evidence_ids', {})}")
                    
                    if shoe_topics:
                        print(f"👟 Found shoe page trending topic!")
                        for topic in shoe_topics:
                            print(f"   Title: {topic.get('title')}")
                            print(f"   Keywords: {topic.get('keywords')}")
                            print(f"   Count: {topic.get('count_in_window')}")
                            print(f"   Evidence: {topic.get('evidence_ids', {})}")
                    
                    return trends
            else:
                print(f"❌ Trending topics detection failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Trending topics detection failed with exception: {e}")
            return False

async def main():
    """Create Zendesk tickets and test trend detection"""
    print("🎫 Zendesk Ticket Trend Detection Test - Refund & Shoe Page Issues")
    print("=" * 65)
    print(f"Creating tickets for refund issues and shoe page problems")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Create refund issue tickets (first trend)
    refund_success = await create_refund_issue_tickets()
    
    # Wait a bit between trends
    await asyncio.sleep(5)
    
    # Create shoe page issue tickets (second trend)
    shoe_success = await create_shoe_page_tickets()
    
    if refund_success > 0 or shoe_success > 0:
        print("\n⏳ Waiting for processing...")
        await asyncio.sleep(20)  # Wait longer for Zendesk processing
        
        # Test trending topics detection
        await test_trending_topics_detection()
    
    print("\n" + "=" * 65)
    print("✅ Test completed!")
    print("Check your dashboard to see if the refund and shoe page issues appear as trending topics")

if __name__ == "__main__":
    asyncio.run(main())