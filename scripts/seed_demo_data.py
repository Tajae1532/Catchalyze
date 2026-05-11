#!/usr/bin/env python3
"""
Seed script to populate CustomerWhisperer database with demo data.
Run this after setting up the database schema.
"""

import os
import sys
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") 

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    sys.exit(1)

# Initialize Supabase client
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✓ Connected to Supabase")
except Exception as e:
    print(f"✗ Failed to connect to Supabase: {e}")
    sys.exit(1)

def seed_customers():
    """Seed demo customers"""
    customers = [
        {
            "name": "Acme Corporation",
            "email": "contact@acme.com",
            "zendesk_id": "1001",
            "health_score": 85,
            "churn_risk": "low",
            "sentiment_score": 0.6,
            "last_interaction": datetime.now() - timedelta(hours=2)
        },
        {
            "name": "TechStart Inc",
            "email": "hello@techstart.com", 
            "zendesk_id": "1002",
            "health_score": 45,
            "churn_risk": "high",
            "sentiment_score": -0.3,
            "last_interaction": datetime.now() - timedelta(days=5)
        },
        {
            "name": "Global Industries",
            "email": "support@global.com",
            "zendesk_id": "1003", 
            "health_score": 72,
            "churn_risk": "medium",
            "sentiment_score": 0.2,
            "last_interaction": datetime.now() - timedelta(hours=8)
        }
    ]
    
    try:
        for customer in customers:
            customer['last_interaction'] = customer['last_interaction'].isoformat()
        
        result = supabase.table("customers").upsert(customers, on_conflict="zendesk_id").execute()
        print(f"✓ Seeded {len(result.data)} customers")
        return result.data
    except Exception as e:
        print(f"✗ Failed to seed customers: {e}")
        return []

def seed_tickets(customers):
    """Seed demo tickets"""
    if not customers:
        print("✗ No customers available for seeding tickets")
        return []
        
    tickets = [
        {
            "customer_id": customers[0]["id"],
            "zendesk_ticket_id": "10001",
            "subject": "Login issues with new update",
            "description": "Users are experiencing difficulties logging in after the latest update. This is affecting our daily operations.",
            "status": "open",
            "priority": "high",
            "sentiment_score": -0.4,
            "ai_summary": "Customer reporting login issues affecting operations",
            "tags": ["login", "bug", "urgent"],
            "created_at": datetime.now() - timedelta(hours=6)
        },
        {
            "customer_id": customers[1]["id"], 
            "zendesk_ticket_id": "10002",
            "subject": "Feature request: Advanced reporting",
            "description": "We would love to see more advanced reporting features in the dashboard. This would help us make better business decisions.",
            "status": "pending",
            "priority": "normal", 
            "sentiment_score": 0.3,
            "ai_summary": "Feature request for enhanced reporting capabilities",
            "tags": ["feature-request", "reporting"],
            "created_at": datetime.now() - timedelta(days=2)
        },
        {
            "customer_id": customers[2]["id"],
            "zendesk_ticket_id": "10003", 
            "subject": "Billing question",
            "description": "I have a question about my recent invoice. The charges seem higher than expected.",
            "status": "resolved",
            "priority": "low",
            "sentiment_score": -0.1,
            "ai_summary": "Customer inquiry about billing charges",
            "tags": ["billing", "invoice"],
            "created_at": datetime.now() - timedelta(days=1)
        }
    ]
    
    try:
        for ticket in tickets:
            ticket['created_at'] = ticket['created_at'].isoformat()
            
        result = supabase.table("tickets").upsert(tickets, on_conflict="zendesk_ticket_id").execute()
        print(f"✓ Seeded {len(result.data)} tickets")
        return result.data
    except Exception as e:
        print(f"✗ Failed to seed tickets: {e}")
        return []

def seed_slack_messages(customers):
    """Seed demo Slack messages"""
    if not customers:
        print("✗ No customers available for seeding Slack messages")
        return []
        
    messages = [
        {
            "customer_id": customers[0]["id"],
            "slack_channel_id": "C1234567890",
            "slack_message_id": "1234567890.123456",
            "user_id": "U1234567890",
            "text": "Hey team, Acme Corporation just upgraded to our premium plan! 🎉",
            "sentiment_score": 0.8,
            "mentions": ["@channel"],
            "created_at": datetime.now() - timedelta(hours=3)
        },
        {
            "customer_id": customers[1]["id"],
            "slack_channel_id": "C1234567890", 
            "slack_message_id": "1234567890.123457",
            "user_id": "U0987654321",
            "text": "TechStart Inc seems frustrated with the recent issues. We should reach out proactively.",
            "sentiment_score": -0.5,
            "mentions": [],
            "created_at": datetime.now() - timedelta(hours=1)
        },
        {
            "customer_id": customers[2]["id"],
            "slack_channel_id": "C0987654321",
            "slack_message_id": "1234567890.123458", 
            "user_id": "U1111111111",
            "text": "Global Industries wants to schedule a demo of our new features. Great opportunity!",
            "sentiment_score": 0.6,
            "mentions": ["@sales"],
            "created_at": datetime.now() - timedelta(minutes=30)
        }
    ]
    
    try:
        for message in messages:
            message['created_at'] = message['created_at'].isoformat()
            
        result = supabase.table("slack_messages").upsert(
            messages, 
            on_conflict="slack_channel_id,slack_message_id"
        ).execute()
        print(f"✓ Seeded {len(result.data)} Slack messages")
        return result.data
    except Exception as e:
        print(f"✗ Failed to seed Slack messages: {e}")
        return []

def seed_insights():
    """Seed demo insights"""
    insights = [
        {
            "type": "trending_issue",
            "title": "Login Issues Affecting Multiple Customers",
            "description": "AI Analysis detected a pattern of login-related issues affecting 15% of active customers. Recommend immediate investigation of authentication service.",
            "severity": "high",
            "affected_customers": 12,
            "data": {
                "pattern": "login_failures",
                "time_range": "last_24h", 
                "confidence": 0.85,
                "keywords": ["login", "authentication", "timeout"]
            },
            "is_active": True
        },
        {
            "type": "sentiment_spike",
            "title": "Declining Customer Satisfaction Trend",
            "description": "Customer sentiment scores have decreased by 15% over the past week. Primary drivers include technical issues and response time concerns.",
            "severity": "medium",
            "affected_customers": 28,
            "data": {
                "average_sentiment": -0.12,
                "trend": "declining",
                "primary_factors": ["technical_issues", "response_time"],
                "time_period": "7_days"
            },
            "is_active": True
        },
        {
            "type": "churn_risk", 
            "title": "High-Risk Customers Identified",
            "description": "5 customers showing strong churn signals based on reduced activity and negative sentiment. Recommend immediate outreach.",
            "severity": "critical",
            "affected_customers": 5,
            "data": {
                "risk_factors": ["low_activity", "negative_sentiment", "support_tickets"],
                "prediction_confidence": 0.78,
                "recommended_actions": ["personal_outreach", "product_demo", "discount_offer"]
            },
            "is_active": True
        }
    ]
    
    try:
        result = supabase.table("insights").insert(insights).execute()
        print(f"✓ Seeded {len(result.data)} insights")
        return result.data
    except Exception as e:
        print(f"✗ Failed to seed insights: {e}")
        return []

def main():
    """Main seeding function"""
    print("🌱 Starting CustomerWhisperer database seeding...")
    
    # Seed in order due to foreign key dependencies
    customers = seed_customers()
    tickets = seed_tickets(customers)
    messages = seed_slack_messages(customers)
    insights = seed_insights()
    
    print("\n📊 Seeding Summary:")
    print(f"   • Customers: {len(customers)}")
    print(f"   • Tickets: {len(tickets)}")
    print(f"   • Slack Messages: {len(messages)}")
    print(f"   • Insights: {len(insights)}")
    print("\n✅ Database seeding completed!")

if __name__ == "__main__":
    main()