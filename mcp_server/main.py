from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse, StreamingResponse, HTMLResponse, JSONResponse
from typing import Dict, Any, List, Optional
import queue
import os
import json
import hmac
import hashlib
import time
import secrets
import socket
import random
from datetime import datetime, timedelta
from supabase import create_client, Client
import openai
import httpx
from fastmcp import FastMCP
from mcp.types import JSONRPCError
import asyncio 
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from urllib.parse import quote, quote_plus
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
import numpy as np
from collections import OrderedDict
import re
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer
import statistics
from dataclasses import dataclass
from typing import Optional
from contextvars import ContextVar
import asyncio
from contextlib import asynccontextmanager
from collections import defaultdict
import html
import logging
import jwt
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv() 

OPENAI_MODEL_DEFAULT = os.environ.get("OPENAI_MODEL_DEFAULT", "gpt-4o-mini")
OPENAI_MODEL_INSIGHTS = os.environ.get("OPENAI_MODEL_INSIGHTS", "gpt-4o-mini")

# Default account ID for development/fallback
DEFAULT_ACCOUNT_ID = os.environ.get("DEFAULT_ACCOUNT_ID", "00000000-0000-0000-0000-000000000000")

# Global context variable for MCP tools  
current_account_id: ContextVar[str] = ContextVar('current_account_id', default=DEFAULT_ACCOUNT_ID)

mcp_server = FastMCP(name="Catchalyze", stateless_http=True)
# Define lifespan context manager
mcp_app = mcp_server.http_app()  

# Scheduler setup
OWNER_ID = f"{socket.gethostname()}:{os.getpid()}:{secrets.token_hex(8)}"

# SSE clients management
sse_clients: List[asyncio.Queue] = []

# === ACCOUNT CONTEXT MANAGEMENT ===

def get_current_account_id() -> str:
    """Get current account ID from context or raise authentication error."""
    try:
        return current_account_id.get()
    except LookupError:
        raise HTTPException(status_code=401, detail="No account context available")

async def set_account_context(request: Request):
    """Set account context for MCP operations."""
    account_id = get_account_id_from_request(request)
    current_account_id.set(account_id)
    return account_id

def get_account_lock_key(base_key: str, account_id: str = None) -> str:
    """Generate account-scoped lock key."""
    if not account_id:
        account_id = get_current_account_id()
    return f"{base_key}:{account_id}"

async def acquire_lock(lock_key: str, ttl_sec: int) -> bool:
    if not supabase: return False
    now = datetime.now()
    expires = now + timedelta(seconds=ttl_sec)
    try:
        # Try insert
        await asyncio.to_thread(
            supabase.table("app_locks").insert({
                "lock_key": lock_key,
                "owner": OWNER_ID,
                "expires_at": expires.isoformat()
            }).execute
        )
        return True
    except Exception:
        try:
            resp = await asyncio.to_thread(
                supabase.table("app_locks")
                .update({"owner": OWNER_ID, "expires_at": expires.isoformat()})
                .eq("lock_key", lock_key)
                .lt("expires_at", now.isoformat())
                .execute
            )
            return bool(resp.data)  # acquired if 1 row updated
        except Exception:
            return False

async def release_lock(lock_key: str):
    if not supabase: return
    try:
        await asyncio.to_thread(
            supabase.table("app_locks")
            .delete()
            .eq("lock_key", lock_key)
            .eq("owner", OWNER_ID)
            .execute
        )
    except Exception:
        pass

async def insights_scheduler():
    """Generate customer insights for all active accounts."""
    await asyncio.sleep(10)
    while True:
        try:
            # Get all active accounts
            accounts_resp = await asyncio.to_thread(
                supabase.table("accounts")
                .select("id, name")
                .execute
            )
            
            if not accounts_resp.data:
                print("[scheduler] No accounts found")
            else:
                for account in accounts_resp.data:
                    account_id = account["id"]
                    account_name = account["name"]
                    
                    # Account-scoped lock key
                    lock_key = get_account_lock_key("insights_scheduler", account_id)
                    
                    got = await acquire_lock(lock_key, ttl_sec=600)
                    if not got:
                        print(f"[scheduler] Skipping account {account_name} ({account_id[:8]}) - locked")
                        continue
                    
                    print(f"[scheduler] Processing insights for account {account_name} ({account_id[:8]})")
                    
                    try:
                        # Set account context for processing
                        current_account_id.set(account_id)
                        
                        # Process insights for this account
                        tools = await mcp_server.get_tools()
                        gen_tool = tools["generate_customer_insights"]
                        result = await gen_tool.run({"time_range": "7d"})
                        
                        print(f"[scheduler] Account {account_id[:8]} insights → {result.structured_content.get('no_insight', 'processed')}")
                        
                    except Exception as e:
                        print(f"[scheduler] Failed to process account {account_id[:8]}: {e}")
                    finally:
                        # Reset context and release lock
                        current_account_id.set(DEFAULT_ACCOUNT_ID)
                        await release_lock(lock_key)
                        print(f"[scheduler] Released lock for account {account_id[:8]}")
                        
        except Exception as e:
            print(f"[scheduler] Multi-account insights failed: {e}")

        jitter = random.randint(-300, 300)
        await asyncio.sleep(2700 + jitter)

async def topic_clustering_scheduler():
    """Run topic clustering for all active accounts."""
    await asyncio.sleep(30)  # Start after insights scheduler
    while True:
        try:
            # Get accounts with recent activity
            cutoff_time = (datetime.now() - timedelta(hours=6)).isoformat()
            active_accounts = await get_accounts_with_recent_activity(cutoff_time)
            
            if not active_accounts:
                print("[topic scheduler] No accounts with recent activity for clustering")
            else:
                for account_id in active_accounts:
                    lock_key = get_account_lock_key("topic_clustering", account_id)
                    
                    got = await acquire_lock(lock_key, ttl_sec=RECLUSTER_INTERVAL_SEC)
                    if not got:
                        print(f"[topic scheduler] Skipping account {account_id[:8]} - locked")
                        continue
                    
                    print(f"[topic scheduler] Processing account {account_id[:8]}")
                    
                    try:
                        # Set account context
                        current_account_id.set(account_id)
                        
                        await run_topic_reclustering()
                        await detect_and_emit_trends()
                        
                        print(f"[topic scheduler] Completed clustering for account {account_id[:8]}")
                        
                    except Exception as e:
                        print(f"[topic scheduler] Failed for account {account_id[:8]}: {e}")
                    finally:
                        current_account_id.set(DEFAULT_ACCOUNT_ID)
                        await release_lock(lock_key)
                        
        except Exception as e:
            print(f"[topic scheduler] loop error: {e}")

        jitter = random.randint(-60, 60)
        await asyncio.sleep(RECLUSTER_INTERVAL_SEC + jitter)

async def micro_batch_processor():
    """Optimized micro-batch processor with account-aware processing"""
    await asyncio.sleep(15)  # Initial delay
    
    while True:
        try:
            # Get all active accounts
            accounts_resp = await asyncio.to_thread(
                supabase.table("accounts")
                .select("id, name")
                .execute
            )
            
            if not accounts_resp.data:
                print("[micro-batch] No accounts found")
            else:
                for account in accounts_resp.data:
                    account_id = account["id"]
                    
                    try:
                        # Clean up stale trends for this account
                        await cleanup_stale_trends(account_id)
                        
                        # Define the time window (last 60 seconds)
                        end_time = datetime.now()
                        start_time = end_time - timedelta(seconds=60)
                        
                        # Check for recent activity in this account
                        recent_activity = await asyncio.to_thread(
                            supabase.table("embeddings_store")
                            .select("id")
                            .eq("account_id", account_id)
                            .gte("ts", start_time.isoformat())
                            .lt("ts", end_time.isoformat())
                            .execute
                        )
                        
                        if recent_activity.data:
                            print(f"[micro-batch] Account {account_id[:8]} - Found {len(recent_activity.data)} recent items")
                            
                            # Set account context
                            current_account_id.set(account_id)
                            
                            # Pass the exact same time window to trend detection
                            trending = await detect_trending_topics(
                                account_id=account_id,
                                start_time=start_time,
                                end_time=end_time
                            )
                            
                            if trending:
                                print(f"[micro-batch] Account {account_id[:8]} - Detected {len(trending)} trends")
                                
                                # Check if trends are already active and need insights
                                new_trends = []
                                missing_insights_trends = []
                                
                                for topic in trending:
                                    trend_type = "volume_spike" if topic.get("volume_spike") else "general"
                                    
                                    # Check if already active
                                    is_active = await check_active_trend(
                                        topic["topic_id"], 
                                        trend_type,
                                        account_id
                                    )
                                    
                                    if not is_active:
                                        new_trends.append(topic)
                                        
                                        # Mark as active to prevent future duplicates
                                        await mark_trend_active(
                                            topic["topic_id"],
                                            trend_type, 
                                            topic,
                                            account_id
                                        )
                                        print(f"[micro-batch] Account {account_id[:8]} - Marked trend {topic['topic_id']} as active")
                                    else:
                                        # Check if this active trend has AI insights
                                        existing_insights_resp = await asyncio.to_thread(
                                            supabase.table("insights")
                                            .select("id")
                                            .eq("type", "trend")
                                            .eq("data->>topic_id", str(topic["topic_id"]))
                                            .execute
                                        )
                                        
                                        if not existing_insights_resp.data:
                                            missing_insights_trends.append(topic)
                                            print(f"[micro-batch] Account {account_id[:8]} - Active trend {topic['topic_id']} missing AI insights")
                                        else:
                                            print(f"[micro-batch] Account {account_id[:8]} - Skipping already active trend {topic['topic_id']} with insights")
                                
                                # Process both new trends and missing insights
                                all_trends_to_process = new_trends + missing_insights_trends
                                
                                if all_trends_to_process:
                                    print(f"[micro-batch] Account {account_id[:8]} - Processing {len(new_trends)} new trends and {len(missing_insights_trends)} trends missing insights")
                                    await generate_trend_insights(all_trends_to_process)
                                else:
                                    print(f"[micro-batch] Account {account_id[:8]} - All detected trends already active with insights")
                            else:
                                print(f"[micro-batch] Account {account_id[:8]} - No trends detected")
                        else:
                            print(f"[micro-batch] Account {account_id[:8]} - No recent activity")
                            
                    except Exception as e:
                        print(f"[micro-batch] Account {account_id[:8]} error: {e}")
                    finally:
                        current_account_id.set(DEFAULT_ACCOUNT_ID)
                
        except Exception as e:
            print(f"[micro-batch] Error: {e}")
        
        await asyncio.sleep(10)  # 10-second intervals

old_lifespan = mcp_app.lifespan

@asynccontextmanager
async def combined_lifespan(app_obj):
    async with old_lifespan(app_obj):
        tasks = [
            asyncio.create_task(insights_scheduler()),
            asyncio.create_task(topic_clustering_scheduler()),
            asyncio.create_task(micro_batch_processor()),
            asyncio.create_task(periodic_cleanup())
        ]
        
        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            await cleanup_rate_limits()

async def get_accounts_with_recent_activity(cutoff_time: str) -> list[str]:
    """Get account IDs that have recent message or ticket activity."""
    try:
        # Get accounts with recent tickets
        recent_tickets = await asyncio.to_thread(
            supabase.table("tickets")
            .select("account_id")
            .gte("created_at", cutoff_time)
            .execute
        )
        
        # Get accounts with recent messages
        recent_messages = await asyncio.to_thread(
            supabase.table("slack_messages")
            .select("account_id")
            .gte("created_at", cutoff_time)
            .execute
        )
        
        # Combine and deduplicate account IDs
        active_accounts = set()
        
        for ticket in recent_tickets.data:
            if ticket.get("account_id"):
                active_accounts.add(ticket["account_id"])
        
        for message in recent_messages.data:
            if message.get("account_id"):
                active_accounts.add(message["account_id"])
        
        return list(active_accounts)
        
    except Exception as e:
        print(f"Error getting accounts with recent activity: {e}")
        return []

# Set lifespan callable for FastAPI
app = FastAPI(
    title="Catchalyze MCP Server",
    description="MCP Server for customer intelligence platforms",
    version="1.0.0",
    lifespan=combined_lifespan,
)

@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    content_length = request.headers.get('content-length')
    if content_length:
        content_length = int(content_length)
        if content_length > 10 * 1024 * 1024:  # 10MB limit
            return JSONResponse(
                status_code=413,
                content={"error": "Request too large"}
            )
    response = await call_next(request)
    return response

if os.environ.get("ENVIRONMENT") == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

# Configure logging
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add these constants and variables after your existing constants
JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable required")

mcp_rate_limits = defaultdict(lambda: {"count": 0, "reset_time": time.time()})
expensive_tool_limits = defaultdict(lambda: {"count": 0, "reset_time": time.time()})

# Add these helper functions
def get_client_ip(request: Request) -> str:
    """Extract client IP address with proper X-Forwarded-For handling"""
    # Handle X-Forwarded-For which can contain multiple IPs (first is original client)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    # Fallback to X-Real-IP
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    
    # Last resort - use request client (may be proxy)
    return getattr(request.client, 'host', 'unknown')

async def check_mcp_rate_limit(client_ip: str, max_requests: int = 30, window_seconds: int = 60) -> bool:
    """Check if client has exceeded MCP rate limit - 30 requests per minute"""
    current_time = time.time()
    client_data = mcp_rate_limits[client_ip]
    
    # Reset counter if window has passed
    if current_time > client_data["reset_time"] + window_seconds:
        client_data["count"] = 0
        client_data["reset_time"] = current_time
    
    # Check limit
    if client_data["count"] >= max_requests:
        return True  # Rate limited
    
    client_data["count"] += 1
    return False  # OK

async def check_tool_rate_limit(account_id: str, tool_name: str, max_requests: int = 5, window_seconds: int = 60) -> bool:
    """Check rate limit for specific expensive tools - 5 requests per minute per account"""
    current_time = time.time()
    key = f"{account_id}:{tool_name}"
    tool_data = expensive_tool_limits[key]
    
    # Reset counter if window has passed
    if current_time > tool_data["reset_time"] + window_seconds:
        tool_data["count"] = 0
        tool_data["reset_time"] = current_time
    
    # Check limit
    if tool_data["count"] >= max_requests:
        return True  # Rate limited
    
    tool_data["count"] += 1
    return False  # OK

expensive_tool_limits = defaultdict(lambda: {"count": 0, "reset_time": time.time()})
trending_cache = {}  # Cache: key -> {data, timestamp, hash}

async def check_tool_rate_limit_with_cache(
    account_id: str, 
    tool_name: str, 
    cache_key: str = None,
    max_requests: int = 15, 
    window_seconds: int = 60
) -> tuple[bool, Optional[Dict]]:
    """
    Returns (is_rate_limited, cached_data_if_limited)
    """
    current_time = time.time()
    key = f"{account_id}:{tool_name}"
    tool_data = expensive_tool_limits[key]
    
    # Reset counter if window has passed
    if current_time >= tool_data["reset_time"] + window_seconds:
        tool_data["count"] = 0
        tool_data["reset_time"] = current_time
    
    # Check limit
    if tool_data["count"] >= max_requests:
        # Return cached data if available
        cached = trending_cache.get(cache_key) if cache_key else None
        if cached and current_time - cached["timestamp"] < 300:  # 5min TTL
            return True, cached["data"]
        return True, None
    
    tool_data["count"] += 1
    return False, None

def cache_trending_result(cache_key: str, data: Dict[str, Any]):
    """Cache trending results with timestamp and content hash"""
    data_hash = hash(json.dumps(data.get("trending_topics", []), sort_keys=True))
    trending_cache[cache_key] = {
        "data": data,
        "timestamp": time.time(),
        "hash": data_hash
    }

async def cleanup_rate_limits():
    """Clean up old rate limit entries to prevent memory leaks"""
    current_time = time.time()
    for ip in list(mcp_rate_limits.keys()):
        if current_time > mcp_rate_limits[ip]["reset_time"] + 3600:  # 1 hour old
            del mcp_rate_limits[ip]
    
    for key in list(expensive_tool_limits.keys()):
        if current_time > expensive_tool_limits[key]["reset_time"] + 3600:  # 1 hour old
            del expensive_tool_limits[key]

async def periodic_cleanup():
    """Run rate limit cleanup every hour"""
    while True:
        await asyncio.sleep(3600)  # 1 hour
        await cleanup_rate_limits()

async def account_exists(account_id: str) -> bool:
    """Validate that account exists in database"""
    if not supabase:
        return False
    
    try:
        response = await asyncio.to_thread(
            supabase.table("accounts")
            .select("id")
            .eq("id", account_id)
            .execute
        )
        return len(response.data) > 0
    except Exception:
        return False

class SecureMCPAuthMiddleware:
    """Production-ready MCP authentication and security middleware"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith("/mcp"):
            request = Request(scope, receive)
            client_ip = get_client_ip(request)
            
            # Basic rate limiting (30 requests/minute)
            if await check_mcp_rate_limit(client_ip):
                logger.warning(f"MCP rate limit exceeded from {client_ip}")
                response = JSONResponse(
                    {"error": {"message": "Rate limit exceeded. Try again later."}}, 
                    status_code=429
                )
                await response(scope, receive, send)
                return
            
            # Authentication required
            auth_cookie = request.cookies.get("auth_token")
            if not auth_cookie:
                logger.warning(f"MCP authentication failed from {client_ip}: no auth cookie")
                response = JSONResponse(
                    {"error": {"message": "Authentication required"}}, 
                    status_code=401
                )
                await response(scope, receive, send)
                return
            
            try:
                import jwt
                payload = jwt.decode(
                    auth_cookie, 
                    JWT_SECRET,
                    algorithms=["HS256"]
                )
                
                # Check expiration
                if payload.get("exp", 0) < time.time():
                    logger.warning(f"MCP authentication failed from {client_ip}: token expired")
                    response = JSONResponse(
                        {"error": {"message": "Token expired"}}, 
                        status_code=401
                    )
                    await response(scope, receive, send)
                    return
                
                # Validate account exists
                account_id = payload["account_id"]
                if not await account_exists(account_id):
                    logger.warning(f"MCP authentication failed from {client_ip}: invalid account {account_id}")
                    response = JSONResponse(
                        {"error": {"message": "Invalid account"}}, 
                        status_code=401
                    )
                    await response(scope, receive, send)
                    return
                
                # Set account context
                current_account_id.set(account_id)
                
            except jwt.InvalidTokenError as e:
                logger.warning(f"MCP authentication failed from {client_ip}: invalid token - {str(e)}")
                response = JSONResponse(
                    {"error": {"message": "Invalid token"}}, 
                    status_code=401
                )
                await response(scope, receive, send)
                return
            
            # Execute with security headers
            async def send_with_security_headers(message):
                if message['type'] == 'http.response.start':
                    headers = list(message.get('headers', []))
                    headers.extend([
                        (b'x-content-type-options', b'nosniff'),
                        (b'x-frame-options', b'DENY'),
                        (b'x-xss-protection', b'1; mode=block'),
                    ])
                    message['headers'] = headers
                await send(message)
            
            try:
                await self.app(scope, receive, send_with_security_headers)
            finally:
                current_account_id.set(DEFAULT_ACCOUNT_ID)
        else:
            await self.app(scope, receive, send)

# Apply middleware to MCP app
mcp_app.add_middleware(SecureMCPAuthMiddleware)

@dataclass
class RateLimiter:
    """Simple adaptive rate limiter for OpenAI API"""
    requests_per_minute: int = 10  # Start conservative
    last_rate_limit: Optional[datetime] = None
    consecutive_successes: int = 0
    consecutive_failures: int = 0
    
    def should_proceed(self) -> bool:
        """Check if we should make a request"""
        if self.last_rate_limit:
            time_since = (datetime.now() - self.last_rate_limit).total_seconds()
            if time_since < 60:  # Wait at least 1 minute after rate limit
                return False
        return True
    
    def record_success(self):
        """Record successful request"""
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        
        # Gradually increase rate if doing well
        if self.consecutive_successes >= 10:
            self.requests_per_minute = min(60, self.requests_per_minute + 5)
            self.consecutive_successes = 0
    
    def record_rate_limit(self):
        """Record rate limit hit"""
        self.last_rate_limit = datetime.now()
        self.consecutive_successes = 0
        self.consecutive_failures += 1
        
        # Reduce rate on failure
        self.requests_per_minute = max(5, self.requests_per_minute // 2)
    
    def get_delay(self) -> float:
        """Get delay between requests based on current rate"""
        return 60.0 / self.requests_per_minute

# Global rate limiter instance
rate_limiter = RateLimiter()

# Keep the existing rate_limit_stats for monitoring
rate_limit_stats = {
    "total_requests": 0,
    "rate_limit_hits": 0,
    "successful_retries": 0,
    "failed_after_retries": 0,
    "last_rate_limit_time": None
}

def validate_account_context():
    account_id = get_current_account_id()
    if account_id == DEFAULT_ACCOUNT_ID:
        raise RuntimeError("Account context not properly set")
    return account_id

# --- Configuration ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") 
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:8080").rstrip("/")

# Email configuration
EMAIL_USERNAME = os.environ.get("EMAIL_USERNAME")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD") 
GMAIL_SMTP_ENABLED = os.environ.get("GMAIL_SMTP_ENABLED", "false").lower() == "true"

ALLOWED_ORIGINS = [
    FRONTEND_URL,               
    "http://localhost:8080",   
    "http://localhost:5173",
    "https://4478704c87d5.ngrok-free.app",
]

if "ngrok" in FRONTEND_URL:
    ALLOWED_ORIGINS.append(FRONTEND_URL)

# CORS for the MCP sub-app (handles /rpc)
mcp_app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CORS for your main app (handles /slack/*, /zendesk/*, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Slack Configuration
SLACK_CLIENT_ID = os.environ.get("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.environ.get("SLACK_CLIENT_SECRET")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
SLACK_SCOPES = os.environ.get("SLACK_SCOPES", "channels:history,channels:read,chat:write,team:read,users:read")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000")

# Zendesk Configuration
ZENDESK_SUBDOMAIN = os.environ.get("ZENDESK_SUBDOMAIN")
ZENDESK_EMAIL = os.environ.get("ZENDESK_EMAIL")
ZENDESK_API_TOKEN = os.environ.get("ZENDESK_API_TOKEN")
ZENDESK_CLIENT_ID = os.environ.get("ZENDESK_CLIENT_ID")
ZENDESK_CLIENT_SECRET = os.environ.get("ZENDESK_CLIENT_SECRET")
ZENDESK_SCOPES = os.environ.get("ZENDESK_SCOPES", "read write")
ZENDESK_ENCRYPTION_KEY = os.environ.get("ZENDESK_ENCRYPTION_KEY")

# === SECURITY EXCEPTIONS ===

class SecurityUpgradeRequired(Exception):
    """Exception raised when encrypted credential format needs upgrade."""
    pass

# === ENCRYPTION FUNCTIONS ===

def normalize_subdomain_for_decrypt(subdomain: str) -> str:
    """Apply same normalization used during encryption."""
    subdomain = subdomain.strip().lower()
    if '.zendesk.com' in subdomain:
        subdomain = subdomain.split('.zendesk.com')[0]
    if '://' in subdomain:
        url_parts = subdomain.split('://')[1]
        if url_parts:
            subdomain = url_parts.split('.zendesk.com')[0]
    return subdomain

def detect_encryption_format(stored_value: str) -> tuple[str, str]:
    """Check for AES-GCM-256: prefix, return format and version."""
    if stored_value.startswith('AES-GCM-256:'):
        version = stored_value.split(':')[1]
        return 'aes-gcm', version
    
    # Format detection unclear - require re-save
    return 'unknown', 'unknown'

def encrypt_aes_gcm_credential(client_secret: str, subdomain: str) -> str:
    """Encrypt using AES-GCM with AAD binding"""
    if not ZENDESK_ENCRYPTION_KEY:
        raise HTTPException(status_code=500, detail="Encryption key not configured")
    
    # Use existing normalization
    aad = normalize_subdomain_for_decrypt(subdomain).encode('utf-8')
    
    # Prepare key material (same as edge function)
    key_material = ZENDESK_ENCRYPTION_KEY.encode('utf-8').ljust(32, b'0')[:32]
    
    # Generate random IV
    iv = secrets.token_bytes(12)
    
    # Encrypt using AES-GCM
    aesgcm = AESGCM(key_material)
    ciphertext = aesgcm.encrypt(iv, client_secret.encode('utf-8'), aad)
    
    # Combine IV + ciphertext and encode
    combined = iv + ciphertext
    encoded = base64.b64encode(combined).decode('ascii')
    
    return f"AES-GCM-256:v1:{encoded}"

def decrypt_aes_gcm_credential(encrypted_data: str, subdomain: str) -> str:
    """Decrypt using AAD binding with normalized subdomain."""
    if not ZENDESK_ENCRYPTION_KEY:
        raise HTTPException(status_code=500, detail="Encryption key not configured")
    
    try:
        # Parse format: "AES-GCM-256:v1:base64(iv+ciphertext)"
        parts = encrypted_data.split(':')
        if len(parts) != 3 or parts[0] != 'AES-GCM-256':
            raise ValueError("Invalid encrypted data format")
        
        version = parts[1]
        if version != 'v1':
            raise ValueError(f"Unsupported encryption version: {version}")
        
        # Decode the combined IV + ciphertext
        combined_data = base64.b64decode(parts[2])
        
        # Extract IV (first 12 bytes) and ciphertext (rest)
        iv = combined_data[:12]
        ciphertext = combined_data[12:]
        
        # Use normalized subdomain as AAD
        aad = normalize_subdomain_for_decrypt(subdomain).encode('utf-8')
        
        # Prepare key material (same as encryption)
        key_material = ZENDESK_ENCRYPTION_KEY.encode('utf-8').ljust(32, b'0')[:32]
        
        # Decrypt using AES-GCM
        aesgcm = AESGCM(key_material)
        plaintext = aesgcm.decrypt(iv, ciphertext, aad)
        
        return plaintext.decode('utf-8')
        
    except Exception as e:
        logger.error(f"AES-GCM decryption failed for subdomain {subdomain}: {e}")
        raise HTTPException(status_code=500, detail="Failed to decrypt credentials")

# Initialize Supabase client
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Supabase client initialized.")
    except Exception as e:
        print(f"Failed to initialize Supabase client: {e}")
        supabase = None
else:
    print("Supabase URL or Key not found in environment variables.")

# Initialize OpenAI client
openai_client: AsyncOpenAI | None = None
if OPENAI_API_KEY:
    try:
        # Async client works cleanly inside FastAPI async endpoints
        openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        print("OpenAI client initialized.")
    except Exception as e:
        print(f"Failed to initialize OpenAI client: {e}")
        openai_client = None
else:
    print("OpenAI API Key not found in environment variables.")

# --- Helper Functions (used by tools) ---

def _completion_limit_kw(model_name: str, n: int) -> dict:
    # GPT-5 uses max_completion_tokens; others use max_tokens
    if (model_name or "").lower().startswith("gpt-5"):
        return {"max_completion_tokens": n}
    return {"max_tokens": n}

def _model_specific_args(model_name: str, max_out_tokens: int, *, temperature: float | None) -> dict:
    """
    Build kwargs for chat.completions.create that are compatible with each model.
    - GPT-5: omit temperature/top_p/etc, use max_completion_tokens
    - Others: allow temperature, use max_tokens
    """
    args = {}
    args.update(_completion_limit_kw(model_name, max_out_tokens))

    is_gpt5 = (model_name or "").lower().startswith("gpt-5")
    if not is_gpt5 and temperature is not None:
        args["temperature"] = temperature

    return args

async def call_openai_api(
    prompt: str,
    system_message: str | None = None,
) -> Dict[str, Any]:
    """Call OpenAI chat.completions with the async SDK."""
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI client not configured")

    messages: list[dict[str, str]] = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})
    model_name = OPENAI_MODEL_DEFAULT
    try:
        resp = await openai_client.chat.completions.create(
            model=model_name,
            messages=messages,
            timeout=30.0,  # request-level timeout
            **_model_specific_args(model_name, 1000, temperature=0.7),
        )
        # Keep returning a dict so existing callers that read choices[0].message.content keep working
        return resp.model_dump()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {str(e)}")

def calculate_sentiment_score(text: str) -> float:
    """Simple sentiment calculation - would be enhanced with ML model"""
    positive_words = ['great', 'excellent', 'good', 'satisfied', 'happy', 'love', 'perfect']
    negative_words = ['bad', 'terrible', 'hate', 'awful', 'frustrated', 'angry', 'disappointed']
    
    words = text.lower().split()
    positive_count = sum(1 for word in words if word in positive_words)
    negative_count = sum(1 for word in words if word in negative_words)
    
    total_sentiment_words = positive_count + negative_count
    if total_sentiment_words == 0:
        return 0.0
    
    return (positive_count - negative_count) / total_sentiment_words

# --- Helper functions for grounded insights ---

def resolve_time_range(time_range: str) -> int:
    """Convert time range string to days"""
    tr = time_range.lower().strip()
    if tr == "24h" or tr == "1d":
        return 1
    elif tr == "7d":
        return 7
    elif tr == "30d":
        return 30
    elif tr == "90d":
        return 90
    else:
        return 7  # default

async def ensure_ticket_summaries(tickets: list[dict]) -> dict[str, str]:
    """Ensure all tickets have summaries, return mapping of ticket_id -> one_line"""
    if not supabase or not tickets:
        return {}
    
    ticket_ids = [t["id"] for t in tickets]
    
    # Get existing summaries
    existing_resp = await asyncio.to_thread(
        supabase.table("ticket_summaries")
        .select("ticket_id, one_line")
        .in_("ticket_id", ticket_ids)
        .execute
    )
    existing = {s["ticket_id"]: s["one_line"] for s in (existing_resp.data or [])}
    
    # Create missing summaries
    missing_tickets = [t for t in tickets if t["id"] not in existing]
    if missing_tickets:
        new_summaries = []
        for ticket in missing_tickets:
            subject = ticket.get("subject", "")
            description = ticket.get("description", "")
            combined = f"{subject} {description}".strip()
            one_line = combined[:200] if combined else "No description"
            token_estimate = max(1, int(len(one_line.split()) * 1.3))
            
            new_summaries.append({
                "ticket_id": ticket["id"],
                "one_line": one_line,
                "token_estimate": token_estimate
            })
        
        if new_summaries:
            await asyncio.to_thread(
                supabase.table("ticket_summaries").upsert(new_summaries).execute
            )
            for summary in new_summaries:
                existing[summary["ticket_id"]] = summary["one_line"]
    
    return existing

async def ensure_slack_summaries(messages: list[dict]) -> dict[str, str]:
    """Ensure all slack messages have summaries, return mapping of message_id -> one_line"""
    if not supabase or not messages:
        return {}
    
    message_ids = [m["id"] for m in messages]
    
    # Get existing summaries
    existing_resp = await asyncio.to_thread(
        supabase.table("slack_message_summaries")
        .select("slack_message_id, one_line")
        .in_("slack_message_id", message_ids)
        .execute
    )
    existing = {s["slack_message_id"]: s["one_line"] for s in (existing_resp.data or [])}
    
    # Create missing summaries
    missing_messages = [m for m in messages if m["id"] not in existing]
    if missing_messages:
        new_summaries = []
        for message in missing_messages:
            text = message.get("text", "")
            one_line = text[:200] if text else "Empty message"
            token_estimate = max(1, int(len(one_line.split()) * 1.3))
            
            new_summaries.append({
                "slack_message_id": message["id"],
                "one_line": one_line,
                "token_estimate": token_estimate
            })
        
        if new_summaries:
            await asyncio.to_thread(
                supabase.table("slack_message_summaries").upsert(new_summaries).execute
            )
            for summary in new_summaries:
                existing[summary["slack_message_id"]] = summary["one_line"]
    
    return existing

def normalize_title(title: str) -> str:
    """Normalize title for comparison"""
    import re
    # Convert to lowercase, remove punctuation, remove common stopwords
    stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
    words = re.sub(r'[^\w\s]', '', title.lower()).split()
    return " ".join(w for w in words if w not in stopwords)

def title_similarity(a: str, b: str) -> float:
    """Calculate title similarity using simple token overlap"""
    norm_a = set(normalize_title(a).split())
    norm_b = set(normalize_title(b).split())
    if not norm_a and not norm_b:
        return 0.0
    if not norm_a or not norm_b:
        return 0.0
    intersection = len(norm_a & norm_b)
    union = len(norm_a | norm_b)
    return intersection / union if union > 0 else 0.0

def jaccard_overlap(a_set: set[str], b_set: set[str]) -> float:
    """Calculate Jaccard similarity between two sets"""
    if not a_set and not b_set:
        return 0.0
    if not a_set or not b_set:
        return 0.0
    intersection = len(a_set & b_set)
    union = len(a_set | b_set)
    return intersection / union if union > 0 else 0.0

def priority_score(impact: float, confidence: float, novelty: float) -> float:
    """Calculate priority score for insight ranking"""
    return 0.5 * impact + 0.3 * (confidence * 100) + 0.2 * novelty

# --- Enum & numeric coercion ---

ALLOWED_TYPE = {"trend","churn_risk","bug","ux_friction","feature_request","process_gap"}
ALLOWED_SEVERITY = {"low","medium","high","critical"}
ALLOWED_OWNER_HINT = {"CS","Support","PM","Eng","Sales"}
ALLOWED_TIME_COST = {"S","M","L"}

def _clamp_float(v, lo, hi, default):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    if x != x:  # NaN
        return default
    return max(lo, min(hi, x))

def _clamp_int(v, lo, hi, default):
    try:
        x = int(round(float(v)))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, x))

def coerce_insight_fields(raw: dict) -> dict:
    """
    Normalize enums/case and clamp numeric/text fields so DB inserts/updates don't 400 on drift.
    Applies:
      - type, severity enums (lowercase)
      - owner_hint in {"CS","Support","PM","Eng","Sales"} or None
      - time_cost_hint in {"S","M","L"} or None
      - confidence -> [0,1], impact/novelty -> [0,100]
      - trims playbook_steps (≤3) and short text fields
    """
    out = dict(raw)

    desc = (
        (out.get("description") or "").strip()
        or (out.get("why_now") or "").strip()
        or (out.get("recommended_action") or "").strip()
        or (out.get("title") or "").strip()
    )
    # enums
    t = (out.get("type") or "trend").strip().lower()
    out["type"] = t if t in ALLOWED_TYPE else "trend"

    s = (out.get("severity") or "medium").strip().lower()
    out["severity"] = s if s in ALLOWED_SEVERITY else "medium"

    oh = out.get("owner_hint")
    if oh is None or str(oh).strip() == "":
        out["owner_hint"] = None
    else:
        oh_str = str(oh).strip()
        oh_norm = oh_str.upper() if oh_str.upper() in {"CS","PM","ENG"} else oh_str.capitalize()
        out["owner_hint"] = oh_norm if oh_norm in ALLOWED_OWNER_HINT else None

    tch = out.get("time_cost_hint")
    if tch is None or str(tch).strip() == "":
        out["time_cost_hint"] = None
    else:
        tch_norm = str(tch).strip().upper()
        out["time_cost_hint"] = tch_norm if tch_norm in ALLOWED_TIME_COST else None

    # numeric clamps
    out["confidence"] = _clamp_float(out.get("confidence", 0.7), 0.0, 1.0, 0.7)
    out["impact_score"] = _clamp_int(out.get("impact_score", 50), 0, 100, 50)
    out["novelty_score"] = _clamp_int(out.get("novelty_score", 50), 0, 100, 50)

    # small text hygiene
    steps = (out.get("playbook_steps") or [])[:3]
    out["playbook_steps"] = [str(s)[:140] for s in steps]
    out["title"] = (out.get("title") or "")[:180]
    out["recommended_action"] = (out.get("recommended_action") or "")[:200]
    out["why_now"] = (out.get("why_now") or "")[:300]
    out["description"] = (desc or "Auto-generated insight.").strip()[:600]

    return out

# --- Context sampling ---

MAX_CONTEXT_ITEMS = 400
SAMPLE_NEWEST_PER_SOURCE = 150   # newest by created_at
SAMPLE_EXTREMES_EACH = 50        # most negative and most positive by sentiment, per source (cap if not enough)

def _parse_dt(iso: str) -> float:
    try:
        return datetime.fromisoformat((iso or "").replace("Z","+00:00")).timestamp()
    except Exception:
        return 0.0

def _sent(v) -> float:
    try:
        return float(v if v is not None else 0.0)
    except Exception:
        return 0.0

def sample_by_recency_and_extremes(items: list[dict], per_newest: int, extremes_each: int) -> list[dict]:
    if not items:
        return []
    # newest
    newest = sorted(items, key=lambda x: _parse_dt(x.get("created_at","")), reverse=True)[:per_newest]
    # extremes by sentiment
    by_sent = sorted(items, key=lambda x: _sent(x.get("sentiment_score")))
    most_neg = by_sent[:extremes_each]
    most_pos = by_sent[-extremes_each:] if len(by_sent) > extremes_each else by_sent
    # merge & de-dupe by id
    seen = set()
    out = []
    for it in newest + most_neg + most_pos:
        _id = it.get("id") or it.get("zendesk_ticket_id") or it.get("slack_message_id")
        if _id and _id not in seen:
            seen.add(_id)
            out.append(it)
    return out

def interleave_cap(a: list[dict], b: list[dict], max_total: int) -> tuple[list[dict], list[dict]]:
    """Interleave to maintain mix; truncate to max_total, return possibly shortened (a,b)."""
    out = []
    i = j = 0
    while len(out) < max_total and (i < len(a) or j < len(b)):
        if i < len(a):
            out.append(("a", i)); i += 1
        if len(out) >= max_total: break
        if j < len(b):
            out.append(("b", j)); j += 1
    # rebuild lists from the chosen indices
    a_idx = [k for src,k in out if src=="a"]
    b_idx = [k for src,k in out if src=="b"]
    a_final = [a[k] for k in a_idx]
    b_final = [b[k] for k in b_idx]
    return a_final, b_final

# --- Utility Functions ---

def _iso(dt: datetime) -> str:
    """Convert datetime to ISO string (no microseconds)."""
    return dt.replace(microsecond=0).isoformat()

def _needs_refresh(expires_at: Optional[str], skew_seconds: int = 300) -> bool:
    """True if token is within the refresh window (or expired)."""
    if not expires_at:
        return False
    try:
        expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        return datetime.now() >= (expiry - timedelta(seconds=skew_seconds))
    except Exception:
        return False

def _cookie_secure() -> bool:
    """Use secure cookies when PUBLIC_BASE_URL is HTTPS."""
    return str(PUBLIC_BASE_URL).lower().startswith("https://")

def _cookie_samesite() -> str:
    """Return 'none' for HTTPS (cross-site) and 'lax' for localhost/dev."""
    return "none" if _cookie_secure() else "lax"


async def get_zendesk_creds_for(subdomain: str) -> tuple[str, str, str]:
    """
    Returns (client_id, client_secret, scopes).
    Use client_secret_enc column with format detection and AAD binding.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not available")

    # Normalize subdomain for consistency
    normalized_subdomain = normalize_subdomain_for_decrypt(subdomain)
    
    try:
        # Query for encrypted credentials with correct column name
        result = await asyncio.to_thread(
            lambda: supabase.table("zendesk_oauth_clients")
            .select("client_id, client_secret_enc, scopes, encryption_version")
            .eq("subdomain", normalized_subdomain)
            .single()
            .execute()
        )
        
        if result.data:
            row = result.data
            client_id = row["client_id"]
            encrypted_secret = row["client_secret_enc"]  # Use _enc column
            scopes = row.get("scopes", "read write")
            encryption_version = row.get("encryption_version", "legacy")
            
            # Handle different encryption formats
            format_type, version = detect_encryption_format(encrypted_secret)
            
            if format_type == 'aes-gcm':
                if version != 'v1':
                    logger.warning(f"Unsupported AES-GCM version '{version}' for {normalized_subdomain}")
                    raise SecurityUpgradeRequired("Please re-save your zendesk credentials to upgrade security")
                if encryption_version != 'v1':
                    logger.warning(f"Credential version mismatch for {normalized_subdomain}: prefix={version}, column={encryption_version} (proceeding)")
                # Decrypt using AES-GCM with AAD binding
                client_secret = decrypt_aes_gcm_credential(encrypted_secret, normalized_subdomain)
                logger.info(f"Successfully decrypted credentials for subdomain {normalized_subdomain} (version: {version})")
                return client_id, client_secret, scopes
                
            elif format_type == 'unknown':
                # Format detection failed - require re-save
                logger.warning(f"Unknown encryption format for subdomain {normalized_subdomain} - upgrade required")
                raise SecurityUpgradeRequired("Please re-save your Zendesk credentials to upgrade security")
            
    except SecurityUpgradeRequired:
        raise
    except Exception as e:
        logger.info(f"Database query failed for subdomain {normalized_subdomain}: {e}")
        # Fall through to environment fallback
        pass
    
    # If no DB row found, fall back to environment variables
    if ZENDESK_CLIENT_ID and ZENDESK_CLIENT_SECRET:
        logger.info(f"No custom credentials found for {normalized_subdomain}, using environment fallback")
        return (
            ZENDESK_CLIENT_ID,
            ZENDESK_CLIENT_SECRET, 
            ZENDESK_SCOPES or "read write"
        )
    
    raise HTTPException(
        status_code=400,
        detail=(
            f"No Zendesk OAuth client configured for subdomain '{normalized_subdomain}'. "
            "Please configure credentials via the onboarding wizard."
        )
    )

# --- Slack Helper Functions ---

def verify_slack_signature(request_body: bytes, timestamp: str, signature: str) -> bool:
    """Verify Slack request signature for webhook security"""
    if not SLACK_SIGNING_SECRET:
        return False
    
    # Check timestamp to prevent replay attacks (request should be within 5 minutes)
    if abs(time.time() - int(timestamp)) > 300:
        return False
    
    # Create signature
    sig_basestring = f"v0:{timestamp}:{request_body.decode('utf-8')}"
    expected_signature = 'v0=' + hmac.new(
        SLACK_SIGNING_SECRET.encode('utf-8'),
        sig_basestring.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)

async def exchange_oauth_code(code: str) -> Dict[str, Any]:
    """Exchange OAuth code for access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": SLACK_CLIENT_ID,
                "client_secret": SLACK_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"{PUBLIC_BASE_URL}/slack/oauth/callback"
            }
        )
        return response.json()

async def refresh_slack_token_if_needed(workspace_id: str) -> str:
    """
    Load token row. If no refresh_token or no expires_at, return access_token (assume non-expiring).
    If near expiry, refresh via Slack OAuth v2 and update DB. Return valid access_token.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        row = await asyncio.to_thread(
            supabase.table("slack_oauth_tokens")
            .select("access_token,refresh_token,expires_at")
            .eq("workspace_id", workspace_id).single().execute
        )
        if not row.data:
            raise HTTPException(status_code=401, detail=f"No Slack token found for workspace {workspace_id}")

        data = row.data
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_at = data.get("expires_at")

        if not refresh_token or not _needs_refresh(expires_at):
            return access_token

        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": SLACK_CLIENT_ID,
                    "client_secret": SLACK_CLIENT_SECRET,
                },
            )
        j = r.json()
        if not j.get("ok"):
            raise HTTPException(401, f"Slack refresh failed: {j.get('error','unknown')}")

        new_access = j["access_token"]
        new_refresh = j.get("refresh_token", refresh_token)
        new_expires = j.get("expires_in")
        new_expires_at = _iso(datetime.now() + timedelta(seconds=new_expires)) if new_expires else None

        await asyncio.to_thread(
            supabase.table("slack_oauth_tokens").upsert({
                "workspace_id": workspace_id,
                "access_token": new_access,
                "refresh_token": new_refresh,
                "expires_at": new_expires_at,
            }, on_conflict="workspace_id").execute
        )
        return new_access
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh Slack token: {str(e)}")


async def fetch_channel_list(access_token: str) -> List[Dict[str, Any]]:
    """Fetch list of public channels from Slack workspace"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://slack.com/api/conversations.list",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"types": "public_channel", "limit": 200}
        )
        data = response.json()
        return data.get("channels", []) if data.get("ok") else []

async def fetch_channel_history(access_token: str, channel_id: str, oldest: str = None) -> List[Dict[str, Any]]:
    """Fetch message history for a specific channel"""
    async with httpx.AsyncClient() as client:
        params = {"channel": channel_id, "limit": 200}
        if oldest:
            params["oldest"] = oldest
            
        response = await client.get(
            "https://slack.com/api/conversations.history",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params
        )
        data = response.json()
        return data.get("messages", []) if data.get("ok") else []

async def sync_workspace_history(workspace_id: str) -> Dict[str, Any]:
    """Background job to sync 90 days of message history for a workspace"""
    try:
        print(f"Starting history sync for workspace {workspace_id}")

        # Look up account for this workspace
        account_id = await get_account_for_workspace(workspace_id)

        # Get fresh access token (with refresh if needed)
        access_token = await refresh_slack_token_if_needed(workspace_id)

        ninety_days_ago = (datetime.now() - timedelta(days=90)).timestamp()
        channels = await fetch_channel_list(access_token)
        total_messages = 0

        for channel in channels:
            channel_id = channel["id"]
            print(f"Syncing channel {channel.get('name','?')} ({channel_id})")

            messages = await fetch_channel_history(access_token, channel_id, str(ninety_days_ago))
            for message in messages:
                if message.get("subtype") == "bot_message" or not message.get("text"):
                    continue

                sentiment_score = calculate_sentiment_score(message.get("text", ""))
                mentions = []
                text = message.get("text", "")
                if "@" in text:
                    import re
                    mentions = re.findall(r'<@([^>]+)>', text)

                ts = float(message.get("ts", 0))
                created_at = datetime.fromtimestamp(ts).isoformat()

                message_data = {
                    "account_id": account_id,
                    "slack_channel_id": channel_id,
                    "slack_message_id": message.get("ts", ""),
                    "thread_ts": message.get("thread_ts", ""),
                    "user_id": message.get("user", ""),
                    "text": text,
                    "sentiment_score": sentiment_score,
                    "mentions": mentions,
                    "created_at": created_at
                }

                try:
                    await asyncio.to_thread(
                        supabase.table("slack_messages").upsert(
                            message_data, on_conflict="slack_channel_id,slack_message_id"
                        ).execute
                    )
                    total_messages += 1
                except Exception as e:
                    print(f"Error inserting message: {e}")
                    continue

        print(f"Completed sync for workspace {workspace_id}: {total_messages} messages")
        return {"status": "completed", "messages_synced": total_messages}

    except Exception as e:
        print(f"Error syncing workspace history: {e}")
        return {"status": "error", "error": str(e)}

async def refresh_zendesk_token_if_needed(subdomain: str) -> str:
    """
    Load token row. If no refresh_token, assume legacy non-expiring and return access_token.
    If near expiry, refresh and update DB. Return valid access_token.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        row = await asyncio.to_thread(
            supabase.table("zendesk_oauth_tokens")
            .select("access_token,refresh_token,expires_at")
            .eq("subdomain", subdomain).single().execute
        )
        if not row.data:
            raise HTTPException(status_code=401, detail=f"No Zendesk token found for subdomain {subdomain}")

        data = row.data
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_at = data.get("expires_at")

        if not refresh_token or not _needs_refresh(expires_at):
            return access_token

        try:
            client_id, client_secret, _ = await get_zendesk_creds_for(subdomain)
        except SecurityUpgradeRequired:
            raise HTTPException(status_code=400, detail="Please re-save your Zendesk credentials to upgrade security")

        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"https://{subdomain}.zendesk.com/oauth/tokens",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
        if r.status_code != 200:
            raise HTTPException(status_code=401, detail=f"Failed to refresh Zendesk token: {r.text}")

        j = r.json()
        new_access = j["access_token"]
        new_refresh = j.get("refresh_token", refresh_token)
        new_expires = j.get("expires_in")
        new_expires_at = _iso(datetime.now() + timedelta(seconds=new_expires)) if new_expires else None

        await asyncio.to_thread(
            supabase.table("zendesk_oauth_tokens").upsert({
                "subdomain": subdomain,
                "access_token": new_access,
                "refresh_token": new_refresh,
                "expires_at": new_expires_at,
            }, on_conflict="subdomain").execute
        )
        return new_access
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh Zendesk token: {str(e)}")

# --- Zendesk Helper Functions ---

async def fetch_zendesk_tickets(access_token: str, subdomain: str, days_back: int = 90, page: int = 1) -> Dict[str, Any]:
    """Fetch tickets from Zendesk API using OAuth access token"""
    if not access_token or not subdomain:
        raise ValueError("Access token and subdomain are required")
    
    # Calculate the date filter for the last N days
    start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    async with httpx.AsyncClient() as client:
        url = f"https://{subdomain}.zendesk.com/api/v2/search.json"
        params = {
            "query": f"type:ticket created>{start_date}",
            "sort_by": "created_at",
            "sort_order": "desc",
            "per_page": 100,
            "page": page
        }
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = await client.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(
                status_code=response.status_code, 
                detail=f"Zendesk API error: {response.text}"
            )

async def sync_zendesk_history(subdomain: str, days_back: int = 90) -> Dict[str, Any]:
    """Background job to sync historical Zendesk tickets"""
    try:
        print(f"Starting Zendesk history sync for subdomain {subdomain}, last {days_back} days")
        
        # Look up account for this subdomain
        account_id = await get_account_for_subdomain(subdomain)
        
        # Get fresh access token (with refresh if needed)
        access_token = await refresh_zendesk_token_if_needed(subdomain)
        
        total_tickets = 0
        page = 1
        has_more = True
        
        while has_more:
            print(f"Fetching page {page} from Zendesk...")
            
            data = await fetch_zendesk_tickets(access_token, subdomain, days_back, page)
            tickets = data.get("results", [])
            
            if not tickets:
                has_more = False
                break
            
            for ticket in tickets:
                # Extract ticket data
                zendesk_ticket_id = str(ticket.get("id", ""))
                subject = ticket.get("subject", "")
                description = ticket.get("description", "")
                status = ticket.get("status", "open")
                priority = ticket.get("priority", "normal")
                requester_id = str(ticket.get("requester_id", ""))
                tags = ticket.get("tags", [])
                created_at = ticket.get("created_at", "")
                updated_at = ticket.get("updated_at", "")
                
                # Calculate sentiment score
                full_text = f"{subject} {description}"
                sentiment_score = calculate_sentiment_score(full_text)
                
                # Find or create customer
                customer_data = {
                    "account_id": account_id,
                    "zendesk_id": requester_id,
                    "name": f"Customer {requester_id}",
                    "email": ticket.get("requester", {}).get("email", "") if ticket.get("requester") else ""
                }
                
                try:
                    # Upsert customer
                    customer_response = await asyncio.to_thread(
                        supabase.table("customers").upsert(
                            customer_data, 
                            on_conflict="zendesk_id"
                        ).execute
                    )
                    customer_id = customer_response.data[0]["id"] if customer_response.data else None
                    
                    # Insert ticket
                    ticket_data = {
                        "account_id": account_id,
                        "zendesk_ticket_id": zendesk_ticket_id,
                        "customer_id": customer_id,
                        "subject": subject,
                        "description": description,
                        "status": status,
                        "priority": priority,
                        "sentiment_score": sentiment_score,
                        "tags": tags,
                        "created_at": created_at,
                        "updated_at": updated_at
                    }
                    
                    await asyncio.to_thread(
                        supabase.table("tickets").upsert(
                            ticket_data, 
                            on_conflict="zendesk_ticket_id"
                        ).execute
                    )
                    total_tickets += 1
                    
                except Exception as e:
                    print(f"Error inserting ticket {zendesk_ticket_id}: {e}")
                    continue
            
            # Check if there are more pages
            has_more = data.get("next_page") is not None
            page += 1
            
            # Rate limiting: wait between requests
            await asyncio.sleep(0.5)
        
        print(f"Completed Zendesk sync: {total_tickets} tickets processed")
        return {"status": "completed", "tickets_synced": total_tickets}
        
    except Exception as e:
        print(f"Error syncing Zendesk history: {e}")
        return {"status": "error", "error": str(e)}

# --- Zendesk OAuth Helper Functions ---

async def exchange_zendesk_oauth_code(code: str, subdomain: str) -> Dict[str, Any]:
    """Exchange OAuth code for Zendesk access token."""
    try:
        client_id, client_secret, scopes = await get_zendesk_creds_for(subdomain)
    except SecurityUpgradeRequired:
        # This should not happen during OAuth flow, but if it does, return error
        raise HTTPException(status_code=400, detail="Please re-save your Zendesk credentials to upgrade security")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://{subdomain}.zendesk.com/oauth/tokens",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": f"{PUBLIC_BASE_URL}/zendesk/oauth/callback",
                "scope": scopes,
            },
        )
        return response.json()

async def create_zendesk_webhook(access_token: str, subdomain: str) -> Dict[str, Any]:
    """Create a webhook in the customer's Zendesk instance"""
    webhook_url = f"{PUBLIC_BASE_URL}/zendesk/webhooks/tickets/{subdomain}"
    
    webhook_data = {
        "webhook": {
            "name": "Catchalyze Ticket Updates",
            "endpoint": webhook_url,
            "http_method": "POST",
            "request_format": "json",
            "status": "active",
            "subscriptions": ["conditional_ticket_events"]
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://{subdomain}.zendesk.com/api/v2/webhooks",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=webhook_data
        )
        return response.json()

async def create_zendesk_trigger(access_token: str, subdomain: str, webhook_id: str) -> Dict[str, Any]:
    trigger_data = {
        "trigger": {
            "title": "Catchalyze Ticket Trigger",
            "active": True,
            "conditions": {
                "any": [
                    {"field": "update_type", "operator": "is", "value": "Create"},
                    {"field": "update_type", "operator": "is", "value": "Change"}
                ]
            },
            "actions": [
                {
                    "field": "notification_webhook",
                    "value": [
                        webhook_id,
                        """{
                            "ticket": {
                                "id": "{{ticket.id}}",
                                "title": "{{ticket.title}}",
                                "description": "{{ticket.description}}",
                                "latest_public_comment": "{{ticket.latest_public_comment}}",
                                "status": "{{ticket.status | downcase}}",
                                "priority": "{{ticket.priority | downcase}}",
                                "requester": {
                                    "id": "{{ticket.requester.id}}",
                                    "email": "{{ticket.requester.email}}",
                                    "name": "{{ticket.requester.name}}"
                                },
                                "tags": {% assign tag_array = ticket.tags | split: ' ' %}{% if tag_array.size > 0 %}[{% for tag in tag_array %}"{{tag}}"{% unless forloop.last %},{% endunless %}{% endfor %}]{% else %}[]{% endif %},
                                "created_at": "{{ticket.created_at_with_time}}",
                                "updated_at": "{{ticket.updated_at_with_time}}"
                            }
                        }"""
                    ]
                }
            ]
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://{subdomain}.zendesk.com/api/v2/triggers",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=trigger_data
        )
        return response.json()

async def setup_zendesk_integration(access_token: str, subdomain: str) -> Dict[str, Any]:
    """Complete setup of Zendesk integration (webhook + trigger)"""
    try:
        # Create webhook first
        print(f"Creating webhook for Zendesk subdomain: {subdomain}")
        webhook_response = await create_zendesk_webhook(access_token, subdomain)
        
        if "webhook" not in webhook_response:
            return {"status": "error", "error": "Failed to create webhook", "response": webhook_response}
        
        webhook_id = str(webhook_response["webhook"]["id"])
        print(f"Webhook created with ID: {webhook_id}")
        
        # Create trigger that uses the webhook
        print(f"Creating trigger for webhook ID: {webhook_id}")
        trigger_response = await create_zendesk_trigger(access_token, subdomain, webhook_id)
        
        if "trigger" not in trigger_response:
            return {"status": "error", "error": "Failed to create trigger", "response": trigger_response}
        
        trigger_id = str(trigger_response["trigger"]["id"])
        print(f"Trigger created with ID: {trigger_id}")
        
        return {
            "status": "success",
            "webhook_id": webhook_id,
            "trigger_id": trigger_id,
            "webhook_url": f"{PUBLIC_BASE_URL}/zendesk/webhooks/tickets/{subdomain}"
        }
        
    except Exception as e:
        print(f"Error setting up Zendesk integration: {e}")
        return {"status": "error", "error": str(e)}

async def update_daily_metrics(topic_id: str, day: str, count_delta: int = 1, sentiment: float = None):
    """Update daily metrics for a topic using the RPC function"""
    try:
        await asyncio.to_thread(
            supabase.rpc('upsert_topic_daily_metrics', {
                'p_topic_id': topic_id,
                'p_account_id': ACCOUNT_ID,
                'p_day': day,
                'p_count_delta': count_delta,
                'p_sentiment': sentiment  # Can be None, the RPC function handles it
            }).execute
        )
    except Exception as e:
        print(f"[metrics] failed to update daily metrics for topic {topic_id}: {e}")

async def backfill_daily_metrics():
    """Backfill daily metrics for the last DAILY_METRICS_CUTOFF_DAYS"""
    try:
        cutoff_date = datetime.now() - timedelta(days=DAILY_METRICS_CUTOFF_DAYS)
        
        # Get all embeddings for recalculation
        embeddings_resp = await asyncio.to_thread(
            supabase.table("embeddings_store")
            .select("*, topic_membership(topic_id)")
            .eq("account_id", ACCOUNT_ID)
            .gte("ts", cutoff_date.isoformat())
            .execute
        )
        
        if not embeddings_resp.data:
            return
        
        # Group by topic and day
        metrics = {}
        for embedding in embeddings_resp.data:
            if not embedding.get("topic_membership"):
                continue
            
            topic_id = embedding["topic_membership"][0]["topic_id"]
            day = embedding["ts"][:10]  # Extract date part
            sentiment = embedding.get("sentiment")
            
            key = (topic_id, day)
            if key not in metrics:
                metrics[key] = {"count": 0, "sentiments": []}
            
            metrics[key]["count"] += 1
            if sentiment is not None:
                metrics[key]["sentiments"].append(sentiment)
        
        # Update metrics
        for (topic_id, day), data in metrics.items():
            avg_sentiment = statistics.mean(data["sentiments"]) if data["sentiments"] else None
            
            await asyncio.to_thread(
                supabase.rpc('upsert_topic_daily_metrics', {
                    'p_topic_id': topic_id,
                    'p_account_id': ACCOUNT_ID,
                    'p_day': day,
                    'p_count_delta': data["count"],
                    'p_sentiment': avg_sentiment
                }).execute
            )
        
        print(f"[metrics] backfilled {len(metrics)} daily metrics")
        
    except Exception as e:
        print(f"[metrics] backfill failed: {e}")


# --- Topic Clustering Constants ---
ASSIGN_THRESHOLD = 0.35
MERGE_THRESHOLD = 0.92
COHESION_FLOOR = 0.65
SPIKE_Z = 0.5
MIN_TODAY_VOLUME = 4
SENTIMENT_DROP = 0.15
MIN_TOPIC_SIZE_14D = 2
RECLUSTER_WINDOW_DAYS = 30
RECLUSTER_INTERVAL_SEC = 900  # 15 minutes
DAILY_METRICS_CUTOFF_DAYS = 60
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
CACHE_SIZE = 1000
CACHE_TTL_SEC = 600  # 10 minutes

BETA_METRICS_LOGGING = True

# Global account_id for tenant isolation (development fallback)
DEFAULT_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"

# Rate limiting storage (simple in-memory for beta)
rate_limit_store = defaultdict(list)
ACCOUNT_ID = DEFAULT_ACCOUNT_ID

# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_SCOPES = "openid email profile"

def get_account_id_from_request(request: Request = None) -> str:
    """Extract account_id from request context or raise authentication error."""
    if not request:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Try to extract from JWT token in cookie
    try:
        import jwt
        auth_cookie = request.cookies.get("auth_token")
        if auth_cookie:
            payload = jwt.decode(auth_cookie, JWT_SECRET, algorithms=["HS256"])
            account_id = payload["account_id"]
            return account_id
    except Exception as e:
        print(f"[DEBUG] JWT decode failed: {e}")
    
    # No valid authentication found
    raise HTTPException(status_code=401, detail="Authentication required")

# def _cookie_secure() -> bool:
#     """Determine if cookies should be secure based on environment."""
#     return not (PUBLIC_BASE_URL and ("localhost" in PUBLIC_BASE_URL or "127.0.0.1" in PUBLIC_BASE_URL))

# --- LRU Cache Implementation ---
class LRUCache:
    def __init__(self, capacity: int, ttl_seconds: int = 600):
        self.capacity = capacity
        self.ttl_seconds = ttl_seconds
        self.cache = OrderedDict()
        self.timestamps = {}
    
    def get(self, key):
        if key not in self.cache:
            return None
        
        # Check TTL
        if time.time() - self.timestamps[key] > self.ttl_seconds:
            del self.cache[key]
            del self.timestamps[key]
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.capacity:
                # Remove least recently used item
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
            self.cache[key] = value
        
        self.timestamps[key] = time.time()

# Global topic cache
topic_cache = LRUCache(CACHE_SIZE, CACHE_TTL_SEC)

# --- Text Normalization & Hashing ---
def normalize_text(text: str) -> str:
    """Normalize text for consistent hashing and processing"""
    if not text:
        return ""
    
    # Lowercase, trim, collapse whitespace
    text = re.sub(r'\s+', ' ', text.lower().strip())
    
    # Optional: strip URLs (keeping emojis)
    text = re.sub(r'https?://[^\s]+', '', text)
    
    return text

def get_canonical_text(source: str, data: dict, one_line: str = None) -> str:
    """Get canonical text for embedding/hashing"""
    if one_line:
        return one_line[:200]
    
    if source == "ticket":
        subject = data.get("subject", "")
        description = data.get("description", "")
        combined = f"{subject}\n{description}"
    elif source == "slack":
        combined = data.get("text", "")
    else:
        combined = str(data)
    
    return normalize_text(combined)[:1000]

def hash_text(text: str) -> str:
    """Generate SHA256 hash of canonical text"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

# --- Embedding Functions ---
async def get_embedding(text: str, account_id: str = DEFAULT_ACCOUNT_ID) -> Optional[List[float]]:
    """Get embedding for text, with caching"""
    if not openai_client or not text.strip():
        return None
    
    # Check cache first
    text_hash = hash_text(text)
    cache_key = f"{account_id}:{text_hash}:{EMBEDDING_MODEL}:{EMBEDDING_DIM}"
    
    cached = topic_cache.get(cache_key)
    if cached:
        return cached
    
    try:
        response = await openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
            encoding_format="float"
        )
        
        embedding = response.data[0].embedding
        if len(embedding) != EMBEDDING_DIM:
            print(f"Warning: embedding dimension mismatch: {len(embedding)} != {EMBEDDING_DIM}")
            return None
        
        # Normalize for cosine similarity
        embedding_array = np.array(embedding)
        norm = np.linalg.norm(embedding_array)
        if norm > 0:
            embedding = (embedding_array / norm).tolist()
        
        # Cache the result
        topic_cache.put(cache_key, embedding)
        return embedding
        
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return None

async def batch_get_embeddings(texts: List[str], account_id: str = DEFAULT_ACCOUNT_ID) -> List[Optional[List[float]]]:
    """Get embeddings for multiple texts efficiently"""
    if not texts:
        return []
    
    # Check cache for each text
    results = []
    uncached_texts = []
    uncached_indices = []
    
    for i, text in enumerate(texts):
        if not text.strip():
            results.append(None)
            continue
            
        text_hash = hash_text(text)
        cache_key = f"{account_id}:{text_hash}:{EMBEDDING_MODEL}:{EMBEDDING_DIM}"
        
        cached = topic_cache.get(cache_key)
        if cached:
            results.append(cached)
        else:
            results.append(None)  # Placeholder
            uncached_texts.append(text)
            uncached_indices.append(i)
    
    # Batch process uncached texts
    if uncached_texts and openai_client:
        try:
            response = await openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=uncached_texts,
                encoding_format="float"
            )
            
            for idx, embedding_data in enumerate(response.data):
                original_idx = uncached_indices[idx]
                embedding = embedding_data.embedding
                
                if len(embedding) == EMBEDDING_DIM:
                    # Normalize
                    embedding_array = np.array(embedding)
                    norm = np.linalg.norm(embedding_array)
                    if norm > 0:
                        normalized_embedding = (embedding_array / norm).tolist()
                        results[original_idx] = normalized_embedding
                        
                        # Cache it
                        text_hash = hash_text(uncached_texts[idx])
                        cache_key = f"{account_id}:{text_hash}:{EMBEDDING_MODEL}:{EMBEDDING_DIM}"
                        topic_cache.put(cache_key, normalized_embedding)
                        
        except Exception as e:
            print(f"Error in batch embeddings: {e}")
    
    return results

# --- Topic Assignment Functions ---
async def find_nearest_topic(embedding: List[float], account_id: str = DEFAULT_ACCOUNT_ID) -> Optional[dict]:
    """Find the nearest topic using cosine similarity"""
    if not supabase or not embedding:
        return None
    
    try:
        # Query active topics for this account
        response = await asyncio.to_thread(
            supabase.table("topics")
            .select("topic_id, centroid, cohesion, name, keywords")
            .eq("account_id", account_id)
            .eq("state", "active")
            .gte("cohesion", COHESION_FLOOR)
            .execute
        )
        
        if not response.data:
            return None
        
        best_topic = None
        best_similarity = 0.0
        
        for topic in response.data:
            try:
                # Convert string representation of vector back to list
                centroid = topic["centroid"]
                if isinstance(centroid, str):
                    # Parse vector string format
                    centroid = list(map(float, centroid.strip('[]').split(',')))
                elif isinstance(centroid, list):
                    centroid = [float(x) for x in centroid]
                else:
                    continue
                
                if len(centroid) != EMBEDDING_DIM:
                    continue
                
                # Calculate cosine similarity
                similarity = np.dot(embedding, centroid)
                
                if similarity > best_similarity and similarity >= ASSIGN_THRESHOLD:
                    best_similarity = similarity
                    best_topic = {
                        **topic,
                        "similarity": similarity
                    }
                    
            except Exception as e:
                print(f"Error processing topic {topic.get('topic_id')}: {e}")
                continue
        
        return best_topic
        
    except Exception as e:
        print(f"Error finding nearest topic: {e}")
        return None


async def assign_to_topic(embedding_id: str, topic_id: str, account_id: str = DEFAULT_ACCOUNT_ID):
    """Assign an embedding to a topic"""
    if not supabase:
        return
    
    try:
        await asyncio.to_thread(
            supabase.table("topic_membership")
            .upsert({
                "topic_id": topic_id,
                "embedding_id": embedding_id, 
                "account_id": account_id
            })
            .execute
        )
        
        # Update daily metrics
        today = datetime.now().date()
        
        # Get embedding data for sentiment
        embedding_resp = await asyncio.to_thread(
            supabase.table("embeddings_store")
            .select("sentiment")
            .eq("id", embedding_id)
            .single()
            .execute
        )
        
        sentiment = embedding_resp.data.get("sentiment") if embedding_resp.data else None
        
        await update_daily_metrics(
            topic_id=topic_id,
            day=today.isoformat(), 
            count_delta=1,
            sentiment=sentiment
        )
        
    except Exception as e:
        print(f"Error assigning to topic: {e}")

# --- Topic Processing Functions ---
async def process_content_for_topics(source: str, source_id: str, data: dict, 
                                   customer_id: str = None, channel_id: str = None,
                                   account_id: str = None):
    """Process content (ticket/slack message) for topic assignment"""
    print(f"[DEBUG] process_content_for_topics called: source={source}, source_id={source_id}")
    
    # Get account_id from parameter or context
    if not account_id:
        account_id = get_current_account_id()
    
    if not supabase:
        return
    
    try:
        # Simple extraction of user identifier from webhook data
        user_identifier = None
        if source == "slack":
            user_identifier = data.get("user_id")  # Direct from webhook
            print(f"[DEBUG] Slack user_identifier: '{user_identifier}' from webhook data: {data.keys()}")
        elif source == "ticket":
            user_identifier = customer_id or data.get("customer_id")  # From parameter or webhook
            print(f"[DEBUG] Ticket user_identifier: '{user_identifier}' (customer_id={customer_id}, data.customer_id={data.get('customer_id')})")
        
        # Get or create one_line summary
        if source == "ticket":
            summaries = await ensure_ticket_summaries([{"id": source_id, **data}])
            one_line = summaries.get(source_id, "")
        elif source == "slack":
            summaries = await ensure_slack_summaries([{"id": source_id, **data}])
            one_line = summaries.get(source_id, "")
        else:
            one_line = str(data)[:200]
        
        # Get canonical text and hash
        canonical_text = get_canonical_text(source, data, one_line)
        text_hash = hash_text(canonical_text)
        
        # Check if we already processed this content
        existing_resp = await asyncio.to_thread(
            supabase.table("embeddings_store")
            .select("id")
            .eq("account_id", account_id)
            .eq("source", source)
            .eq("source_id", source_id)
            .execute
        )
        
        if existing_resp.data:
            return  # Already processed
        
        # Get embedding
        embedding = await get_embedding(canonical_text, account_id)
        if not embedding:
            print("[DEBUG] Failed to get embedding")
            return

        print(f"[DEBUG] Got embedding, length: {len(embedding)}")
        
        # Calculate sentiment
        sentiment = calculate_sentiment_score(canonical_text)
        
        # Store embedding WITH user_identifier and account_id
        embedding_data = {
            "account_id": account_id,
            "source": source,
            "source_id": source_id,
            "user_identifier": user_identifier,
            "ts": datetime.now().isoformat(),
            "customer_id": customer_id,
            "channel_id": channel_id,
            "one_line": one_line,
            "sentiment": sentiment,
            "text_hash": text_hash,
            "embedding": embedding
        }
        
        embedding_resp = await asyncio.to_thread(
            supabase.table("embeddings_store")
            .upsert(embedding_data, on_conflict="account_id,source,source_id")
            .execute
        )
        
        if not embedding_resp.data:
            return
        
        embedding_id = embedding_resp.data[0]["id"]
        
        # Find nearest topic
        nearest_topic = await find_nearest_topic(embedding, account_id)
        
        if nearest_topic:
            # Assign to existing topic
            await assign_to_topic(embedding_id, nearest_topic["topic_id"], account_id)
        else:
            # Create new topic
            topic_id = await create_topic(embedding, canonical_text, account_id)
            if topic_id:
                await assign_to_topic(embedding_id, topic_id, account_id)
        
    except Exception as e:
        print(f"Error processing content for topics: {e}")

# --- Trend Detection ---
async def detect_trending_topics(account_id: str = DEFAULT_ACCOUNT_ID,
                                 time_window_minutes: int = None,
                                 start_time: datetime = None,
                                 end_time: datetime = None,
                                 broadcast: bool = True) -> List[dict]:
    """Detect topics with significant volume spikes or sentiment drops"""
    if not supabase:
        return []
    
    topic_data = {}
    
    # Determine time window type and parameters
    if start_time and end_time:
        # Granular window (for micro-batching)
        window_start = start_time
        window_end = end_time
        window_duration_minutes = (end_time - start_time).total_seconds() / 60
        print(f"[trending] Checking granular window: {window_start} to {window_end} ({window_duration_minutes:.1f} minutes)")
        
        # For micro-batching, use simple volume-based detection
        try:
            # Get embeddings in the time window
            embeddings_resp = await asyncio.to_thread(
                supabase.table("embeddings_store")
                .select("id, topic_membership(topic_id), sentiment, ts, source, user_identifier")
                .eq("account_id", account_id)
                .gte("ts", window_start.isoformat())
                .lt("ts", window_end.isoformat())
                .execute
            )
            
            if not embeddings_resp.data:
                return []
            
            print(f"[DEBUG] Found {len(embeddings_resp.data)} embeddings in 180-minute window")
            
            print(f"[trending] Found {len(embeddings_resp.data)} embeddings in window")
            
            # Group by topic
            topic_data = {}
            for emb in embeddings_resp.data:
                print(f"[DEBUG] Processing embedding: source={emb.get('source')}, topic_membership={emb.get('topic_membership')}")
                if emb.get("topic_membership"):
                    topic_id = emb["topic_membership"][0]["topic_id"]
                    if topic_id not in topic_data:
                        topic_data[topic_id] = {
                            "count": 0,
                            "sentiments": [],
                            "sources": set(),
                            "embeddings": []
                        }
                    
                    topic_data[topic_id]["count"] += 1
                    topic_data[topic_id]["sources"].add(emb.get("source", "unknown"))
                    topic_data[topic_id]["embeddings"].append(emb)
                    
                    if emb.get("sentiment") is not None:
                        topic_data[topic_id]["sentiments"].append(emb["sentiment"])
            
            # Analyze each topic for trends
            trending_topics = []
            
            for topic_id, data in topic_data.items():
                count = data["count"]
                print(f"[DEBUG] Topic {topic_id}: {count} messages, volume threshold check next")
                avg_sentiment = statistics.mean(data["sentiments"]) if data["sentiments"] else None
                
                # Get topic metadata
                topic_resp = await asyncio.to_thread(
                    supabase.table("topics")
                    .select("name, keywords, cohesion")
                    .eq("topic_id", topic_id)
                    .eq("account_id", account_id)
                    .single()
                    .execute
                )
                
                if not topic_resp.data:
                    continue
                
                topic_meta = topic_resp.data
                
                # Micro-batch: hybrid volume threshold with sentiment filtering
                messages_per_minute = count / window_duration_minutes

                # Hybrid threshold: consider both rate and absolute count
                if window_duration_minutes <= 2:  # Very short window
                    volume_threshold = 0.5  # 1 message every 2 minutes
                    min_count = 4
                elif window_duration_minutes <= 10:  # Short window
                    volume_threshold = 0.3  # 1 message every 3 minutes  
                    min_count = 4
                elif window_duration_minutes <= 60:  # Medium window (1 hour)
                    volume_threshold = 0.05  # 1 message every 20 minutes
                    min_count = 4
                elif window_duration_minutes <= 180:  # 3 hour window
                    volume_threshold = 0.02  # 1 message every 50 minutes
                    min_count = 4
                else:  # Long window (24 hours+)
                    volume_threshold = 0.001  # 1 message every 333 minutes (5.5 hours) - more lenient
                    min_count = 3  # Require at least 3 messages for long windows

                # Check both rate and count thresholds
                volume_check_passed = (messages_per_minute >= volume_threshold and count >= min_count)

                print(f"[DEBUG] Volume check: {messages_per_minute:.4f} >= {volume_threshold} and {count} >= {min_count} = {volume_check_passed}")

                if BETA_METRICS_LOGGING:
                    timestamp = datetime.now().isoformat()
                    print(f"[BETA_METRICS] {timestamp} Topic {topic_id}: count={count}, min_required={min_count}, users_found={len(data['embeddings'])}")
                    if not volume_check_passed:
                        print(f"[BETA_METRICS] {timestamp} REJECTED_VOLUME: Topic {topic_id} failed volume check: {count} < {min_count}")

                if volume_check_passed:
                    # DEBUG: Check diversity calculation
                    print(f"[DEBUG] Checking diversity for topic {topic_id}")
                    print(f"  Total embeddings: {len(data['embeddings'])}")

                    user_identifier_values = [emb.get("user_identifier") for emb in data["embeddings"]]
                    print(f"  User identifier values: {user_identifier_values}")

                    # Simple diversity check that handles nulls and empty strings gracefully
                    unique_users = {
                        emb.get("user_identifier") 
                        for emb in data["embeddings"] 
                        if emb.get("user_identifier") not in (None, "", "null")
                    }
                    print(f"  Unique users found: {unique_users}")

                    if BETA_METRICS_LOGGING:
                        print(f"[BETA_METRICS] PASSED_VOLUME: Topic {topic_id} passed volume check: {count} >= {min_count}")
                        print(f"[BETA_METRICS] USER_DIVERSITY: Topic {topic_id} has {len(unique_users)} unique users (min_required=3)")

                    # If we can't identify enough users, be conservative
                    if len(unique_users) < 3:
                        if BETA_METRICS_LOGGING:
                            timestamp = datetime.now().isoformat()
                            print(f"[BETA_METRICS] {timestamp} REJECTED_USER_DIVERSITY: Topic {topic_id} failed user diversity: {len(unique_users)} < 3")
                        print(f"[trending] Skipping topic {topic_id}: only {len(unique_users)} identifiable users")
                        continue
                    
                    # Only detect trends for negative/neutral sentiment
                    print(f"[DEBUG] Topic {topic_id} sentiment check: avg_sentiment={avg_sentiment}, threshold=0.3")
                    if avg_sentiment is None or avg_sentiment <= 0.3:  # Negative/neutral only
                        print(f"[DEBUG] Processing topic {topic_id}: sentiment acceptable ({avg_sentiment})")
                        # Calculate impact metrics
                        impact_data = await calculate_topic_impact(topic_id, account_id)
                        
                        # Get evidence IDs for this window
                        evidence_ids = await get_topic_evidence_ids_granular_with_retry(topic_id, window_start, window_end, account_id)
                        
                        # Generate root cause hint
                        root_cause_hint = await generate_root_cause_hint(topic_id, account_id)
                        
                        trending_topic = {
                            "topic_id": topic_id,
                            "name": topic_meta.get("name"),
                            "keywords": topic_meta.get("keywords", []),
                            "cohesion": topic_meta.get("cohesion", 0.0),
                            "volume_spike": True,
                            "sentiment_drop": False,
                            "z_score": messages_per_minute,  # Use rate as z-score equivalent
                            "count_in_window": count,
                            "messages_per_minute": messages_per_minute,
                            "avg_sentiment": avg_sentiment,
                            "sources": list(data["sources"]),
                            "impact": impact_data,
                            "evidence_ids": evidence_ids,
                            "root_cause_hint": root_cause_hint,
                            "window_start": window_start.isoformat(),
                            "window_end": window_end.isoformat(),
                            "detection_method": "micro_batch"
                        }

                        insights_resp = await asyncio.to_thread(
                            supabase.table("insights")
                            .select("title, recommended_action, playbook_steps, description, data")
                            .eq("type", "trend")
                            .eq("data->>topic_id", str(topic_id))
                            .order("created_at", desc=True)
                            .limit(1)
                            .execute
                        )

                        if insights_resp.data:
                            insight = insights_resp.data[0]
                            trending_topic.update({
                                "recommended_action": insight.get("recommended_action"),
                                "playbook_steps": insight.get("playbook_steps", []),
                                "title": insight.get("title"),
                                "description": insight.get("description"),
                                "affected_customers": insight.get("affected_customers"),
                                "customer_percentage": insight.get("data", {}).get("impact_metrics", {}).get("customer_percentage")
                            })
                        
                        trending_topics.append(trending_topic)
                    else:
                        print(f"[trending] Skipping positive sentiment topic (sentiment: {avg_sentiment})")
            
            # Sort by volume rate
            trending_topics.sort(key=lambda x: x["messages_per_minute"], reverse=True)
            
            if BETA_METRICS_LOGGING:
                total_topics_analyzed = len(topic_data)
                volume_passed = sum(1 for t in topic_data.values() if t["count"] >= min_count)
                print(f"[BETA_METRICS] SUMMARY: {total_topics_analyzed} topics analyzed, {volume_passed} passed volume, {len(trending_topics)} final trends")
            # Broadcast new trends to SSE clients if any found
            if broadcast and trending_topics:
                await broadcast_to_account_clients(account_id, {
                    "type": "new_trends",
                    "trends": trending_topics,
                    "timestamp": datetime.now().isoformat(),
                    "detection_method": "micro_batch"
                })
            return trending_topics
            
        except Exception as e:
            print(f"Error in micro-batch trend detection: {e}")
            return []
            
    elif time_window_minutes:
        # Relative window (for scheduled jobs) - use granular detection
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=time_window_minutes)
        
        print(f"[trending] Checking last {time_window_minutes} minutes since {start_time}")
        
        # Use the same granular logic as micro-batch
        return await detect_trending_topics(
            account_id=account_id,
            start_time=start_time,
            end_time=end_time
        )
    else:
        # Full day (existing behavior) - your original logic
        cutoff = datetime.now().date()
        print(f"[trending] Checking full day: {cutoff}")
        
        try:
            today = datetime.now().date()
            baseline_start = today - timedelta(days=14)
            
            # Get daily metrics for active topics
            metrics_resp = await asyncio.to_thread(
                supabase.table("topic_daily_metrics")
                .select("topic_id, day, count, avg_sentiment")
                .eq("account_id", account_id)
                .gte("day", baseline_start.isoformat())
                .execute
            )
            
            if not metrics_resp.data:
                return []
            
            # Group by topic
            topic_metrics = {}
            for metric in metrics_resp.data:
                topic_id = metric["topic_id"]
                if topic_id not in topic_metrics:
                    topic_metrics[topic_id] = []
                topic_metrics[topic_id].append(metric)
            
            trending_topics = []
            
            for topic_id, metrics in topic_metrics.items():
                # Check if topic meets size requirements
                total_volume = sum(m["count"] for m in metrics)
                if total_volume < MIN_TOPIC_SIZE_14D:
                    continue
                
                # Separate today's metrics from baseline
                today_metrics = [m for m in metrics if m["day"] == today.isoformat()]
                baseline_metrics = [m for m in metrics if m["day"] != today.isoformat()]
                
                if not today_metrics or not baseline_metrics:
                    continue
                
                today_count = sum(m["count"] for m in today_metrics)
                today_sentiment = statistics.mean([m["avg_sentiment"] for m in today_metrics if m["avg_sentiment"] is not None]) if any(m["avg_sentiment"] is not None for m in today_metrics) else None
                
                baseline_counts = [m["count"] for m in baseline_metrics]
                baseline_sentiments = [m["avg_sentiment"] for m in baseline_metrics if m["avg_sentiment"] is not None]
                
                if not baseline_counts:
                    continue
                
                baseline_avg = statistics.mean(baseline_counts)
                baseline_std = statistics.stdev(baseline_counts) if len(baseline_counts) > 1 else 0
                
                # Volume spike detection
                volume_spike = False
                z_score = 0.0
                
                if baseline_std > 0 and baseline_avg >= 0.1:  # Minimum baseline activity
                    z_score = (today_count - baseline_avg) / baseline_std
                    if z_score >= SPIKE_Z and today_count >= MIN_TODAY_VOLUME:
                        volume_spike = True
                
                # Sentiment drop detection
                sentiment_drop = False
                sentiment_delta = 0.0
                
                if today_sentiment is not None and baseline_sentiments:
                    baseline_sentiment_avg = statistics.mean(baseline_sentiments)
                    baseline_sentiment_std = statistics.stdev(baseline_sentiments) if len(baseline_sentiments) > 1 else 0
                    
                    sentiment_delta = baseline_sentiment_avg - today_sentiment
                    if sentiment_delta >= SENTIMENT_DROP and baseline_sentiment_std > 0:
                        sentiment_drop = True
                
                # If either condition is met, it's trending
                if volume_spike or sentiment_drop:
                    # Get topic details
                    topic_resp = await asyncio.to_thread(
                        supabase.table("topics")
                        .select("name, keywords, cohesion")
                        .eq("topic_id", topic_id)
                        .eq("account_id", account_id)
                        .single()
                        .execute
                    )
                    
                    if not topic_resp.data:
                        continue
                    
                    topic_data = topic_resp.data
                    
                    # Calculate impact metrics
                    impact_data = await calculate_topic_impact(topic_id, account_id)
                    
                    # Get evidence IDs
                    evidence_ids = await get_topic_evidence_ids(topic_id, today, account_id)
                    
                    # Generate root cause hint
                    root_cause_hint = await generate_root_cause_hint(topic_id, account_id)
                    
                    trending_topic = {
                        "topic_id": topic_id,
                        "name": topic_data.get("name"),
                        "keywords": topic_data.get("keywords", []),
                        "cohesion": topic_data.get("cohesion", 0.0),
                        "volume_spike": volume_spike,
                        "sentiment_drop": sentiment_drop,
                        "z_score": z_score,
                        "count_today": today_count,
                        "baseline_avg": baseline_avg,
                        "avg_sentiment_today": today_sentiment,
                        "sentiment_delta": sentiment_delta,
                        "impact": impact_data,
                        "evidence_ids": evidence_ids,
                        "root_cause_hint": root_cause_hint,
                        "detection_method": "daily_baseline"
                    }
                    
                    trending_topics.append(trending_topic)
            
            return trending_topics
            
        except Exception as e:
            print(f"Error in daily trend detection: {e}")
            return []

async def backfill_user_identifiers():
    """Simple backfill - no complex error handling needed"""
    
    resp = await supabase.table("embeddings_store").select("*").is_("user_identifier", "null").execute()

    print(f"Found {len(resp.data)} embeddings without user identifiers - this is expected for historical data")

async def get_topic_evidence_ids_granular(topic_id: str, start_time: datetime, end_time: datetime, account_id: str = DEFAULT_ACCOUNT_ID) -> dict:
    """Get evidence IDs for a topic in a specific time window"""
    try:
        # Get embedding IDs for this topic first
        membership_resp = await asyncio.to_thread(
            supabase.table("topic_membership")
            .select("embedding_id")
            .eq("topic_id", topic_id)
            .eq("account_id", account_id)
            .execute
        )
        
        embedding_ids = [m["embedding_id"] for m in membership_resp.data] if membership_resp.data else []
        
        if not embedding_ids:
            return {"tickets": [], "slack_messages": []}
        
        # Get embeddings for this topic from the specified time window
        window_embeddings_resp = await asyncio.to_thread(
            supabase.table("embeddings_store")
            .select("id, source, source_id, ts, sentiment")
            .eq("account_id", account_id)
            .gte("ts", start_time.isoformat())
            .lt("ts", end_time.isoformat())
            .in_("id", embedding_ids)
            .order("ts", desc=True)
            .limit(10)
            .execute
        )
        
        evidence_ids = {"tickets": [], "slack_messages": []}
        
        if window_embeddings_resp.data:
            for embedding in window_embeddings_resp.data[:5]:
                if embedding["source"] == "ticket":
                    # For tickets, source_id is the zendesk_ticket_id, need to find database row ID
                    ticket_resp = await asyncio.to_thread(
                        supabase.table("tickets")
                        .select("id")
                        .eq("zendesk_ticket_id", embedding["source_id"])
                        .single()
                        .execute
                    )
                    if ticket_resp.data:
                        evidence_ids["tickets"].append(ticket_resp.data["id"])
                elif embedding["source"] == "slack":
                    # For Slack, source_id might be the database row ID already
                    # But let's be safe and look it up by slack_message_id
                    slack_resp = await asyncio.to_thread(
                        supabase.table("slack_messages")
                        .select("id")
                        .eq("slack_message_id", embedding["source_id"])
                        .single()
                        .execute
                    )
                    if slack_resp.data:
                        evidence_ids["slack_messages"].append(slack_resp.data["id"])
        
        print(f"[DEBUG] Evidence IDs found: {evidence_ids}")
        return evidence_ids
        
    except Exception as e:
        print(f"Error getting granular topic evidence: {e}")
        import traceback
        traceback.print_exc()
        return {"tickets": [], "slack_messages": []}

# --- Helper Functions for Active Trends State Management ---

async def check_active_trend(topic_id: str, trend_type: str, account_id: str = DEFAULT_ACCOUNT_ID) -> bool:
    """Check if a trend is already active (to prevent duplicate alerts)"""
    if not supabase:
        return False
    
    try:
        # Check for active trend in last 30 minutes
        cutoff = (datetime.now() - timedelta(minutes=30)).isoformat()
        
        active_resp = await asyncio.to_thread(
            supabase.table("active_trends")
            .select("id")
            .eq("account_id", account_id)
            .eq("topic_id", topic_id)
            .eq("trend_type", trend_type)
            .eq("is_active", True)
            .gte("created_at", cutoff)
            .execute
        )
        
        return bool(active_resp.data)
        
    except Exception as e:
        print(f"Error checking active trend: {e}")
        return False

async def mark_trend_active(
    topic_id: str, 
    trend_type: str, 
    trend_data: dict, 
    account_id: str = DEFAULT_ACCOUNT_ID
) -> str:
    """Mark a trend as active and return the trend ID"""
    if not supabase:
        return None
    
    try:
        trend_record = {
            "account_id": account_id,
            "topic_id": topic_id,
            "trend_type": trend_type,
            "trend_data": trend_data,
            "is_active": True,
            "created_at": datetime.now().isoformat()
        }
        
        resp = await asyncio.to_thread(
            supabase.table("active_trends")
            .insert(trend_record)
            .execute
        )
        
        return resp.data[0]["id"] if resp.data else None
        
    except Exception as e:
        print(f"Error marking trend active: {e}")
        return None

async def cleanup_stale_trends(account_id: str = DEFAULT_ACCOUNT_ID):
    """Clean up trends older than 1 hour"""
    if not supabase:
        return
    
    try:
        cutoff = (datetime.now() - timedelta(hours=1)).isoformat()
        
        await asyncio.to_thread(
            supabase.table("active_trends")
            .update({"is_active": False})
            .eq("account_id", account_id)
            .eq("is_active", True)
            .lt("created_at", cutoff)
            .execute
        )
        
    except Exception as e:
        print(f"Error cleaning up stale trends: {e}")

async def calculate_topic_impact(topic_id: str, account_id: str = DEFAULT_ACCOUNT_ID) -> dict:
    """Calculate business impact metrics for a topic"""
    try:
        # Get embedding IDs for this topic first
        membership_resp = await asyncio.to_thread(
            supabase.table("topic_membership")
            .select("embedding_id")
            .eq("topic_id", topic_id)
            .eq("account_id", account_id)
            .execute
        )
        
        embedding_ids = [m["embedding_id"] for m in membership_resp.data] if membership_resp.data else []
        
        if not embedding_ids:
            return {
                "customer_count": 0,
                "customer_percentage": 0.0,
                "estimated_revenue_impact": None
            }
        
        # Get unique customers affected by this topic via embeddings
        customers_resp = await asyncio.to_thread(
            supabase.table("embeddings_store")
            .select("customer_id")
            .eq("account_id", account_id)
            .not_.is_("customer_id", "null")
            .in_("id", embedding_ids)
            .execute
        )
        
        unique_customers = set()
        if customers_resp.data:
            for item in customers_resp.data:
                if item["customer_id"]:
                    unique_customers.add(item["customer_id"])
        
        customer_count = len(unique_customers)
        
        # Get total customer count for percentage
        total_customers_resp = await asyncio.to_thread(
            supabase.table("customers")
            .select("id", count="exact")
            .execute
        )
        
        total_customers = total_customers_resp.count or 1
        customer_percentage = (customer_count / total_customers) * 100
        
        # Estimate revenue impact (placeholder - would be enhanced with real data)
        estimated_revenue_impact = None
        if customer_count > 0:
            # Simple estimate: assume $1000 average customer value
            estimated_revenue_impact = customer_count * 1000
        
        return {
            "customer_count": customer_count,
            "customer_percentage": round(customer_percentage, 1),
            "estimated_revenue_impact": estimated_revenue_impact
        }
        
    except Exception as e:
        print(f"Error calculating topic impact: {e}")
        return {
            "customer_count": 0,
            "customer_percentage": 0.0,
            "estimated_revenue_impact": None
        }

async def get_topic_evidence_ids(topic_id: str, day: datetime.date, account_id: str = DEFAULT_ACCOUNT_ID) -> dict:
    """Get evidence IDs for a topic on a specific day"""
    try:
        # Get embedding IDs for this topic first
        membership_resp = await asyncio.to_thread(
            supabase.table("topic_membership")
            .select("embedding_id")
            .eq("topic_id", topic_id)
            .eq("account_id", account_id)
            .execute
        )
        
        embedding_ids = [m["embedding_id"] for m in membership_resp.data] if membership_resp.data else []
        
        if not embedding_ids:
            return {"tickets": [], "slack_messages": []}
        
        # Get embeddings for this topic from the specified day
        today_embeddings_resp = await asyncio.to_thread(
            supabase.table("embeddings_store")
            .select("id, source, source_id, ts, sentiment")
            .eq("account_id", account_id)
            .gte("ts", day.isoformat())
            .lt("ts", (day + timedelta(days=1)).isoformat())
            .in_("id", embedding_ids)
            .order("ts", desc=True)
            .limit(10)
            .execute
        )
        
        evidence_ids = {"tickets": [], "slack_messages": []}
        
        if today_embeddings_resp.data:
            # Get 3 most recent + 2 closest to centroid (simplified: just take 5 most recent)
            for embedding in today_embeddings_resp.data[:5]:
                if embedding["source"] == "ticket":
                    # For tickets, source_id is the zendesk_ticket_id, need to find database row ID
                    try:
                        ticket_resp = await asyncio.to_thread(
                            supabase.table("tickets")
                            .select("id")
                            .eq("zendesk_ticket_id", embedding["source_id"])
                            .execute
                        )
                        if ticket_resp.data:
                            for record in ticket_resp.data:
                                evidence_ids["tickets"].append(record["id"])
                    except Exception as e:
                        print(f"Error looking up ticket: {e}")
                elif embedding["source"] == "slack":
                    # For Slack, source_id is the slack timestamp, need to find database row ID
                    try:
                        slack_resp = await asyncio.to_thread(
                            supabase.table("slack_messages")
                            .select("id")
                            .eq("slack_message_id", embedding["source_id"])
                            .execute
                        )
                        if slack_resp.data:
                            for record in slack_resp.data:
                                evidence_ids["slack_messages"].append(record["id"])
                    except Exception as e:
                        print(f"Error looking up slack message: {e}")
        
        return evidence_ids
        
    except Exception as e:
        print(f"Error getting topic evidence: {e}")
        return {"tickets": [], "slack_messages": []}

async def generate_root_cause_hint(topic_id: str, account_id: str = DEFAULT_ACCOUNT_ID) -> str:
    """Generate root cause hint from topic data"""
    try:
        # Get embedding IDs for this topic first
        membership_resp = await asyncio.to_thread(
            supabase.table("topic_membership")
            .select("embedding_id")
            .eq("topic_id", topic_id)
            .eq("account_id", account_id)
            .execute
        )
        
        embedding_ids = [m["embedding_id"] for m in membership_resp.data] if membership_resp.data else []
        
        if not embedding_ids:
            return "Insufficient data for root cause analysis"
        
        # Get recent texts for this topic
        texts_resp = await asyncio.to_thread(
            supabase.table("embeddings_store")
            .select("one_line")
            .eq("account_id", account_id)
            .in_("id", embedding_ids)
            .order("ts", desc=True)
            .limit(20)
            .execute
        )
        
        if not texts_resp.data:
            return "Insufficient data for root cause analysis"
        
        texts = [item["one_line"] for item in texts_resp.data]
        
        # Extract common phrases
        phrase_counts = {}
        for text in texts:
            words = text.lower().split()
            # Look for 2-3 word phrases
            for i in range(len(words) - 1):
                phrase = " ".join(words[i:i+2])
                if len(phrase) > 5:  # Skip very short phrases
                    phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
            
            for i in range(len(words) - 2):
                phrase = " ".join(words[i:i+3])
                if len(phrase) > 8:
                    phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
        
        # Find most common meaningful phrase
        if phrase_counts:
            most_common_phrase, count = max(phrase_counts.items(), key=lambda x: x[1])
            percentage = (count / len(texts)) * 100
            
            if percentage >= 20:  # At least 20% mention it
                return f"{percentage:.0f}% mention '{most_common_phrase}'"
        
        return "Multiple issues reported - see evidence for details"
        
    except Exception as e:
        print(f"Error generating root cause hint: {e}")
        return "Unable to determine root cause"

# --- Topic Clustering Scheduler ---
async def topic_clustering_scheduler():
    """Background scheduler for topic clustering tasks"""
    await asyncio.sleep(30)  # Initial delay
    
    while True:
        try:
            # Acquire clustering lock
            got_lock = await acquire_lock("topic_clustering", ttl_sec=RECLUSTER_INTERVAL_SEC)
            if not got_lock:
                print("[topic_clustering] skipping (locked)")
            else:
                print("[topic_clustering] acquired lock")
                try:
                    # Detect trending topics and generate insights
                    trending_topics = await detect_trending_topics(DEFAULT_ACCOUNT_ID)
                    
                    if trending_topics:
                        print(f"[topic_clustering] found {len(trending_topics)} trending topics")
                        await generate_trend_insights(trending_topics)
                    
                except Exception as e:
                    print(f"[topic_clustering] error: {e}")
                finally:
                    await release_lock("topic_clustering")
                    print("[topic_clustering] released lock")
        
        except Exception as e:
            print(f"[topic_clustering] scheduler error: {e}")
        
        # Wait for next cycle
        await asyncio.sleep(RECLUSTER_INTERVAL_SEC)

async def generate_topic_name(topic_id: str, account_id: str = DEFAULT_ACCOUNT_ID) -> str:
    """Generate a meaningful name for a topic using LLM"""
    if not openai_client or not supabase:
        return "Unnamed Topic"
    
    try:
        # Get recent texts for this topic (last 20 messages)
        membership_resp = await asyncio.to_thread(
            supabase.table("topic_membership")
            .select("embedding_id")
            .eq("topic_id", topic_id)
            .eq("account_id", account_id)
            .execute
        )
        
        embedding_ids = [m["embedding_id"] for m in membership_resp.data] if membership_resp.data else []
        
        if not embedding_ids:
            return "Unnamed Topic"
        
        # Get recent texts
        texts_resp = await asyncio.to_thread(
            supabase.table("embeddings_store")
            .select("one_line")
            .eq("account_id", account_id)
            .in_("id", embedding_ids)
            .order("ts", desc=True)
            .limit(20)
            .execute
        )
        
        if not texts_resp.data:
            return "Unnamed Topic"
        
        texts = [item["one_line"] for item in texts_resp.data]
        sample_texts = texts[:10]  # Use first 10 for context
        
        # Get keywords for additional context
        topic_resp = await asyncio.to_thread(
            supabase.table("topics")
            .select("keywords")
            .eq("topic_id", topic_id)
            .eq("account_id", account_id)
            .single()
            .execute
        )
        
        keywords = topic_resp.data.get("keywords", []) if topic_resp.data else []
        
        # Create prompt for name generation
        prompt = f"""
You are a customer intelligence analyst. Based on the following customer messages and keywords, generate a clear, concise topic name that describes the main issue or theme.

Sample messages:
{chr(10).join(f"- {text}" for text in sample_texts)}

Keywords: {', '.join(keywords)}

Generate a topic name that:
1. Is 3-8 words maximum
2. Describes the core issue or theme
3. Uses clear, professional language
4. Avoids technical jargon unless necessary
5. Focuses on the customer's perspective

Examples of good topic names:
- "Checkout process broken"
- "Login authentication issues" 
- "Product page loading problems"
- "Payment processing errors"
- "Account access difficulties"

Return only the topic name, nothing else.
"""
        
        response = await openai_client.chat.completions.create(
            model=OPENAI_MODEL_DEFAULT,
            messages=[
                {"role": "system", "content": "You are a customer intelligence analyst. Generate concise, descriptive topic names."},
                {"role": "user", "content": prompt}
            ],
            **_model_specific_args(OPENAI_MODEL_DEFAULT, 100, temperature=0.3)
        )
        
        topic_name = response.choices[0].message.content.strip()
        
        # Clean up the name
        topic_name = topic_name.replace('"', '').replace("'", "").strip()
        if topic_name.lower().startswith("topic name:"):
            topic_name = topic_name[11:].strip()
        
        return topic_name[:100]  # Limit length
        
    except Exception as e:
        print(f"Error generating topic name: {e}")
        return "Unnamed Topic"

async def create_topic(embedding: List[float], canonical_text: str, account_id: str = DEFAULT_ACCOUNT_ID) -> Optional[str]:
    """Create a new topic with this embedding as the seed"""
    if not supabase or not embedding:
        return None
    
    try:
        # Extract initial keywords using simple tf-idf on the single text
        words = re.findall(r'\b\w+\b', canonical_text.lower())
        # Filter out common stopwords
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
        keywords = [w for w in words if len(w) > 2 and w not in stopwords][:10]
        
        response = await asyncio.to_thread(
            supabase.table("topics")
            .insert({
                "account_id": account_id,
                "centroid": embedding,
                "keywords": keywords,
                "cohesion": 1.0,  # Single point has perfect cohesion
                "doc_count_30d": 1,
                "state": "active"
            })
            .execute
        )
        
        if response.data:
            topic_id = response.data[0]["topic_id"]
            
            # Generate topic name asynchronously (don't block the main flow)
            asyncio.create_task(generate_and_update_topic_name(topic_id, account_id))
            
            return topic_id
        
    except Exception as e:
        print(f"Error creating topic: {e}")
        
    return None

rate_limit_stats = {
    "total_requests": 0,
    "rate_limit_hits": 0,
    "successful_retries": 0,
    "failed_after_retries": 0,
    "last_rate_limit_time": None
}

async def generate_topic_name_with_retry(topic_id: str, account_id: str = DEFAULT_ACCOUNT_ID, max_retries: int = 3) -> str:
    """Generate topic name with adaptive rate limiting and retry logic"""
    global rate_limit_stats, rate_limiter
    
    # Check if we should proceed
    if not rate_limiter.should_proceed():
        print(f"[topic] Rate limiter blocking request for topic {topic_id}")
        return "Unnamed Topic"
    
    base_delay = rate_limiter.get_delay()
    max_delay = 60.0
    
    for attempt in range(max_retries + 1):
        try:
            rate_limit_stats["total_requests"] += 1
            
            result = await generate_topic_name(topic_id, account_id)
            
            # Record success
            rate_limiter.record_success()
            return result
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if it's a rate limit error
            is_rate_limit = any(phrase in error_msg for phrase in [
                'rate limit', 'too many requests', '429', 'quota exceeded',
                'requests per minute', 'requests per day'
            ])
            
            if is_rate_limit:
                rate_limit_stats["rate_limit_hits"] += 1
                rate_limit_stats["last_rate_limit_time"] = datetime.now().isoformat()
                rate_limiter.record_rate_limit()
                
                if attempt < max_retries:
                    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                    print(f"[topic] Rate limit hit for topic {topic_id}, attempt {attempt + 1}/{max_retries + 1}, waiting {delay:.1f}s")
                    await asyncio.sleep(delay)
                    continue
                else:
                    rate_limit_stats["failed_after_retries"] += 1
                    print(f"[topic] Failed to generate name for topic {topic_id} after {attempt + 1} attempts: {e}")
                    return "Unnamed Topic"
            else:
                # Non-rate-limit error
                print(f"[topic] Non-rate-limit error for topic {topic_id}: {e}")
                return "Unnamed Topic"
    
    return "Unnamed Topic"

async def generate_and_update_topic_name(topic_id: str, account_id: str = DEFAULT_ACCOUNT_ID):
    """Generate and update topic name with retry logic"""
    try:
        topic_name = await generate_topic_name_with_retry(topic_id, account_id)
        
        if topic_name != "Unnamed Topic":
            await asyncio.to_thread(
                supabase.table("topics")
                .update({"name": topic_name})
                .eq("topic_id", topic_id)
                .eq("account_id", account_id)
                .execute
            )
            
            print(f"[topic] Generated name for topic {topic_id}: {topic_name}")
        else:
            print(f"[topic] Failed to generate meaningful name for topic {topic_id}")
            
    except Exception as e:
        print(f"Error updating topic name: {e}")

async def update_topic_centroid(topic_id: str, centroid: List[float], cohesion: float, keywords: List[str], doc_count: int):
    """Update topic centroid and metadata"""
    if not supabase:
        return
    
    try:
        # Get current topic data to check if we need to regenerate name
        current_topic_resp = await asyncio.to_thread(
            supabase.table("topics")
            .select("name, keywords, centroid")
            .eq("topic_id", topic_id)
            .eq("account_id", ACCOUNT_ID)
            .single()
            .execute
        )
        
        current_topic = current_topic_resp.data if current_topic_resp.data else {}
        current_keywords = set(current_topic.get("keywords", []))
        new_keywords = set(keywords)
        
        # Check if topic has changed significantly (keyword overlap < 50%)
        keyword_overlap = len(current_keywords & new_keywords) / len(current_keywords | new_keywords) if current_keywords else 0
        
        should_regenerate_name = (
            keyword_overlap < 0.5 or  # Significant keyword change
            not current_topic.get("name") or  # No name exists
            current_topic.get("name") == "Unnamed Topic"  # Generic name
        )
        
        update_data = {
            "centroid": centroid,
            "cohesion": cohesion,
            "keywords": keywords,
            "doc_count_30d": doc_count,
            "last_updated": datetime.now().isoformat()
        }
        
        # Update topic data
        await asyncio.to_thread(
            supabase.table("topics")
            .update(update_data)
            .eq("topic_id", topic_id)
            .eq("account_id", ACCOUNT_ID)
            .execute
        )
        
        # Regenerate name if needed
        if should_regenerate_name:
            asyncio.create_task(generate_and_update_topic_name(topic_id, ACCOUNT_ID))
            print(f"[topic] Topic {topic_id} changed significantly, regenerating name")
        
    except Exception as e:
        print(f"Error updating topic centroid: {e}")

async def backfill_topic_names():
    """Backfill names for existing topics with adaptive rate limiting"""
    if not supabase:
        return
    
    try:
        # Get topics without names
        topics_resp = await asyncio.to_thread(
            supabase.table("topics")
            .select("topic_id")
            .eq("account_id", ACCOUNT_ID)
            .eq("state", "active")
            .or_("name.is.null,name.eq.Unnamed Topic")
            .execute
        )
        
        if not topics_resp.data:
            print("[topic] No topics need name backfill")
            return
        
        print(f"[topic] Backfilling names for {len(topics_resp.data)} topics")
        
        # Process sequentially with adaptive rate limiting
        for i, topic in enumerate(topics_resp.data):
            topic_id = topic["topic_id"]
            
            # Check rate limiter before each request
            if not rate_limiter.should_proceed():
                print(f"[topic] Rate limiter blocking, pausing backfill at topic {i+1}/{len(topics_resp.data)}")
                await asyncio.sleep(60)  # Wait 1 minute
                continue
            
            # Generate name with retry logic
            await generate_and_update_topic_name(topic_id, ACCOUNT_ID)
            
            # Use adaptive delay
            delay = rate_limiter.get_delay()
            await asyncio.sleep(delay)
        
    except Exception as e:
        print(f"Error backfilling topic names: {e}")

async def run_topic_reclustering():
    """Pull last 30 days of embeddings and refine topic centroids"""
    if not supabase:
        print("[reclustering] Supabase not configured")
        return
    
    try:
        print("[reclustering] Starting topic reclustering...")
        
        # Pull last 30 days of embeddings for the account
        cutoff_date = (datetime.now() - timedelta(days=RECLUSTER_WINDOW_DAYS)).isoformat()
        
        embeddings_resp = await asyncio.to_thread(
            supabase.table("embeddings_store")
            .select("id, embedding, one_line")
            .eq("account_id", ACCOUNT_ID)
            .gte("ts", cutoff_date)
            .execute
        )
        
        if not embeddings_resp.data or len(embeddings_resp.data) < 10:
            print("[reclustering] Insufficient embeddings for reclustering")
            return
        
        embeddings = embeddings_resp.data
        print(f"[reclustering] Processing {len(embeddings)} embeddings")
        
        # Convert string embeddings back to vectors
        vectors = []
        valid_embeddings = []
        
        for emb in embeddings:
            try:
                # Parse vector string format
                vector = list(map(float, emb["embedding"].strip('[]').split(',')))
                if len(vector) == EMBEDDING_DIM:
                    vectors.append(vector)
                    valid_embeddings.append(emb)
            except Exception as e:
                print(f"[reclustering] Error parsing embedding {emb['id']}: {e}")
                continue
        
        if len(vectors) < 10:
            print("[reclustering] Insufficient valid vectors for clustering")
            return
        
        # Get existing topics for mapping
        existing_topics_resp = await asyncio.to_thread(
            supabase.table("topics")
            .select("topic_id, centroid, cohesion")
            .eq("account_id", ACCOUNT_ID)
            .eq("state", "active")
            .execute
        )
        
        existing_topics = existing_topics_resp.data or []
        print(f"[reclustering] Found {len(existing_topics)} existing topics")
        
        # Run mini-batch k-means to refine topic centroids
        # Estimate number of clusters based on data size and existing topics
        n_clusters = max(len(existing_topics), min(len(vectors) // 5, 20))
        n_clusters = max(n_clusters, 2)  # At least 2 clusters
        
        print(f"[reclustering] Running k-means with {n_clusters} clusters")
        
        kmeans = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, batch_size=100)
        cluster_labels = kmeans.fit_predict(vectors)
        centroids = kmeans.cluster_centers_.tolist()
        
        # Map clusters back to existing topics by finding nearest centroids
        cluster_to_topic_mapping = {}
        
        if existing_topics:
            # For each cluster, find the nearest existing topic centroid
            for i, cluster_centroid in enumerate(centroids):
                best_topic = None
                best_similarity = 0.0
                
                for topic in existing_topics:
                    try:
                        topic_centroid = list(map(float, topic["centroid"].strip('[]').split(',')))
                        similarity = np.dot(cluster_centroid, topic_centroid)
                        
                        if similarity > best_similarity:
                            best_similarity = similarity
                            best_topic = topic
                    except Exception as e:
                        print(f"[reclustering] Error processing topic {topic.get('topic_id')}: {e}")
                        continue
                
                # Only map if similarity is high enough (≥ 0.7)
                if best_similarity >= 0.7 and best_topic:
                    cluster_to_topic_mapping[i] = best_topic["topic_id"]
                    print(f"[reclustering] Mapped cluster {i} to topic {best_topic['topic_id']} (similarity: {best_similarity:.3f})")
                else:
                    print(f"[reclustering] Cluster {i} has no good match (best similarity: {best_similarity:.3f})")
        
        # Update topic centroids and cohesion scores
        updated_topics = 0
        for i, centroid in enumerate(centroids):
            # Find embeddings in this cluster
            cluster_embeddings = [emb for j, emb in enumerate(valid_embeddings) if cluster_labels[j] == i]
            
            if len(cluster_embeddings) < 3:
                continue  # Skip small clusters
            
            # Calculate cohesion (average similarity to centroid)
            similarities = []
            for emb in cluster_embeddings:
                try:
                    vector = list(map(float, emb["embedding"].strip('[]').split(',')))
                    similarity = np.dot(vector, centroid)
                    similarities.append(similarity)
                except:
                    continue
            
            cohesion = statistics.mean(similarities) if similarities else 0.0
            
            # Skip if cohesion is too low
            if cohesion < COHESION_FLOOR:
                print(f"[reclustering] Skipping cluster {i} - low cohesion: {cohesion:.3f}")
                continue
            
            # Extract keywords using tf-idf
            texts = [emb["one_line"] for emb in cluster_embeddings]
            keywords = extract_keywords_from_texts(texts)
            
            # Update existing topic or create new one
            topic_id = cluster_to_topic_mapping.get(i)
            if topic_id:
                # Update existing topic
                await update_topic_centroid(topic_id, centroid, cohesion, keywords, len(cluster_embeddings))
                updated_topics += 1
            else:
                # Create new topic for unmatched cluster
                new_topic_id = await create_new_topic_from_cluster(centroid, cohesion, keywords, len(cluster_embeddings))
                if new_topic_id:
                    updated_topics += 1
                    print(f"[reclustering] Created new topic {new_topic_id} for cluster {i}")
        
        print(f"[reclustering] Completed - updated {updated_topics} topics")
        
    except Exception as e:
        print(f"[reclustering] Error: {e}")

async def create_new_topic_from_cluster(centroid: List[float], cohesion: float, keywords: List[str], doc_count: int) -> Optional[str]:
    """Create a new topic for an unmatched cluster"""
    if not supabase:
        return None
    
    try:
        response = await asyncio.to_thread(
            supabase.table("topics")
            .insert({
                "account_id": ACCOUNT_ID,
                "centroid": centroid,
                "cohesion": cohesion,
                "keywords": keywords,
                "doc_count_30d": doc_count,
                "state": "active",
                "last_updated": datetime.now().isoformat()
            })
            .execute
        )
        
        if response.data:
            return response.data[0]["topic_id"]
        
    except Exception as e:
        print(f"Error creating new topic: {e}")
        
    return None

async def detect_and_emit_trends():
    """Detect trending topics and generate insights"""
    try:
        print("[trends] Starting trend detection...")
        
        # Call your existing detect_trending_topics()
        trending_topics = await detect_trending_topics(ACCOUNT_ID)
        
        if trending_topics:
            print(f"[trends] Found {len(trending_topics)} trending topics")
            
            # Call your existing generate_trend_insights()
            await generate_trend_insights(trending_topics)
        else:
            print("[trends] No trending topics detected")
            
    except Exception as e:
        print(f"[trends] Error: {e}")

# Helper functions
def extract_keywords_from_texts(texts: List[str], max_keywords: int = 10) -> List[str]:
    """Extract keywords using tf-idf"""
    if not texts:
        return []
    
    try:
        # Simple keyword extraction (you can enhance this)
        all_words = []
        for text in texts:
            words = re.findall(r'\b\w+\b', text.lower())
            # Filter out common stopwords
            stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
            words = [w for w in words if len(w) > 2 and w not in stopwords]
            all_words.extend(words)
        
        # Count word frequencies
        word_counts = {}
        for word in all_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Return most frequent words
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:max_keywords]]
        
    except Exception as e:
        print(f"Error extracting keywords: {e}")
        return []

async def update_topic_centroid(topic_id: str, centroid: List[float], cohesion: float, keywords: List[str], doc_count: int):
    """Update topic centroid and metadata"""
    if not supabase:
        return
    
    try:
        await asyncio.to_thread(
            supabase.table("topics")
            .update({
                "centroid": centroid,
                "cohesion": cohesion,
                "keywords": keywords,
                "doc_count_30d": doc_count,
                "last_updated": datetime.now().isoformat()
            })
            .eq("topic_id", topic_id)
            .eq("account_id", ACCOUNT_ID)
            .execute
        )
    except Exception as e:
        print(f"Error updating topic centroid: {e}")

async def generate_trend_insights(trending_topics: List[dict]):
    """Generate insights for trending topics using LLM"""
    if not trending_topics or not openai_client:
        return
    
    for topic in trending_topics:
        try:
            # Skip if topic already has recent insights
            print("Before calling existing insights check")
            existing_insights_resp = await asyncio.to_thread(
                supabase.table("insights")
                .select("id")
                .eq("type", "trend")
                .eq("data->>topic_id", str(topic["topic_id"]))  # Only check THIS topic
                .gte("created_at", (datetime.now() - timedelta(hours=12)).isoformat())  # 12-hour window per topic
                .execute
            )
            print("After calling existing insights check")
            
            if existing_insights_resp.data:
                continue  # Skip - already has recent insight

            print("After existing insights check")
            
            # Prepare context for LLM
            keywords_str = ", ".join(topic["keywords"][:5])
            
            # Build why_now message - handle both micro-batch and daily baseline formats
            detection_method = topic.get("detection_method", "daily_baseline")
            
            if detection_method == "micro_batch":
                # Micro-batch format
                count_in_window = topic.get("count_in_window", 0)
                messages_per_minute = topic.get("messages_per_minute", 0)
                window_duration = topic.get("window_duration_minutes", 1)
                why_now = f"Volume spike: {count_in_window} messages in {window_duration:.1f} minutes ({messages_per_minute:.1f} per minute)"
            else:
                # Daily baseline format
                if topic["volume_spike"]:
                    why_now = f"Volume spike: {topic['count_today']} messages today vs {topic['baseline_avg']:.1f} avg (z-score: {topic['z_score']:.1f})"
                else:
                    why_now = f"Sentiment drop: {topic['avg_sentiment_today']:.2f} today vs baseline (-{topic['sentiment_delta']:.2f})"
            
            print("Before LLM call")
            
            # Prepare LLM input
            llm_prompt = f"""
You are a customer success analyst for Catchalyze, a platform that detects emerging customer issues before they escalate. Analyze this trending customer issue and provide specific, actionable insights for support and customer success teams.

CONTEXT:
- Topic Keywords: {keywords_str}
- Trend: {why_now}
- Impact: {topic['impact']['customer_count']} customers affected ({topic['impact']['customer_percentage']}% of customer base)
- Root Cause: {topic['root_cause_hint']}

REQUIREMENTS:
- Focus on customer-facing solutions that prevent escalation
- Action steps should be executable by support/CS teams within 1 hour
- Be specific about communication, investigation, and resolution steps
- Prioritize customer retention and satisfaction

Provide JSON response with:
- name: Clear issue description for CS teams (≤60 chars)
- recommended_action: Primary action to prevent escalation (≤160 chars)
- playbook_steps: Array of 3 specific CS/support actions (each ≤120 chars)
- impact_summary: Customer retention risk and scope (≤100 chars)
- root_cause: Issue source and why customers are frustrated (≤150 chars)

Good action step examples:
- "Create help center article addressing common login error solutions"
- "Send proactive email to affected customers with workaround steps"
- "Update status page and notify customers of known issue resolution timeline"

Bad action step examples:
- "Monitor the situation"
- "Investigate further"
- "Escalate to development team"
"""
            print(f"[LLM] Calling OpenAI for topic: {keywords_str}")
            print(f"[LLM] Full prompt: {llm_prompt}")
            
            # Call LLM
            response = await openai_client.chat.completions.create(
                model=OPENAI_MODEL_INSIGHTS,
                messages=[
                    {"role": "system", "content": "You are a customer intelligence analyst. Provide concise, actionable insights in valid JSON format."},
                    {"role": "user", "content": llm_prompt}
                ],
                **_model_specific_args(OPENAI_MODEL_INSIGHTS, 800, temperature=None)
            )

            print(f"[DEBUG] OPENAI_MODEL_INSIGHTS: {OPENAI_MODEL_INSIGHTS}")
            print(f"[LLM] Response object: {response}")
            print(f"[LLM] Response choices: {response.choices}")
            print(f"[LLM] Response message: {response.choices[0].message}")
            
            llm_text = response.choices[0].message.content.strip()
            print(f"[LLM] Raw response: {llm_text}")

            cleaned_text = llm_text.replace('```json', '').replace('```', '').strip()
            print(f"[LLM] Cleaned response: {cleaned_text}")
            
            # Parse JSON response
            try:
                llm_data = json.loads(cleaned_text)
                print(f"[LLM] Parsed JSON successfully: {llm_data}")
            except json.JSONDecodeError as e:
                # Fallback if JSON parsing fails
                print(f"[LLM] JSON parsing failed: {e}")
                print(f"[LLM] Using fallback data")
                llm_data = {
                    "name": f"Topic Trend: {keywords_str[:40]}",
                    "recommended_action": "Investigate and address the trending topic",
                    "playbook_steps": ["Review customer messages", "Identify common issues", "Implement fixes"],
                    "impact_summary": f"Affects {topic['impact']['customer_count']} customers",
                    "root_cause": topic['root_cause_hint']
                }
            
            # Determine severity based on impact and trend strength
            if topic['impact']['customer_count'] > 50 or topic.get('z_score', 0) > 3:
                severity = "high"
            elif topic['impact']['customer_count'] > 20 or topic.get('z_score', 0) > 2.5:
                severity = "medium"
            else:
                severity = "low"
            
            # Create insight
            insight_data = {
                "type": "trend",
                "account_id": get_current_account_id(),
                "severity": severity,
                "title": llm_data.get("name", "Trending Topic")[:180],
                "description": llm_data.get("root_cause", why_now)[:600],
                "why_now": why_now[:300],
                "recommended_action": llm_data.get("recommended_action", "")[:200],
                "playbook_steps": (llm_data.get("playbook_steps", []))[:3],
                "confidence": 0.85,  # High confidence for trend-based insights
                "impact_score": min(100, max(0, int(topic['impact']['customer_count'] * 2))),
                "novelty_score": 80,  # Trending topics are novel by definition
                "affected_customers": topic['impact']['customer_count'],
                "data": {
                    "topic_id": topic["topic_id"],
                    "keywords": topic["keywords"],
                    "impact_metrics": topic["impact"],
                    "trend_data": {
                        "z_score": topic.get("z_score", 0),
                        "sentiment_delta": topic.get("sentiment_delta", 0),
                        "detection_method": detection_method
                    }
                }
            }
            
            # Add detection-specific fields to trend_data
            if detection_method == "micro_batch":
                insight_data["data"]["trend_data"].update({
                    "volume_today": topic.get("count_in_window", 0),
                    "baseline_avg": topic.get("messages_per_minute", 0),
                    "window_duration_minutes": topic.get("window_duration_minutes", 1)
                })
            else:
                insight_data["data"]["trend_data"].update({
                    "volume_today": topic.get("count_today", 0),
                    "baseline_avg": topic.get("baseline_avg", 0)
                })
            
            # Coerce and insert insight
            coerced_insight = coerce_insight_fields(insight_data)
            
            insight_resp = await asyncio.to_thread(
                supabase.table("insights")
                .insert(coerced_insight)
                .execute
            )
            
            if insight_resp.data:
                insight_id = insight_resp.data[0]["id"]
                
                # Create evidence links
                evidence_entries = []
                for ticket_id in topic["evidence_ids"]["tickets"]:
                    evidence_entries.append({
                        "insight_id": insight_id,
                        "ticket_id": ticket_id,
                        "evidence_snippet": "Trending topic evidence",
                        "evidence_sentiment": topic.get("avg_sentiment") or topic.get("avg_sentiment_today")
                    })
                
                for slack_id in topic["evidence_ids"]["slack_messages"]:
                    evidence_entries.append({
                        "insight_id": insight_id,
                        "slack_message_id": slack_id,
                        "evidence_snippet": "Trending topic evidence", 
                        "evidence_sentiment": topic.get("avg_sentiment") or topic.get("avg_sentiment_today")
                    })
                
                if evidence_entries:
                    await asyncio.to_thread(
                        supabase.table("insight_evidence")
                        .insert(evidence_entries)
                        .execute
                    )
                
                print(f"[topic_clustering] Created trend insight for topic {topic['topic_id']}")
            
        except Exception as e:
            print(f"Error generating insight for topic {topic.get('topic_id')}: {e}")

# MCP Tools
@mcp_server.tool(
    name="analyze_zendesk_tickets",
    description="Analyzes recent Zendesk tickets for sentiment and trends"
)
async def analyze_zendesk_tickets(days_back: int = 7, customer_id: str = None) -> Dict[str, Any]:
    """Analyzes Zendesk tickets for trends and sentiment"""
    # Security validation
    account_id = validate_account_context()

    # Input validation
    if not 1 <= days_back <= 365:
        raise ValueError("days_back must be between 1 and 365")
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    try:
        query_builder = supabase.table("tickets").select("*").eq("account_id", account_id)
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        query_builder = query_builder.gte("created_at", cutoff_date)
        if customer_id:
            query_builder = query_builder.eq("customer_id", customer_id)

        # Call .execute() inside asyncio.to_thread
        response = await asyncio.to_thread(query_builder.execute)
        tickets = response.data
        
        total_tickets = len(tickets)
        avg_sentiment = sum(float(t.get('sentiment_score', 0)) for t in tickets) / max(total_tickets, 1)
        
        status_counts = {}
        priority_counts = {}
        
        for ticket in tickets:
            status = ticket.get('status', 'unknown')
            priority = ticket.get('priority', 'normal')
            status_counts[status] = status_counts.get(status, 0) + 1
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        return {
            "total_tickets": total_tickets,
            "average_sentiment": round(avg_sentiment, 2),
            "status_breakdown": status_counts,
            "priority_breakdown": priority_counts,
            "time_range_days": days_back,
            "account_id": account_id[:8],
            "analyzed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing tickets for account {account_id[:8]}: {str(e)}")

@mcp_server.tool(
    name="analyze_slack_messages",
    description="Analyzes Slack messages for customer sentiment and mentions"
)
async def analyze_slack_messages(days_back: int = 7, channel_id: str = None) -> Dict[str, Any]:
    """Analyzes Slack messages for sentiment and engagement"""
    # Security validation
    account_id = validate_account_context()

    # Input validation
    if not 1 <= days_back <= 365:
        raise ValueError("days_back must be between 1 and 365")
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    try:
        query_builder = supabase.table("slack_messages").select("*").eq("account_id", account_id)
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        query_builder = query_builder.gte("created_at", cutoff_date)
        if channel_id:
            query_builder = query_builder.eq("slack_channel_id", channel_id)

        # Call .execute() inside asyncio.to_thread
        response = await asyncio.to_thread(query_builder.execute)
        messages = response.data
        
        total_messages = len(messages)
        avg_sentiment = sum(float(m.get('sentiment_score', 0)) for m in messages) / max(total_messages, 1)
        
        total_mentions = sum(len(m.get('mentions', [])) for m in messages)
        
        unique_users = len(set(m.get('user_id') for m in messages))
        
        return {
            "total_messages": total_messages,
            "average_sentiment": round(avg_sentiment, 2),
            "total_mentions": total_mentions,
            "unique_users": unique_users,
            "time_range_days": days_back,
            "account_id": account_id[:8],
            "analyzed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing messages for account {account_id[:8]}: {str(e)}")

@mcp_server.tool(
    name="generate_customer_insights",
    description="Generates grounded, structured insights with ranking and deduplication"
)
async def generate_customer_insights(
    time_range: str = "7d", 
    customer_id: str | None = None, 
    insight_type: str = "trend",
    llm_model: str | None = None,
) -> Dict[str, Any]:
    """Generates grounded AI-powered customer insights with evidence linking"""
    # Security validation
    account_id = validate_account_context()

    # Tool-specific rate limiting for expensive operations
    if await check_tool_rate_limit(account_id, "generate_customer_insights"):
        raise RuntimeError("Tool rate limit exceeded. Try again later.")

    # Input validation
    if time_range not in ["1h", "6h", "24h", "7d", "30d", "90d"]:
        raise ValueError(f"Invalid time_range: {time_range}")
    
    if insight_type not in ["trend", "churn_risk", "bug", "ux_friction", "feature_request", "process_gap"]:
        raise ValueError(f"Invalid insight_type: {insight_type}")
    
    # Constants for tuning
    MAX_ITEMS_PER_SOURCE = 300
    RECENT_DEDUPE_DAYS = 14
    MIN_CONFIDENCE = 0.6
    MIN_IMPACT = 50
    MIN_EVIDENCE = 2
    PROMPT_VERSION = "v2-2025-07-28"
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI client not configured")
    
    try:
        # A) Time-windowed, grounded input
        # account_id already validated above
        days_back = resolve_time_range(time_range)
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        # Fetch windowed tickets for this account
        tickets_query = supabase.table("tickets").select("*").eq("account_id", account_id).gte("created_at", cutoff_date).order("created_at", desc=True).limit(MAX_ITEMS_PER_SOURCE)
        if customer_id:
            tickets_query = tickets_query.eq("customer_id", customer_id)
        tickets_response = await asyncio.to_thread(tickets_query.execute)
        tickets = tickets_response.data or []
        
        # Fetch windowed slack messages for this account
        messages_query = supabase.table("slack_messages").select("*").eq("account_id", account_id).gte("created_at", cutoff_date).order("created_at", desc=True).limit(MAX_ITEMS_PER_SOURCE)
        if customer_id:
            messages_query = messages_query.eq("customer_id", customer_id)
        messages_response = await asyncio.to_thread(messages_query.execute)
        messages = messages_response.data or []
        
        # Sample per source BEFORE summaries
        tickets_sample = sample_by_recency_and_extremes(
            tickets, SAMPLE_NEWEST_PER_SOURCE, SAMPLE_EXTREMES_EACH
        )
        messages_sample = sample_by_recency_and_extremes(
            messages, SAMPLE_NEWEST_PER_SOURCE, SAMPLE_EXTREMES_EACH
        )

        # Enforce global cap by interleaving if needed
        total_after_sample = len(tickets_sample) + len(messages_sample)
        if total_after_sample > MAX_CONTEXT_ITEMS:
            tickets_sample, messages_sample = interleave_cap(tickets_sample, messages_sample, MAX_CONTEXT_ITEMS)
        
        # Ensure summaries exist for sampled sets only
        ticket_summaries = await ensure_ticket_summaries(tickets_sample)
        slack_summaries = await ensure_slack_summaries(messages_sample)
        
        # Build compact context and allowed ID lists
        context_items = []
        allowed_ticket_ids = set()
        allowed_slack_ids = set()
        
        for ticket in tickets_sample:
            ticket_id = ticket["id"]
            allowed_ticket_ids.add(ticket_id)
            context_items.append({
                "id": ticket_id,
                "source": "ticket",
                "one_line": ticket_summaries.get(ticket_id, "No summary"),
                "sentiment": ticket.get("sentiment_score", 0.0) or 0.0,
                "created_at": ticket.get("created_at", ""),
                "customer_id": ticket.get("customer_id")
            })
        
        for message in messages_sample:
            message_id = message["id"]
            allowed_slack_ids.add(message_id)
            context_items.append({
                "id": message_id,
                "source": "slack",
                "one_line": slack_summaries.get(message_id, "No summary"),
                "sentiment": message.get("sentiment_score", 0.0) or 0.0,
                "created_at": message.get("created_at", ""),
                "customer_id": message.get("customer_id")
            })
        
        if len(context_items) < MIN_EVIDENCE:
            return {"no_insight": True, "reason": "insufficient_data"}
        
        # B) Strict JSON output contract
        system_message = """Respond with JSON ONLY matching the schema. Use only evidence IDs provided in allowed_ticket_ids and allowed_slack_ids. Do not invent IDs. If nothing qualifies, return { "no_insight": true, "reason": "..." }."""
        
        schema_example = """{
  "no_insight": false,
  "insights": [
    {
      "type": "trend" | "churn_risk" | "bug" | "ux_friction" | "feature_request" | "process_gap",
      "title": "string",
      "severity": "low" | "medium" | "high" | "critical",
      "confidence": 0.0,
      "impact_score": 0,
      "novelty_score": 0,
      "recommended_action": "string (≤1 sentence)",
      "playbook_steps": ["≤3 short bullets"],
      "why_now": "1–2 sentences",
      "owner_hint": "CS" | "Support" | "PM" | "Eng" | "Sales",
      "time_cost_hint": "S" | "M" | "L",
      "evidence_ids": {
        "tickets": ["<ticket_id>", "..."],
        "slack_messages": ["<slack_message_id>", "..."]
      }
    }
  ]
}"""
        
        user_prompt = f"""Time window: {time_range} ({days_back} days)

Context items ({len(context_items)} total):
{json.dumps(context_items, indent=2)}

Allowed ticket IDs: {list(allowed_ticket_ids)}
Allowed slack message IDs: {list(allowed_slack_ids)}

Analyze this data and propose 2-5 insights maximum. Schema:
{schema_example}"""
        model_name = (llm_model or OPENAI_MODEL_INSIGHTS or "gpt-4o-mini")
        
        # Call LLM with JSON-only mode, with fallback
        try:
            response = await openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                **_model_specific_args(model_name, 900, temperature=0.3),
            )
        except Exception as e:
            # Fallback to GPT-4o-mini if GPT-5 fails
            if model_name.lower().startswith("gpt-5"):
                print(f"GPT-5 failed, falling back to GPT-4o-mini: {e}")
                model_name = "gpt-4o-mini"
                response = await openai_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    **_model_specific_args(model_name, 900, temperature=0.3),
                )
            else:
                raise
        
        # C) Parse, validate, threshold
        try:
            ai_result = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            # Retry once with fix formatting instruction
            fix_prompt = "Fix formatting only; same schema; do not invent IDs"
            retry_response = await openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": response.choices[0].message.content},
                    {"role": "user", "content": fix_prompt}
                ],
                response_format={"type": "json_object"},
                **_model_specific_args(model_name, 900, temperature=0.3),
            )
            try:
                ai_result = json.loads(retry_response.choices[0].message.content)
            except json.JSONDecodeError:
                return {"no_insight": True, "reason": "json_parse_error"}
        
        if ai_result.get("no_insight"):
            return ai_result
        
        # Validate insights
        valid_insights = []
        for insight in ai_result.get("insights", []):
            # Validate required fields and ranges
            confidence = float(insight.get("confidence", 0))
            impact_score = int(insight.get("impact_score", 0))
            novelty_score = int(insight.get("novelty_score", 0))
            playbook_steps = insight.get("playbook_steps", [])
            evidence_ids = insight.get("evidence_ids", {})
            
            # Validation checks
            if not (0 <= confidence <= 1):
                continue
            if not (0 <= impact_score <= 100):
                continue
            if not (0 <= novelty_score <= 100):
                continue
            if len(playbook_steps) > 3:
                continue
            
            # Validate evidence IDs
            ticket_ids = set(evidence_ids.get("tickets", []))
            slack_ids = set(evidence_ids.get("slack_messages", []))
            
            if not ticket_ids.issubset(allowed_ticket_ids):
                continue
            if not slack_ids.issubset(allowed_slack_ids):
                continue
            
            total_evidence = len(ticket_ids) + len(slack_ids)
            if total_evidence < MIN_EVIDENCE:
                continue
            
            # Quality gates
            if impact_score < MIN_IMPACT:
                continue
            if confidence < MIN_CONFIDENCE:
                continue
            
            insight["_validated_evidence"] = {"tickets": ticket_ids, "slack_messages": slack_ids}
            insight = coerce_insight_fields(insight)
            valid_insights.append(insight)
        
        if not valid_insights:
            return {"no_insight": True, "reason": "below_thresholds"}
        
        # D) Ranking & dedupe
        # Calculate priority and sort
        for insight in valid_insights:
            insight["_priority"] = priority_score(
                insight["impact_score"], 
                insight["confidence"], 
                insight["novelty_score"]
            )
        
        valid_insights.sort(key=lambda x: x["_priority"], reverse=True)
        valid_insights = valid_insights[:5]  # Keep top 5
        
        # Load recent insights for deduplication
        dedupe_cutoff = (datetime.now() - timedelta(days=RECENT_DEDUPE_DAYS)).isoformat()
        recent_insights_resp = await asyncio.to_thread(
            supabase.table("insights")
            .select("id,title,type,severity,confidence,impact_score,novelty_score,created_at")
            .eq("is_active", True)
            .gte("created_at", dedupe_cutoff)
            .execute
        )
        recent_insights = recent_insights_resp.data or []
        
        # Get evidence for recent insights
        recent_evidence = {}
        if recent_insights:
            evidence_resp = await asyncio.to_thread(
                supabase.table("insight_evidence")
                .select("insight_id, ticket_id, slack_message_id")
                .in_("insight_id", [i["id"] for i in recent_insights])
                .execute
            )
            for ev in (evidence_resp.data or []):
                insight_id = ev["insight_id"]
                if insight_id not in recent_evidence:
                    recent_evidence[insight_id] = {"tickets": set(), "slack_messages": set()}
                if ev.get("ticket_id"):
                    recent_evidence[insight_id]["tickets"].add(ev["ticket_id"])
                if ev.get("slack_message_id"):
                    recent_evidence[insight_id]["slack_messages"].add(ev["slack_message_id"])
        
        # Deduplicate
        final_insights = []
        updated_insights = []
        
        for insight in valid_insights:
            is_duplicate = False
            evidence_set = insight["_validated_evidence"]
            all_evidence = evidence_set["tickets"] | evidence_set["slack_messages"]
            
            for recent in recent_insights:
                recent_id = recent["id"]
                recent_evidence_set = recent_evidence.get(recent_id, {"tickets": set(), "slack_messages": set()})
                recent_all_evidence = recent_evidence_set["tickets"] | recent_evidence_set["slack_messages"]
                
                # Check title similarity
                title_sim = title_similarity(insight.get("title", ""), recent.get("title", ""))
                
                # Check evidence overlap
                evidence_overlap = jaccard_overlap(all_evidence, recent_all_evidence)
                
                if title_sim >= 0.7 or evidence_overlap >= 0.5:
                    # Update existing insight
                    is_duplicate = True
                    
                    # Add new evidence that isn't already linked
                    new_evidence_rows = []
                    for ticket_id in evidence_set["tickets"]:
                        if ticket_id not in recent_evidence_set["tickets"]:
                            ticket_summary = ticket_summaries.get(ticket_id, "")[:200]
                            ticket_data = next((t for t in tickets if t["id"] == ticket_id), {})
                            new_evidence_rows.append({
                                "insight_id": recent_id,
                                "ticket_id": ticket_id,
                                "evidence_snippet": ticket_summary,
                                "evidence_sentiment": ticket_data.get("sentiment_score", 0.0)
                            })
                    
                    for slack_id in evidence_set["slack_messages"]:
                        if slack_id not in recent_evidence_set["slack_messages"]:
                            slack_summary = slack_summaries.get(slack_id, "")[:200]
                            slack_data = next((m for m in messages if m["id"] == slack_id), {})
                            new_evidence_rows.append({
                                "insight_id": recent_id,
                                "slack_message_id": slack_id,
                                "evidence_snippet": slack_summary,
                                "evidence_sentiment": slack_data.get("sentiment_score", 0.0)
                            })
                    
                    if new_evidence_rows:
                        await asyncio.to_thread(
                            supabase.table("insight_evidence").insert(new_evidence_rows).execute
                        )
                    
                    # Optionally bump scores  
                    base_impact = _clamp_int(recent.get("impact_score", 0), 0, 100, 0)
                    base_novel = _clamp_int(recent.get("novelty_score", 0), 0, 100, 0)
                    new_impact = min(100, base_impact + 5)
                    new_novelty = min(100, base_novel + 5)
                    
                    await asyncio.to_thread(
                        supabase.table("insights")
                        .update({
                            "impact_score": new_impact,
                            "novelty_score": new_novelty
                        })
                        .eq("id", recent_id)
                        .execute
                    )
                    
                    updated_insights.append({
                        "id": recent_id,
                        "title": recent.get("title", ""),
                        "type": recent.get("type", ""),
                        "severity": recent.get("severity", ""),
                        "confidence": recent.get("confidence", 0),
                        "impact_score": new_impact,
                        "novelty_score": new_novelty,
                        "priority": priority_score(new_impact, recent.get("confidence", 0), new_novelty),
                        "evidence_counts": {
                            "tickets": len(recent_evidence_set["tickets"]) + len([e for e in new_evidence_rows if e.get("ticket_id")]),
                            "slack_messages": len(recent_evidence_set["slack_messages"]) + len([e for e in new_evidence_rows if e.get("slack_message_id")])
                        },
                        "updated": True,
                        "created_at": recent.get("created_at", ""),
                        "updated_at": datetime.now().isoformat()
                    })
                    break
            
            if not is_duplicate:
                final_insights.append(insight)
        
        # E) Persist + return
        persisted_insights = []
        
        for insight in final_insights:
            insight = coerce_insight_fields(insight)
            evidence_set = insight["_validated_evidence"]
            
            # Insert insight
            insight_data = {
                "type": insight.get("type", "trend"),
                "account_id": get_current_account_id(),
                "title": insight.get("title", ""),
                "description": insight.get("description", ""),
                "severity": insight.get("severity", "medium"),
                "confidence": insight.get("confidence", 0.7),
                "impact_score": insight.get("impact_score", 50),
                "novelty_score": insight.get("novelty_score", 50),
                "recommended_action": insight.get("recommended_action", ""),
                "playbook_steps": insight.get("playbook_steps", []),
                "why_now": insight.get("why_now", ""),
                "owner_hint": insight.get("owner_hint", "CS"),
                "time_cost_hint": insight.get("time_cost_hint", "M"),
                "prompt_version": PROMPT_VERSION,
                "is_active": True,
                "data": {
                    "time_range": time_range,
                    "customer_id": customer_id,
                    "evidence_counts": {
                        "tickets": len(evidence_set["tickets"]),
                        "slack_messages": len(evidence_set["slack_messages"])
                    }
                }
            }
            
            insert_resp = await asyncio.to_thread(
                supabase.table("insights").insert(insight_data).execute
            )
            
            if insert_resp.data:
                insight_id = insert_resp.data[0]["id"]
                created_at = insert_resp.data[0]["created_at"]
                
                # Insert evidence
                evidence_rows = []
                for ticket_id in evidence_set["tickets"]:
                    ticket_summary = ticket_summaries.get(ticket_id, "")[:200]
                    ticket_data = next((t for t in tickets if t["id"] == ticket_id), {})
                    evidence_rows.append({
                        "insight_id": insight_id,
                        "ticket_id": ticket_id,
                        "evidence_snippet": ticket_summary,
                        "evidence_sentiment": ticket_data.get("sentiment_score", 0.0)
                    })
                
                for slack_id in evidence_set["slack_messages"]:
                    slack_summary = slack_summaries.get(slack_id, "")[:200]
                    slack_data = next((m for m in messages if m["id"] == slack_id), {})
                    evidence_rows.append({
                        "insight_id": insight_id,
                        "slack_message_id": slack_id,
                        "evidence_snippet": slack_summary,
                        "evidence_sentiment": slack_data.get("sentiment_score", 0.0)
                    })
                
                if evidence_rows:
                    await asyncio.to_thread(
                        supabase.table("insight_evidence").insert(evidence_rows).execute
                    )
                
                persisted_insights.append({
                    "id": insight_id,
                    "title": insight.get("title", ""),
                    "type": insight.get("type", ""),
                    "severity": insight.get("severity", ""),
                    "confidence": insight.get("confidence", 0),
                    "impact_score": insight.get("impact_score", 0),
                    "novelty_score": insight.get("novelty_score", 0),
                    "priority": insight.get("_priority", 0),
                    "evidence_counts": {
                        "tickets": len(evidence_set["tickets"]),
                        "slack_messages": len(evidence_set["slack_messages"])
                    },
                    "created_at": created_at,
                    "updated_at": created_at
                })
        
        result = {
            "no_insight": False,
            "insights": persisted_insights
        }
        
        if updated_insights:
            result["updated_insights"] = updated_insights
        
        if not persisted_insights and not updated_insights:
            return {"no_insight": True, "reason": "no_persisted_after_filters"}
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating insights: {str(e)}")

@mcp_server.tool(
    name="update_customer_health",
    description="Updates customer health scores based on recent interactions"
)
async def update_customer_health(customer_id: str, health_score: Optional[int] = None) -> Dict[str, Any]:
    """Updates customer health score"""
    # Security validation
    account_id = validate_account_context()

    # Input validation
    if not customer_id or len(customer_id.strip()) == 0:
        raise ValueError("customer_id is required and cannot be empty")
    
    if health_score is not None and not 0 <= health_score <= 100:
        raise ValueError("health_score must be between 0 and 100")
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    try:
        if not customer_id:
            raise JSONRPCError(code=-32602, message="Invalid params: Missing required parameter 'customer_id'")

        if health_score is None:
            # Call .execute() inside asyncio.to_thread
            tickets_response = await asyncio.to_thread(
                supabase.table("tickets").select("sentiment_score").eq("customer_id", customer_id).eq("account_id", account_id).limit(10).execute
            )
            # Call .execute() inside asyncio.to_thread
            messages_response = await asyncio.to_thread(
                supabase.table("slack_messages").select("sentiment_score").eq("customer_id", customer_id).eq("account_id", account_id).limit(10).execute
            )
            
            tickets = tickets_response.data
            messages = messages_response.data
            
            all_sentiments = []
            all_sentiments.extend([float(t.get('sentiment_score', 0)) for t in tickets if t.get('sentiment_score') is not None])
            all_sentiments.extend([float(m.get('sentiment_score', 0)) for m in messages if m.get('sentiment_score') is not None])
            
            if all_sentiments:
                avg_sentiment = sum(all_sentiments) / len(all_sentiments)
                health_score = max(0, min(100, int((avg_sentiment + 1) * 50)))
            else:
                health_score = 50
        
        # Call .execute() inside asyncio.to_thread
        update_response = await asyncio.to_thread(
            supabase.table("customers").update({
                "health_score": health_score,
                "last_interaction": datetime.now().isoformat()
            }).eq("id", customer_id).execute
        )
        
        return {
            "customer_updated": True,
            "customer_id": customer_id,
            "account_id": account_id,
            "new_health_score": health_score,
            "updated_at": datetime.now().isoformat()
        }
        
    except JSONRPCError:
        raise
    except Exception as e:
        raise JSONRPCError(code=-32603, message=f"Internal server error updating customer health: {str(e)}")

@mcp_server.tool(
    name="get_dashboard_data",
    description="Retrieves compiled dashboard metrics and insights"
)
async def get_dashboard_data(time_range: str = "7d") -> Dict[str, Any]:
    """Retrieves dashboard data for the UI (overview + lists + charts)."""
    # Security validation
    account_id = validate_account_context()

    # Input validation
    if time_range not in ["1h", "6h", "24h", "7d", "30d", "90d"]:
        raise ValueError(f"Invalid time_range: {time_range}")
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        # ---- time window ----
        tr = (time_range or "7d").lower()
        if tr == "24h":
            days_back = 1
        elif tr == "30d":
            days_back = 30
        elif tr == "90d":
            days_back = 90
        else:
            days_back = 7

        now = datetime.now()
        cutoff_dt = now - timedelta(days=days_back)
        cutoff_iso = cutoff_dt.isoformat()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

        # helper: safe ISO parse -> date key 'YYYY-MM-DD'
        def date_key(iso_str: Optional[str]) -> Optional[str]:
            if not iso_str:
                return None
            try:
                dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
                return dt.date().isoformat()
            except Exception:
                return None

        # ---- customers (account-scoped) ----
        customers_resp = await asyncio.to_thread(
            supabase.table("customers")
            .select("id,name,email,health_score,churn_risk,last_interaction")
            .eq("account_id", account_id)
            .execute
        )
        customers_all = customers_resp.data or []
        total_customers = len(customers_all)
        avg_health_score = (
            sum((c.get("health_score") or 50) for c in customers_all) / max(total_customers, 1)
        )
        high_risk_customers = sum(
            1 for c in customers_all if (c.get("churn_risk") or "").lower() == "high"
        )

        def sort_key_c(c):
            li = c.get("last_interaction")
            try:
                ts = datetime.fromisoformat(li) if li else None
            except Exception:
                ts = None
            return (0 if ts else 1, -(ts.timestamp() if ts else 0), -(c.get("health_score") or 0))

        customers_top10 = sorted(customers_all, key=sort_key_c)[:10]

        # ---- tickets (time-windowed, account-scoped) ----
        tickets_resp = await asyncio.to_thread(
            supabase.table("tickets")
            .select("id,zendesk_ticket_id,subject,status,priority,sentiment_score,created_at,customer_id")
            .eq("account_id", account_id)
            .gte("created_at", cutoff_iso)
            .order("created_at", desc=True)
            .limit(2000)
            .execute
        )
        tickets = tickets_resp.data or []
        recent_tickets = tickets[:10]

        # today's ticket count (account-scoped)
        tickets_today_resp = await asyncio.to_thread(
            supabase.table("tickets").select("id").eq("account_id", account_id).gte("created_at", today_start).execute
        )
        todays_tickets = len(tickets_today_resp.data or [])

        # ---- slack messages (time-windowed, account-scoped) ----
        slack_resp = await asyncio.to_thread(
            supabase.table("slack_messages")
            .select("id,text,user_id,sentiment_score,created_at,slack_channel_id")
            .eq("account_id", account_id)
            .gte("created_at", cutoff_iso)
            .order("created_at", desc=True)
            .limit(2000)
            .execute
        )
        slack_messages = slack_resp.data or []
        recent_slack_messages = slack_messages[:10]

        # ---- insights (critical count) ----
        insights_resp = await asyncio.to_thread(
            supabase.table("insights")
            .select("id,severity,is_active")
            .eq("account_id", account_id)
            .eq("is_active", True)
            .limit(200)
            .execute
        )
        insights = insights_resp.data or []
        critical_insights = sum(
            1 for i in insights if (i.get("severity") or "").lower() in ("high", "critical")
        )

        # ---- aggregates for charts ----
        # ticket_status_breakdown
        status_counts: Dict[str, int] = {}
        def normalize_status(s: Optional[str]) -> str:
            s = (s or "").strip().lower()
            if s in ("new", "open"): return "open"
            if s in ("pending", "hold", "on-hold", "on hold"): return "pending"
            if s in ("resolved", "solved"): return "solved"
            if s == "closed": return "closed"
            return "open"
        for t in tickets:
            st = normalize_status(t.get("status"))
            status_counts[st] = status_counts.get(st, 0) + 1
        ticket_status_breakdown = [{"status": k, "count": v} for k, v in status_counts.items()]
        ticket_status_breakdown.sort(key=lambda x: x["status"])

        # build day buckets for trend/volume
        days = [(cutoff_dt + timedelta(days=i)).date().isoformat() for i in range(days_back + 1)]
        sentiments_by_day: Dict[str, list] = {d: [] for d in days}
        msg_count_by_day: Dict[str, int] = {d: 0 for d in days}

        for t in tickets:
            dk = date_key(t.get("created_at"))
            if dk in sentiments_by_day and t.get("sentiment_score") is not None:
                try:
                    sentiments_by_day[dk].append(float(t["sentiment_score"]))
                except Exception:
                    pass

        for m in slack_messages:
            dk = date_key(m.get("created_at"))
            if dk in msg_count_by_day:
                msg_count_by_day[dk] += 1
            if dk in sentiments_by_day and m.get("sentiment_score") is not None:
                try:
                    sentiments_by_day[dk].append(float(m["sentiment_score"]))
                except Exception:
                    pass

        sentiment_trend = [
            {
                "date": d,
                "sentiment": round(
                    (sum(vals) / len(vals)) if vals else 0.0, 3
                ),
            }
            for d, vals in sentiments_by_day.items()
        ]
        message_volume = [{"date": d, "messages": msg_count_by_day[d]} for d in days]

        # overall avg sentiment (window)
        all_sents = [s for _, vals in sentiments_by_day.items() for s in vals]
        avg_sentiment = (sum(all_sents) / len(all_sents)) if all_sents else 0.0

        return {
            "overview": {
                "total_customers": total_customers,
                "average_health_score": round(avg_health_score, 1),
                "high_risk_customers": high_risk_customers,
                "critical_insights": critical_insights,
                "todays_tickets": todays_tickets,
                "average_sentiment": round(avg_sentiment, 3),  # 0..1; UI multiplies by 100
            },
            "customers": customers_top10,
            "recent_tickets": recent_tickets,
            "recent_slack_messages": recent_slack_messages,
            "ticket_status_breakdown": ticket_status_breakdown,
            "sentiment_trend": sentiment_trend,
            "message_volume": message_volume,
            "time_range": tr,
            "generated_at": now.isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting dashboard data: {str(e)}")

@mcp_server.tool(
    name="process_zendesk_webhook",
    description="Processes incoming Zendesk webhook data"
)
async def process_zendesk_webhook(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Processes Zendesk webhook data"""
    # Security validation
    account_id = validate_account_context()

    # Input validation
    if not webhook_data or not isinstance(webhook_data, dict):
        raise ValueError("webhook_data must be a valid dictionary")
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        if not webhook_data:
            raise JSONRPCError(code=-32602, message="Invalid params: Missing required parameter 'webhook_data'")

        ticket = webhook_data.get("ticket", {}) or {}
        if not ticket:
            return {"status": "ignored", "reason": "No ticket data in webhook"}

        zendesk_ticket_id = str(ticket.get("id", ""))

        subject = (ticket.get("title") or ticket.get("subject") or "").strip()
        description = (
            ticket.get("latest_public_comment") or
            ticket.get("verbatim_description") or
            ticket.get("description") or
            ""
        ).strip()

        zendesk_status = (ticket.get("status") or "open").lower()
        status_mapping = {
            "new": "open",
            "open": "open",
            "pending": "pending",
            "hold": "pending",
            "solved": "solved",
            "closed": "closed",
        }
        status = status_mapping.get(zendesk_status, "open")
        priority = (ticket.get("priority") or "normal").lower()

        requester = ticket.get("requester") or {}
        requester_id = str(requester.get("id") or ticket.get("requester_id") or "")

        sentiment_score = calculate_sentiment_score(f"{subject} {description}".strip())

        customer_data = {
            "zendesk_id": requester_id,
            "name": (requester.get("name") or f"Customer {requester_id}"),
            "email": requester.get("email") or "",
        }
        customer_response = await asyncio.to_thread(
            supabase.table("customers").upsert(customer_data, on_conflict="zendesk_id").execute
        )
        customer_id = customer_response.data[0]["id"] if customer_response.data else None

        now_iso = datetime.now().isoformat()

        ticket_insert_data = {
            "account_id": account_id,
            "zendesk_ticket_id": zendesk_ticket_id,
            "customer_id": customer_id,
            "subject": subject,
            "description": description,  # clean body
            "status": status,
            "priority": priority,
            "sentiment_score": sentiment_score,
            # optional fields if you want parity with the HTTP handler:
            # "tags": ticket.get("tags") or [],
            "created_at": ticket.get("created_at") or ticket.get("created_at_with_time") or now_iso,
            "updated_at": ticket.get("updated_at") or ticket.get("updated_at_with_time") or now_iso,
        }
        ticket_response = await asyncio.to_thread(
            supabase.table("tickets").upsert(ticket_insert_data, on_conflict="zendesk_ticket_id").execute
        )

        # Process for topic clustering (best effort, don't fail webhook)
        ticket_id = ticket_response.data[0]["id"] if ticket_response.data else None
        try:
            if ticket_id:
                await process_content_for_topics(
                    source="ticket",
                    source_id=ticket_id,
                    data={"subject": subject, "description": description, "customer_id": customer_id},
                    customer_id=customer_id,
                    account_id=account_id
                )
        except Exception as e:
            print(f"[topic processing] failed for ticket {ticket_id}: {e}")

        return {
            "status": "processed",
            "account_id": account_id,
            "ticket_id": ticket_id,
            "customer_id": customer_id,
            "sentiment_score": sentiment_score,
        }

    except JSONRPCError:
        raise
    except Exception as e:
        raise JSONRPCError(code=-32603, message=f"Internal server error processing Zendesk webhook: {str(e)}")

@mcp_server.tool(
    name="process_slack_webhook",
    description="Processes incoming Slack webhook data"
)
async def process_slack_webhook(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Processes Slack webhook data"""
    # Security validation
    account_id = validate_account_context()

    # Input validation
    if not webhook_data or not isinstance(webhook_data, dict):
        raise ValueError("webhook_data must be a valid dictionary")
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    try:
        if not webhook_data:
            raise JSONRPCError(code=-32602, message="Invalid params: Missing required parameter 'webhook_data'")

        if webhook_data.get('type') == 'url_verification':
            return {"challenge": webhook_data.get('challenge')}
        
        event = webhook_data.get('event', {})
        if not event or event.get('type') != 'message':
            return {"status": "ignored", "reason": "Not a message event"}
        
        channel_id = event.get('channel', '')
        message_id = event.get('ts', '')
        user_id = event.get('user', '')
        text = event.get('text', '')
        thread_ts = event.get('thread_ts', '')
        
        if not all([channel_id, message_id, user_id, text]):
            return {"status": "ignored", "reason": "Missing required message data in event"}
        
        sentiment_score = calculate_sentiment_score(text)
        
        mentions = []
        if 'mentions' in text or '@' in text:
            import re
            mentions = re.findall(r'<@([^>]+)>', text)
        
        ts = float(message_id)
        created_at = datetime.fromtimestamp(ts).isoformat()
        
        message_data = {
            "account_id": account_id,
            "slack_channel_id": channel_id,
            "slack_message_id": message_id,
            "thread_ts": thread_ts,
            "user_id": user_id,
            "text": text,
            "sentiment_score": sentiment_score,
            "mentions": mentions,
            "created_at": created_at,
        }
        
        message_response = await asyncio.to_thread(
            supabase.table("slack_messages").upsert(
                message_data,
                on_conflict="slack_channel_id,slack_message_id"
            ).execute
        )
        
        # Process for topic clustering (best effort, don't fail webhook)
        message_id = message_response.data[0]["id"] if message_response.data else None
        try:
            if message_id:
                await process_content_for_topics(
                    source="slack",
                    source_id=message_id,
                    data={"text": text, "user_id": user_id},
                    channel_id=channel_id,
                    account_id=account_id
                )
        except Exception as e:
            print(f"[topic processing] failed for slack message {message_id}: {e}")
        
        return {
            "status": "processed",
            "account_id": account_id,
            "message_id": message_id,
            "sentiment_score": sentiment_score,
            "mentions_count": len(mentions)
        }
        
    except JSONRPCError:
        raise
    except Exception as e:
        raise JSONRPCError(code=-32603, message=f"Internal server error processing Slack webhook: {str(e)}")

async def get_rate_limit_analytics(hours: int = 24) -> Dict[str, Any]:
    """Get rate limit analytics for monitoring"""
    if not supabase:
        return {}
    
    try:
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        events_resp = await asyncio.to_thread(
            supabase.table("rate_limit_events")
            .select("*")
            .eq("account_id", get_current_account_id())
            .gte("timestamp", cutoff)
            .order("timestamp", desc=True)
            .execute
        )
        
        events = events_resp.data or []
        
        if not events:
            return {
                "total_events": 0,
                "success_rate": 100.0,
                "rate_limit_hit_rate": 0.0,
                "current_rate_per_minute": rate_limiter.requests_per_minute,
                "alerts": []
            }
        
        total_events = len(events)
        successful_events = len([e for e in events if e["success"]])
        rate_limit_events = len([e for e in events if e["error_type"] == "rate_limit_exhausted"])
        
        success_rate = (successful_events / total_events) * 100
        rate_limit_hit_rate = (rate_limit_events / total_events) * 100
        
        # Generate alerts
        alerts = []
        
        if success_rate < 80:
            alerts.append({
                "type": "low_success_rate",
                "severity": "high" if success_rate < 60 else "medium",
                "message": f"Success rate is {success_rate:.1f}% (below 80% threshold)"
            })
        
        if rate_limit_hit_rate > 20:
            alerts.append({
                "type": "high_rate_limit_hits",
                "severity": "high" if rate_limit_hit_rate > 40 else "medium",
                "message": f"Rate limit hit rate is {rate_limit_hit_rate:.1f}% (above 20% threshold)"
            })
        
        return {
            "total_events": total_events,
            "success_rate": round(success_rate, 1),
            "rate_limit_hit_rate": round(rate_limit_hit_rate, 1),
            "current_rate_per_minute": rate_limiter.requests_per_minute,
            "alerts": alerts,
            "time_window_hours": hours
        }
        
    except Exception as e:
        print(f"Error getting rate limit analytics: {e}")
        return {}

@mcp_server.tool(
    name="detect_trending_topics",
    description="Detects topics trending in volume or sentiment with graceful rate limiting"
)
async def detect_trending_topics_tool(
    time_window_minutes: int = 1440,
    start_time_iso: str = None,
    end_time_iso: str = None
) -> Dict[str, Any]:
    """Tool wrapper with graceful rate limiting and caching"""
    account_id = validate_account_context()
    
    # Create cache key based on params
    if start_time_iso and end_time_iso:
        cache_key = f"{account_id}:trends:{start_time_iso}:{end_time_iso}"
    else:
        # Round to nearest 30 seconds for micro-batching
        now_rounded = (int(time.time()) // 30) * 30
        cache_key = f"{account_id}:trends:{time_window_minutes}:{now_rounded}"
    
    # Check rate limit with cache fallback
    is_limited, cached_data = await check_tool_rate_limit_with_cache(
        account_id, 
        "detect_trending_topics", 
        cache_key,
        max_requests=20,  # Increased from 5
        window_seconds=60
    )
    
    if is_limited:
        if cached_data:
            # Return stale data with rate limit info
            result = dict(cached_data)
            result.update({
                "rate_limited": True,
                "retry_after_seconds": 30,
                "stale": True,
                "as_of": datetime.fromtimestamp(trending_cache[cache_key]["timestamp"]).isoformat()
            })
            return result
        else:
            # No cache available - return empty with backoff
            return {
                "trending_topics": [],
                "rate_limited": True,
                "retry_after_seconds": 45,
                "message": "Rate limited - no cached data available"
            }
    
    # Input validation
    if time_window_minutes < 1 or time_window_minutes > 10080:  # 1 minute to 1 week
        raise ValueError("time_window_minutes must be between 1 and 10080 (1 week)")
    
    try:
        # Parse datetime parameters if provided
        parsed_start = None
        parsed_end = None
        if start_time_iso:
            parsed_start = datetime.fromisoformat(start_time_iso.replace('Z', '+00:00'))
        if end_time_iso:
            parsed_end = datetime.fromisoformat(end_time_iso.replace('Z', '+00:00'))
        
        # Call the core function
        trending_topics = await detect_trending_topics(
            account_id=account_id,
            time_window_minutes=time_window_minutes,
            start_time=parsed_start,
            end_time=parsed_end,
            broadcast=False  # Don't broadcast from tool calls
        )
        
        result = {
            "trending_topics": trending_topics,
            "rate_limited": False,
            "as_of": datetime.now().isoformat(),
            "detection_method": "granular" if parsed_start and parsed_end else "windowed",
            "time_window_minutes": time_window_minutes
        }
        
        # Cache the successful result
        cache_trending_result(cache_key, result)
        
        return result
        
    except Exception as e:
        raise RuntimeError(f"Error detecting trending topics: {str(e)}")

@mcp_server.tool(
    name="run_evaluation_harness",
    description="Runs comprehensive evaluation tests for trend detection quality"
)
async def run_evaluation_harness() -> Dict[str, Any]:
    """Run evaluation harness to test trend detection quality"""
    # Security validation
    account_id = validate_account_context()

    # Tool-specific rate limiting for expensive operations
    if await check_tool_rate_limit(account_id, "run_evaluation_harness"):
        raise RuntimeError("Tool rate limit exceeded. Try again later.")
    try:
        report = await run_evaluation_test()
        return {
            "status": "completed",
            "report": report,
            "quality_score": report["quality_score"],
            "recommendation": get_quality_recommendation(report["quality_score"])
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "quality_score": 0,
            "recommendation": "Fix errors before deployment"
        }

@mcp_server.tool(
    name="get_evidence_details",
    description="Get evidence details for trending topics by IDs"
)
async def get_evidence_details(evidence_ids: dict) -> Dict[str, Any]:
    """Fetch evidence details for tickets and slack messages by ID"""
    # Security validation
    account_id = validate_account_context()

    # Input validation
    if not evidence_ids or not isinstance(evidence_ids, dict):
        raise ValueError("evidence_ids must be a valid dictionary")
    
    # Validate structure
    for key in evidence_ids.keys():
        if key not in ["tickets", "slack_messages"]:
            raise ValueError("evidence_ids can only contain 'tickets' and 'slack_messages' keys")
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    evidence = {"tickets": [], "slack_messages": []}
    
    try:
        # Fetch ticket details
        if evidence_ids.get("tickets"):
            ticket_ids = []
            for ticket_id in evidence_ids["tickets"]:
                # Check if it's a UUID or zendesk_ticket_id
                try:
                    import uuid
                    uuid.UUID(ticket_id)  # Try to parse as UUID
                    ticket_ids.append(ticket_id)
                except (ValueError, TypeError):
                    # If not UUID, assume it's zendesk_ticket_id, look up the database ID
                    ticket_resp = await asyncio.to_thread(
                        supabase.table("tickets")
                        .select("id")
                        .eq("zendesk_ticket_id", ticket_id)
                        .eq("account_id", account_id)
                        .execute
                    )
                    if ticket_resp.data:
                        ticket_ids.extend([record["id"] for record in ticket_resp.data])
            
            if ticket_ids:
                tickets_resp = await asyncio.to_thread(
                    supabase.table("tickets")
                    .select("id, zendesk_ticket_id, subject, created_at")
                    .in_("id", ticket_ids)
                    .eq("account_id", account_id)
                    .execute
                )
                evidence["tickets"] = tickets_resp.data or []
        
        # Fetch slack message details
        if evidence_ids.get("slack_messages"):
            slack_ids = []
            for slack_id in evidence_ids["slack_messages"]:
                # Check if it's a UUID or slack_message_id timestamp
                try:
                    import uuid
                    uuid.UUID(slack_id)  # Try to parse as UUID
                    slack_ids.append(slack_id)
                except (ValueError, TypeError):
                    # If not UUID, assume it's slack_message_id timestamp, look up the database ID
                    slack_resp = await asyncio.to_thread(
                        supabase.table("slack_messages")
                        .select("id")
                        .eq("slack_message_id", slack_id)
                        .eq("account_id", account_id)
                        .execute
                    )
                    if slack_resp.data:
                        slack_ids.extend([record["id"] for record in slack_resp.data])
            
            if slack_ids:
                messages_resp = await asyncio.to_thread(
                    supabase.table("slack_messages")
                    .select("id, slack_message_id, slack_channel_id, text, created_at, user_id, thread_ts")
                    .in_("id", slack_ids)
                    .eq("account_id", account_id)
                    .execute
                )
                evidence["slack_messages"] = messages_resp.data or []
        
        return evidence
        
    except Exception as e:
        print(f"Error fetching evidence details: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching evidence: {str(e)}")

@mcp_server.tool(
    name="get_historical_trends",
    description="Get historical trends from active_trends table for past time period"
)
async def get_historical_trends(time_window_minutes: int = 10080) -> Dict[str, Any]:
    """Get historical trends from active_trends table without triggering new detection"""
    account_id = validate_account_context()
    
    try:
        # Calculate time window
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=time_window_minutes)
        
        # Query active_trends table directly for historical data
        trends_resp = await asyncio.to_thread(
            supabase.table("active_trends")
            .select("*")
            .eq("account_id", account_id)
            .gte("created_at", start_time.isoformat())
            .lte("created_at", end_time.isoformat())
            .order("created_at", desc=True)
            .execute
        )
        
        if not trends_resp.data:
            return {"trends": []}
        
        # Transform to match expected format
        trends = []
        for trend in trends_resp.data:
            # Get topic details
            topic_resp = await asyncio.to_thread(
                supabase.table("topics")
                .select("name, keywords")
                .eq("topic_id", trend["topic_id"])
                .eq("account_id", account_id)
                .single()
                .execute
            )
            
            topic_data = topic_resp.data if topic_resp.data else {}
            
            # Get insights if available
            insights_resp = await asyncio.to_thread(
                supabase.table("insights")
                .select("*")
                .eq("account_id", account_id)
                .eq("type", "trend")
                .eq("data->>topic_id", str(trend["topic_id"]))
                .execute
            )
            
            # Get evidence IDs from the trend data
            trend_data_json = trend.get("trend_data", {})
            evidence_ids = trend_data_json.get("evidence_ids", {"tickets": [], "slack_messages": []})
            
            # Inline evidence fetching
            evidence = {"tickets": [], "slack_messages": []}
            
            try:
                # Fetch ticket details
                if evidence_ids.get("tickets"):
                    ticket_ids = []
                    for ticket_id in evidence_ids["tickets"]:
                        # Check if it's a UUID or zendesk_ticket_id
                        try:
                            import uuid
                            uuid.UUID(ticket_id)  # Try to parse as UUID
                            ticket_ids.append(ticket_id)
                        except (ValueError, TypeError):
                            # If not UUID, assume it's zendesk_ticket_id, look up the database ID
                            ticket_resp = await asyncio.to_thread(
                                supabase.table("tickets")
                                .select("id")
                                .eq("zendesk_ticket_id", ticket_id)
                                .eq("account_id", account_id)
                                .execute
                            )
                            if ticket_resp.data:
                                ticket_ids.extend([record["id"] for record in ticket_resp.data])
                    
                    if ticket_ids:
                        tickets_resp = await asyncio.to_thread(
                            supabase.table("tickets")
                            .select("id, zendesk_ticket_id, subject, created_at")
                            .in_("id", ticket_ids)
                            .eq("account_id", account_id)
                            .execute
                        )
                        evidence["tickets"] = tickets_resp.data or []
                
                # Fetch slack message details
                if evidence_ids.get("slack_messages"):
                    slack_ids = []
                    for slack_id in evidence_ids["slack_messages"]:
                        # Check if it's a UUID or slack_message_id timestamp
                        try:
                            import uuid
                            uuid.UUID(slack_id)  # Try to parse as UUID
                            slack_ids.append(slack_id)
                        except (ValueError, TypeError):
                            # If not UUID, assume it's slack_message_id timestamp, look up the database ID
                            slack_resp = await asyncio.to_thread(
                                supabase.table("slack_messages")
                                .select("id")
                                .eq("slack_message_id", slack_id)
                                .eq("account_id", account_id)
                                .execute
                            )
                            if slack_resp.data:
                                slack_ids.extend([record["id"] for record in slack_resp.data])
                    
                    if slack_ids:
                        messages_resp = await asyncio.to_thread(
                            supabase.table("slack_messages")
                            .select("id, slack_message_id, slack_channel_id, text, created_at, user_id, thread_ts")
                            .in_("id", slack_ids)
                            .eq("account_id", account_id)
                            .execute
                        )
                        evidence["slack_messages"] = messages_resp.data or []

            except Exception as e:
                print(f"Error fetching evidence details in historical trends: {e}")
                # Continue with empty evidence rather than failing completely
            
            trend_data = {
                "topic_id": trend["topic_id"],
                "title": topic_data.get("name", "Unknown Topic"),
                "keywords": topic_data.get("keywords", []),
                "trend_type": trend.get("trend_type", "volume_spike"),
                "detected_at": trend["created_at"],
                "is_active": trend.get("is_active", False),
                "count_in_window": trend_data_json.get("count_in_window", 0),
                "avg_sentiment": trend_data_json.get("avg_sentiment", 0.0),
                "window_duration": trend_data_json.get("window_duration", "unknown"),
                "insights": insights_resp.data[0] if insights_resp.data else None,
                "evidence_ids": evidence_ids,
                "evidence": evidence
            }
            trends.append(trend_data)
        
        return {"trends": trends}
        
    except Exception as e:
        print(f"Error fetching historical trends: {e}")
        return {"trends": [], "error": str(e)}

@mcp_server.tool(
    name="regenerate_topic_names",
    description="Regenerate names for topics that don't have meaningful names"
)
async def regenerate_topic_names() -> Dict[str, Any]:
    """Regenerate names for topics without meaningful names"""
    # Security validation
    account_id = validate_account_context()

    # Tool-specific rate limiting for expensive operations
    if await check_tool_rate_limit(account_id, "regenerate_topic_names"):
        raise RuntimeError("Tool rate limit exceeded. Try again later.")
    try:
        await backfill_topic_names()
        return {
            "status": "started",
            "message": "Topic name regeneration started in background"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@mcp_server.tool(
    name="get_rate_limit_stats",
    description="Get statistics about OpenAI rate limit usage"
)
async def get_rate_limit_stats() -> Dict[str, Any]:
    """Get rate limit statistics for monitoring"""
    # Security validation
    account_id = validate_account_context()
    return {
        "rate_limit_stats": rate_limit_stats,
        "timestamp": datetime.now().isoformat(),
        "recommendations": get_rate_limit_recommendations()
    }

def get_rate_limit_recommendations() -> List[str]:
    """Get recommendations based on rate limit stats"""
    recommendations = []
    
    if rate_limit_stats["rate_limit_hits"] > 0:
        hit_rate = rate_limit_stats["rate_limit_hits"] / rate_limit_stats["total_requests"]
        
        if hit_rate > 0.1:  # More than 10% rate limit hits
            recommendations.append("High rate limit hit rate - consider reducing request frequency")
        elif hit_rate > 0.05:  # More than 5% rate limit hits
            recommendations.append("Moderate rate limit hits - monitor closely")
        else:
            recommendations.append("Rate limit handling working well")
    
    if rate_limit_stats["failed_after_retries"] > 0:
        recommendations.append(f"{rate_limit_stats['failed_after_retries']} requests failed after retries")
    
    return recommendations

@mcp_server.tool(
    name="get_rate_limit_analytics",
    description="Get rate limit analytics and current rate limiter state"
)
async def get_rate_limit_analytics_tool(hours: int = 24) -> Dict[str, Any]:
    """Get rate limit analytics for monitoring"""
    # Security validation
    account_id = validate_account_context()

    # Tool-specific rate limiting for expensive operations
    if await check_tool_rate_limit(account_id, "get_rate_limit_analytics"):
        raise RuntimeError("Tool rate limit exceeded. Try again later.")

    # Input validation
    if not 1 <= hours <= 168:  # 1 hour to 1 week
        raise ValueError("hours must be between 1 and 168")
    analytics = await get_rate_limit_analytics(hours)
    
    return {
        "analytics": analytics,
        "rate_limiter_state": {
            "requests_per_minute": rate_limiter.requests_per_minute,
            "consecutive_successes": rate_limiter.consecutive_successes,
            "consecutive_failures": rate_limiter.consecutive_failures,
            "last_rate_limit": rate_limiter.last_rate_limit.isoformat() if rate_limiter.last_rate_limit else None
        },
        "current_stats": rate_limit_stats,
        "timestamp": datetime.now().isoformat()
    }

def get_quality_recommendation(score: float) -> str:
    """Get recommendation based on quality score"""
    if score >= 90:
        return "Excellent quality - ready for production"
    elif score >= 75:
        return "Good quality - minor improvements recommended"
    elif score >= 60:
        return "Acceptable quality - improvements needed"
    else:
        return "Poor quality - significant improvements required"

@mcp_server.tool(
    name="get_active_trends_with_insights",
    description="Get active trends that have AI insights generated"
)
async def get_active_trends_with_insights() -> Dict[str, Any]:
    """Get only trends that have been processed and have AI insights"""
    account_id = validate_account_context()
    
    try:
        # Get active trends that have corresponding insights
        twenty_four_hours_ago = (datetime.now() - timedelta(hours=24)).isoformat()
        active_trends_resp = await asyncio.to_thread(
            supabase.table("active_trends")
            .select("*")
            .eq("account_id", account_id)
            .gte("created_at", twenty_four_hours_ago)
            .execute
        )
        
        if not active_trends_resp.data:
            return {"trends": []}
        
        trends_with_insights = []
        
        for trend in active_trends_resp.data:
            # Check if this trend has AI insights
            insights_resp = await asyncio.to_thread(
                supabase.table("insights")
                .select("*")
                .eq("account_id", account_id)
                .eq("type", "trend")
                .eq("data->>topic_id", str(trend["topic_id"]))
                .eq("is_active", True)
                .execute
            )
            
            if insights_resp.data:
                # Get topic details
                topic_resp = await asyncio.to_thread(
                    supabase.table("topics")
                    .select("name, keywords")
                    .eq("topic_id", trend["topic_id"])
                    .eq("account_id", account_id)
                    .single()
                    .execute
                )
                
                topic_data = topic_resp.data if topic_resp.data else {}
                insight_data = insights_resp.data[0]
                
                # Format trend with insights
                trend_with_insight = {
                    "topic_id": trend["topic_id"],
                    "title": topic_data.get("name") or insight_data.get("title", "Trend"),
                    "keywords": topic_data.get("keywords", []),
                    "created_at": trend["created_at"],
                    "window_start": trend.get("window_start"),
                    "count_in_window": trend.get("trend_data", {}).get("count_in_window", 0),
                    "avg_sentiment": trend.get("trend_data", {}).get("avg_sentiment", 0), 
                    "evidence_ids": trend.get("trend_data", {}).get("evidence_ids", {}),
                    "recommended_action": insight_data.get("recommended_action"),
                    "playbook_steps": insight_data.get("playbook_steps", []),
                    "affected_customers": insight_data.get("affected_customers"),
                    "customer_percentage": insight_data.get("data", {}).get("impact_metrics", {}).get("customer_percentage"),
                    "root_cause_hint": insight_data.get("description")
                }
                
                trends_with_insights.append(trend_with_insight)
        
        return {
            "trends": trends_with_insights,
            "count": len(trends_with_insights)
        }
        
    except Exception as e:
        print(f"Error getting active trends with insights: {e}")
        return {"trends": [], "error": str(e)}

# -- Evaluation Harness --

# Add these functions to your main.py

async def run_evaluation_test():
    """Run a comprehensive evaluation test"""
    print("[EVAL] Starting evaluation test...")
    
    results = {
        "micro_batch_latency": [],
        "trend_detection_success": [],
        "insight_generation_success": [],
        "false_positive_rate": [],
        "test_scenarios": []
    }
    
    # Test Scenario 1: Volume Spike Detection
    print("[EVAL] Testing volume spike detection...")
    await test_volume_spike_detection(results)
    
    # Test Scenario 2: Sentiment Drop Detection  
    print("[EVAL] Testing sentiment drop detection...")
    await test_sentiment_drop_detection(results)
    
    # Test Scenario 3: False Positive Check
    print("[EVAL] Testing false positive rate...")
    await test_false_positive_rate(results)
    
    # Generate evaluation report
    report = generate_evaluation_report(results)
    print(f"[EVAL] Evaluation complete: {report}")
    
    return report

async def test_volume_spike_detection(results: dict):
    """Test if system detects volume spikes correctly"""
    try:
        # Send 5 messages about the same topic in 1 minute
        test_messages = [
            "Login page is completely broken",
            "Cannot access my account at all", 
            "Login system down again",
            "Still can't log in to the platform",
            "Login issues persisting for hours"
        ]
        
        start_time = datetime.now()
        
        # Send messages
        for i, message in enumerate(test_messages):
            await send_test_slack_message(message)
            await asyncio.sleep(2)  # 2 seconds between messages
        
        # Wait for micro-batch to process
        await asyncio.sleep(15)
        
        # Check for trends
        trends = await detect_trending_topics(ACCOUNT_ID, time_window_minutes=2)
        
        latency = (datetime.now() - start_time).total_seconds()
        results["micro_batch_latency"].append(latency)
        
        # Check if trend was detected
        trend_detected = len(trends) > 0
        results["trend_detection_success"].append(trend_detected)
        
        if trend_detected:
            print(f"[EVAL] ✅ Volume spike detected in {latency:.1f}s")
            results["test_scenarios"].append({
                "scenario": "volume_spike",
                "status": "PASS",
                "latency": latency,
                "trends_found": len(trends)
            })
        else:
            print(f"[EVAL] ❌ Volume spike NOT detected in {latency:.1f}s")
            results["test_scenarios"].append({
                "scenario": "volume_spike", 
                "status": "FAIL",
                "latency": latency,
                "trends_found": 0
            })
            
    except Exception as e:
        print(f"[EVAL] Error in volume spike test: {e}")
        results["test_scenarios"].append({
            "scenario": "volume_spike",
            "status": "ERROR",
            "error": str(e)
        })

async def test_sentiment_drop_detection(results: dict):
    """Test if system detects sentiment drops correctly"""
    try:
        # Send negative messages
        negative_messages = [
            "This service is absolutely terrible",
            "Worst customer experience ever",
            "Completely disappointed with this product",
            "Never using this again",
            "Terrible support and terrible product"
        ]
        
        start_time = datetime.now()
        
        for message in negative_messages:
            await send_test_slack_message(message)
            await asyncio.sleep(2)
        
        await asyncio.sleep(15)
        
        # CHANGE THIS LINE: Remove time_window_minutes to test daily baseline
        trends = await detect_trending_topics(ACCOUNT_ID)  # ← No time window = daily baseline
        
        # Check for sentiment-based trends
        sentiment_trends = [t for t in trends if t.get("sentiment_drop")]
        
        if sentiment_trends:
            print(f"[EVAL] ✅ Sentiment drop detected")
            results["test_scenarios"].append({
                "scenario": "sentiment_drop",
                "status": "PASS", 
                "trends_found": len(sentiment_trends)
            })
        else:
            print(f"[EVAL] ❌ Sentiment drop NOT detected")
            results["test_scenarios"].append({
                "scenario": "sentiment_drop",
                "status": "FAIL",
                "trends_found": 0
            })
            
    except Exception as e:
        print(f"[EVAL] Error in sentiment test: {e}")
        results["test_scenarios"].append({
            "scenario": "sentiment_drop",
            "status": "ERROR",
            "error": str(e)
        })

async def test_false_positive_rate(results: dict):
    """Test false positive rate with normal messages"""
    try:
        # Send normal, non-trending messages (these should be positive sentiment)
        normal_messages = [
            "Thanks for the help",
            "Working fine now",
            "Appreciate the support",
            "Everything looks good",
            "No issues here"
        ]
        
        for message in normal_messages:
            await send_test_slack_message(message)
            await asyncio.sleep(2)
        
        await asyncio.sleep(15)
        
        # Use micro-batch detection (should filter out positive sentiment)
        trends = await detect_trending_topics(ACCOUNT_ID, time_window_minutes=2)
        
        # Should NOT detect trends from normal messages (due to sentiment filtering)
        false_positives = len(trends)
        results["false_positive_rate"].append(false_positives)
        
        if false_positives == 0:
            print(f"[EVAL] ✅ No false positives detected")
            results["test_scenarios"].append({
                "scenario": "false_positive",
                "status": "PASS",
                "false_positives": 0
            })
        else:
            print(f"[EVAL] ⚠️ {false_positives} false positives detected")
            results["test_scenarios"].append({
                "scenario": "false_positive",
                "status": "WARNING",
                "false_positives": false_positives
            })
            
    except Exception as e:
        print(f"[EVAL] Error in false positive test: {e}")
        results["test_scenarios"].append({
            "scenario": "false_positive",
            "status": "ERROR",
            "error": str(e)
        })

async def get_topic_evidence_ids_granular_with_retry(topic_id: str, start_time: datetime, end_time: datetime, account_id: str = DEFAULT_ACCOUNT_ID, max_retries: int = 3) -> dict:
    """Get evidence IDs with retry logic for network issues"""
    for attempt in range(max_retries):
        try:
            return await get_topic_evidence_ids_granular(topic_id, start_time, end_time, account_id)
        except Exception as e:
            if "Server disconnected" in str(e) and attempt < max_retries - 1:
                print(f"[retry] Network error on attempt {attempt + 1}, retrying...")
                await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                continue
            else:
                print(f"[error] Failed to get evidence after {max_retries} attempts: {e}")
                return {"tickets": [], "slack_messages": []}

async def send_test_slack_message(text: str):
    """Send a test Slack message for evaluation"""
    try:
        # Create test message data
        message_data = {
            "slack_channel_id": "test_channel",
            "slack_message_id": f"test_{int(time.time() * 1000)}",
            "user_id": "test_user",
            "text": text,
            "sentiment_score": calculate_sentiment_score(text),
            "mentions": [],
            "created_at": datetime.now().isoformat()
        }
        
        # Insert into database
        await asyncio.to_thread(
            supabase.table("slack_messages").upsert(
                message_data,
                on_conflict="slack_channel_id,slack_message_id"
            ).execute
        )
        
        # Process for topics
        if supabase.table("slack_messages").select("id").eq("slack_message_id", message_data["slack_message_id"]).execute().data:
            message_id = supabase.table("slack_messages").select("id").eq("slack_message_id", message_data["slack_message_id"]).execute().data[0]["id"]
            await process_content_for_topics(
                source="slack",
                source_id=message_id,
                data={"text": text},
                channel_id="test_channel",
                account_id=DEFAULT_ACCOUNT_ID
            )
            
    except Exception as e:
        print(f"[EVAL] Error sending test message: {e}")

def generate_evaluation_report(results: dict) -> dict:
    """Generate evaluation report from test results"""
    total_scenarios = len(results["test_scenarios"])
    passed_scenarios = len([s for s in results["test_scenarios"] if s["status"] == "PASS"])
    failed_scenarios = len([s for s in results["test_scenarios"] if s["status"] == "FAIL"])
    error_scenarios = len([s for s in results["test_scenarios"] if s["status"] == "ERROR"])
    
    avg_latency = statistics.mean(results["micro_batch_latency"]) if results["micro_batch_latency"] else 0
    success_rate = len([s for s in results["trend_detection_success"] if s]) / len(results["trend_detection_success"]) if results["trend_detection_success"] else 0
    false_positive_rate = len([f for f in results["false_positive_rate"] if f > 0]) / len(results["false_positive_rate"]) if results["false_positive_rate"] else 0
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_scenarios": total_scenarios,
            "passed": passed_scenarios,
            "failed": failed_scenarios,
            "errors": error_scenarios,
            "success_rate": f"{success_rate * 100:.1f}%",
            "avg_latency_seconds": f"{avg_latency:.1f}",
            "false_positive_rate": f"{false_positive_rate * 100:.1f}%"
        },
        "scenarios": results["test_scenarios"],
        "quality_score": calculate_quality_score(results)
    }
    
    return report

def calculate_quality_score(results: dict) -> float:
    """Calculate overall quality score (0-100)"""
    if not results["test_scenarios"]:
        return 0.0
    
    # Weight different factors
    scenario_score = len([s for s in results["test_scenarios"] if s["status"] == "PASS"]) / len(results["test_scenarios"]) * 50
    
    latency_score = 0
    if results["micro_batch_latency"]:
        avg_latency = statistics.mean(results["micro_batch_latency"])
        # Score based on latency (lower is better)
        if avg_latency < 20:  # Under 20 seconds
            latency_score = 25
        elif avg_latency < 30:  # Under 30 seconds  
            latency_score = 20
        elif avg_latency < 45:  # Under 45 seconds
            latency_score = 15
        else:
            latency_score = 10
    
    false_positive_score = 0
    if results["false_positive_rate"]:
        false_positive_rate = len([f for f in results["false_positive_rate"] if f > 0]) / len(results["false_positive_rate"])
        # Score based on false positive rate (lower is better)
        if false_positive_rate == 0:
            false_positive_score = 25
        elif false_positive_rate < 0.2:  # Less than 20%
            false_positive_score = 20
        elif false_positive_rate < 0.4:  # Less than 40%
            false_positive_score = 15
        else:
            false_positive_score = 10
    
    return scenario_score + latency_score + false_positive_score
# --- Slack OAuth Endpoints ---

error_count = 0

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    global error_count
    error_count += 1
    logger.error(f"Error #{error_count}: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.get("/slack/oauth/start")
async def slack_oauth_start():
    """Redirect user to Slack OAuth consent screen with nonce cookie."""
    if not SLACK_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Slack client ID not configured")

    # CSRF nonce
    nonce = secrets.token_urlsafe(32)
    state = json.dumps({"nonce": nonce})

    redirect_uri = quote_plus(f"{PUBLIC_BASE_URL}/slack/oauth/callback")
    scopes_param = quote_plus(SLACK_SCOPES)
    state_param = quote_plus(state)

    slack_auth_url = (
        f"https://slack.com/oauth/v2/authorize"
        f"?client_id={SLACK_CLIENT_ID}"
        f"&scope={scopes_param}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state_param}"
    )

    # Set the cookie on *this* RedirectResponse
    resp = RedirectResponse(url=slack_auth_url)
    resp.set_cookie(
        key="slack_oauth_nonce",
        value=nonce,
        max_age=300,              # 5 minutes
        httponly=True,
        secure=_cookie_secure(),  # True when PUBLIC_BASE_URL is https (ngrok)
        samesite=_cookie_samesite(),
    )
    return resp

@app.get("/slack/oauth/callback")
async def slack_oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    if error:
        return RedirectResponse(url=f"{FRONTEND_URL}/?oauth=slack&ok=0&error={quote_plus(error)}")
    if not code:
        return RedirectResponse(url=f"{FRONTEND_URL}/?oauth=slack&ok=0&error={quote_plus('missing_code')}")
    if not state:
        return RedirectResponse(url=f"{FRONTEND_URL}/?oauth=slack&ok=0&error={quote_plus('missing_state')}")

    # Validate state/nonce
    try:
        state_data = json.loads(state)
        expected_nonce = state_data.get("nonce")
        stored_nonce = request.cookies.get("slack_oauth_nonce")
        if not expected_nonce or not stored_nonce or expected_nonce != stored_nonce:
            return RedirectResponse(url=f"{FRONTEND_URL}/?oauth=slack&ok=0&error={quote_plus('invalid_state')}")
    except (json.JSONDecodeError, KeyError):
        return RedirectResponse(url=f"{FRONTEND_URL}/?oauth=slack&ok=0&error={quote_plus('invalid_state')}")

    try:
        token_response = await exchange_oauth_code(code)
        if not token_response.get("ok"):
            return RedirectResponse(
                url=f"{FRONTEND_URL}/?oauth=slack&ok=0&error={quote_plus(token_response.get('error','token_exchange_failed'))}"
            )

        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in")
        team_info = token_response.get("team", {})
        workspace_id = team_info.get("id")

        if not workspace_id or not access_token:
            return RedirectResponse(url=f"{FRONTEND_URL}/?oauth=slack&ok=0&error={quote_plus('invalid_token_response')}")

        expires_at = _iso(datetime.now() + timedelta(seconds=expires_in)) if expires_in else None

        await asyncio.to_thread(
            supabase.table("slack_oauth_tokens").upsert({
                "workspace_id": workspace_id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
            }, on_conflict="workspace_id").execute
        )

        existing_resp = await asyncio.to_thread(
            supabase.table("slack_account_mapping")
            .select("account_id")
            .eq("workspace_id", workspace_id)
            .execute
        )

        if existing_resp.data:
            return RedirectResponse(
                url=f"{FRONTEND_URL}/?oauth=slack&ok=0&error=workspace_already_connected"
            )

        # Store account mapping for multi-tenant support
        account_id = get_account_id_from_request(request)
        try:
            await asyncio.to_thread(
                supabase.table("slack_account_mapping").upsert({
                    "account_id": account_id,
                    "workspace_id": workspace_id,
                    "team_name": team_info.get("name", "")
                }, on_conflict="workspace_id").execute
            )
        except Exception as e:
            print(f"Warning: Failed to store Slack account mapping: {e}")

        asyncio.create_task(sync_workspace_history(workspace_id))

        team_name = team_info.get("name", "")
        resp = RedirectResponse(
        url=f"{FRONTEND_URL}/?oauth=slack&ok=1&team={quote_plus(team_name)}&wsid={quote_plus(workspace_id)}"
        )
        resp.delete_cookie("slack_oauth_nonce", samesite=_cookie_samesite(), secure=_cookie_secure())
        return resp

    except Exception as e:
        print(f"OAuth callback error: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/?oauth=slack&ok=0&error={quote_plus(str(e))}")

@app.api_route("/slack/events", methods=["GET", "POST"])
async def slack_events(request: Request):
    """Handle Slack Events API webhooks"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        body = await request.body()

        timestamp = request.headers.get("x-slack-request-timestamp")
        signature = request.headers.get("x-slack-signature")
        
        if not timestamp or not signature:
            raise HTTPException(status_code=401, detail="Missing Slack headers")
            
        if not verify_slack_signature(body, timestamp, signature):
            raise HTTPException(status_code=401, detail="Invalid Slack signature")
        
        try:
            data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON body")

        # Handle URL verification challenge
        if data.get("type") == "url_verification":
            return {"challenge": data.get("challenge")}

        # Extract team_id for account lookup
        team_id = data.get("team_id")
        if not team_id:
            raise HTTPException(status_code=400, detail="No team_id in webhook data")
        
        # Look up account for this workspace
        account_id = await get_account_for_workspace(team_id)

        # Handle message events
        event = data.get("event", {})
        
        if event.get("type") == "message" and not event.get("subtype"):
            
            channel_id = event.get("channel", "")
            message_id = event.get("ts", "")
            user_id = event.get("user", "")
            text = event.get("text", "")
            thread_ts = event.get("thread_ts", "")

            if all([channel_id, message_id, user_id, text]):
                
                sentiment_score = calculate_sentiment_score(text)

                mentions = []
                if "@" in text:
                    import re
                    mentions = re.findall(r'<@([^>]+)>', text)

                ts = float(message_id)
                created_at = datetime.fromtimestamp(ts).isoformat()

                message_data = {
                    "account_id": account_id,
                    "slack_channel_id": channel_id,
                    "slack_message_id": message_id,
                    "thread_ts": thread_ts,
                    "user_id": user_id,
                    "text": text,
                    "sentiment_score": sentiment_score,
                    "mentions": mentions,
                    "created_at": created_at
                }

                try:
                    message_response = await asyncio.to_thread(
                        supabase.table("slack_messages").upsert(
                            message_data, 
                            on_conflict="slack_channel_id,slack_message_id"
                        ).execute
                    )
                    
                    if message_response.data:

                        await broadcast_to_account_clients(account_id, {
                            "type": "new_message",
                            "text": text,
                            "user_id": user_id,
                            "channel_id": channel_id,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        # Now try topic processing
                        try:
                            await process_content_for_topics(
                                source="slack",
                                source_id=message_id,
                                data={"text": text, "user_id": user_id},
                                channel_id=channel_id,
                                account_id=account_id
                            )
                        except Exception as topic_error:
                            import traceback
                            traceback.print_exc()
                    else:
                        print("[DEBUG] No data returned from database insert")
                        
                except Exception as db_error:
                    print(f"[DEBUG] Database insert failed: {db_error}")
                    import traceback
                    traceback.print_exc()

                return {
                    "status": "processed",
                    "sentiment_score": sentiment_score,
                    "mentions_count": len(mentions)
                }
            else:
                print(f"[DEBUG] Missing required fields - channel: {bool(channel_id)}, user: {bool(user_id)}, text: {bool(text)}, ts: {bool(message_id)}")
                return {"status": "ignored", "reason": "Missing required message data"}
        else:
            print(f"[DEBUG] Ignoring event type: {event.get('type')} with subtype: {event.get('subtype')}")
            return {"status": "ignored", "reason": "Event type not supported or irrelevant"}

    except Exception as e:
        print(f"[DEBUG] Exception in slack_events: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# --- Zendesk Endpoints ---

@app.get("/zendesk/sync/start")
async def zendesk_sync_start(subdomain: str, days_back: int = 90):
    """Initiate background sync of Zendesk tickets"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    if not subdomain:
        raise HTTPException(status_code=400, detail="Subdomain parameter is required")
    
    # Start background sync
    asyncio.create_task(sync_zendesk_history(subdomain, days_back))
    
    return {
        "status": "started",
        "message": f"Zendesk sync initiated for subdomain {subdomain}, last {days_back} days",
        "started_at": datetime.now().isoformat()
    }

@app.post("/zendesk/webhooks/tickets/{subdomain}")
async def zendesk_webhook_tickets(subdomain: str, request: Request):
    """Handle Zendesk ticket webhooks"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        body = await request.body()
        print(f"[DEBUG] Zendesk webhook body: {body.decode('utf-8')}")
        print(f"[DEBUG] Webhook subdomain: {subdomain}")
        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as e:
            print(f"[DEBUG] JSON decode error: {e}")
            print(f"[DEBUG] Raw body: {body}")
            raise HTTPException(status_code=400, detail="Invalid JSON body")
        
        # Look up account for this subdomain
        account_id = await get_account_for_subdomain(subdomain)

        ticket = data.get("ticket", {}) or {}
        if not ticket:
            return {"status": "ignored", "reason": "No ticket data in webhook"}

        zendesk_ticket_id = str(ticket.get("id", ""))

        lock_key = get_account_lock_key(f"zd_ticket_{zendesk_ticket_id}", account_id)
        got = await acquire_lock(lock_key, ttl_sec=30)
        if not got:
            print(f"[zendesk] Duplicate webhook; skipping ticket {zendesk_ticket_id}")
            return {"status": "ignored", "reason": "duplicate webhook"}

        try:
            subject = (ticket.get("title") or ticket.get("subject") or "").strip()
            description = (
                ticket.get("latest_public_comment") or
                ticket.get("verbatim_description") or
                ticket.get("description") or
                ""
            ).strip()

            zendesk_status = (ticket.get("status") or "open").lower()
            status_mapping = {
                "new": "open",
                "open": "open",
                "pending": "pending",
                "hold": "pending",
                "solved": "solved",
                "closed": "closed",
            }
            status = status_mapping.get(zendesk_status, "open")
            priority = (ticket.get("priority") or "normal").lower()

            requester = ticket.get("requester") or {}
            requester_id = str(requester.get("id") or ticket.get("requester_id") or "")

            tags = ticket.get("tags") or []
            created_at = ticket.get("created_at") or ticket.get("created_at_with_time") or ""
            updated_at = ticket.get("updated_at") or ticket.get("updated_at_with_time") or ""

            print("ZD WEBHOOK FIELDS:", {
                "title": ticket.get("title"),
                "subject": ticket.get("subject"),
                "latest_public_comment": ticket.get("latest_public_comment"),
                "verbatim_description": ticket.get("verbatim_description"),
                "description": ticket.get("description"),
            })

            sentiment_score = calculate_sentiment_score(f"{subject} {description}".strip())

            customer_data = {
                "account_id": account_id,
                "zendesk_id": requester_id,
                "name": (requester.get("name") or f"Customer {requester_id}"),
                "email": requester.get("email") or "",
            }
            customer_response = await asyncio.to_thread(
                supabase.table("customers")
                .upsert(customer_data, on_conflict="zendesk_id")
                .execute
            )
            customer_id = customer_response.data[0]["id"] if customer_response.data else None

            ticket_insert_data = {
                "account_id": account_id,
                "zendesk_ticket_id": zendesk_ticket_id,
                "customer_id": customer_id,
                "subject": subject,
                "description": description,
                "status": status,
                "priority": priority,
                "sentiment_score": sentiment_score,
                "tags": tags,
                "created_at": created_at,
                "updated_at": updated_at,
            }
            ticket_response = await asyncio.to_thread(
                supabase.table("tickets")
                .upsert(ticket_insert_data, on_conflict="zendesk_ticket_id")
                .execute
            )

            ticket_id = ticket_response.data[0]["id"] if ticket_response.data else None
            if ticket_response.data:
                await broadcast_to_account_clients(account_id, {
                    "type": "new_ticket",
                    "subject": subject,
                    "ticket_id": zendesk_ticket_id,
                    "priority": priority,
                    "timestamp": datetime.now().isoformat()
                })

            try:
                await process_content_for_topics(
                    source="ticket",
                    source_id=zendesk_ticket_id,
                    data={"subject": subject, "description": description},
                    customer_id=customer_id,
                    account_id=account_id
                )
            except Exception as e:
                print(f"[topic processing] failed for ticket {ticket_id}: {e}")
        finally:
            await release_lock(lock_key)

        return {
            "status": "processed",
            "ticket_id": ticket_id,
            "customer_id": customer_id,
            "sentiment_score": sentiment_score,
            "processed_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"ERROR: Zendesk webhook processing failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error processing Zendesk webhook: {str(e)}")

# --- Zendesk OAuth Endpoints ---

# --- Zendesk OAuth Start (fixed) ---
@app.get("/zendesk/oauth/start")
async def zendesk_oauth_start(subdomain: str | None = None):
    """Redirect user to Zendesk OAuth authorization page with nonce cookie."""
    if not subdomain:
        subdomain = ZENDESK_SUBDOMAIN
    if not subdomain:
        raise HTTPException(status_code=400, detail="Zendesk subdomain is required")

    try:
        client_id, _client_secret, scopes = await get_zendesk_creds_for(subdomain)
    except SecurityUpgradeRequired:
        # Redirect with security upgrade error
        return RedirectResponse(url=f"{FRONTEND_URL}/?oauth=zendesk&ok=0&error=security_upgrade_required")

    # CSRF nonce
    nonce = secrets.token_urlsafe(32)
    state = json.dumps({"subdomain": subdomain, "nonce": nonce})

    redirect_uri = quote_plus(f"{PUBLIC_BASE_URL}/zendesk/oauth/callback")
    encoded_scopes = quote_plus(scopes)
    state_param = quote_plus(state)

    zendesk_auth_url = (
        f"https://{subdomain}.zendesk.com/oauth/authorizations/new"
        f"?response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&client_id={client_id}"
        f"&scope={encoded_scopes}"
        f"&state={state_param}"
    )

    # Set the cookie on *this* RedirectResponse
    resp = RedirectResponse(url=zendesk_auth_url)
    resp.set_cookie(
        key="zendesk_oauth_nonce",
        value=nonce,
        max_age=300,
        httponly=True,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
    )
    return resp

@app.get("/zendesk/oauth/callback")
async def zendesk_oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    if error:
        return RedirectResponse(url=f"{FRONTEND_URL}/?oauth=zendesk&ok=0&error={quote_plus(error)}")
    if not code:
        return RedirectResponse(url=f"{FRONTEND_URL}/?oauth=zendesk&ok=0&error={quote_plus('missing_code')}")
    if not state:
        return RedirectResponse(url=f"{FRONTEND_URL}/?oauth=zendesk&ok=0&error={quote_plus('missing_state')}")

    # Validate state & nonce
    try:
        state_data = json.loads(state)
        subdomain = state_data.get("subdomain")
        expected_nonce = state_data.get("nonce")
        stored_nonce = request.cookies.get("zendesk_oauth_nonce")

        if not subdomain:
            return RedirectResponse(url=f"{FRONTEND_URL}/?oauth=zendesk&ok=0&error={quote_plus('invalid_subdomain')}")
        if not expected_nonce or not stored_nonce or expected_nonce != stored_nonce:
            return RedirectResponse(url=f"{FRONTEND_URL}/?oauth=zendesk&ok=0&error={quote_plus('invalid_state')}")
    except (json.JSONDecodeError, KeyError):
        return RedirectResponse(url=f"{FRONTEND_URL}/?oauth=zendesk&ok=0&error={quote_plus('invalid_state')}")

    try:
        token_response = await exchange_zendesk_oauth_code(code, subdomain)
        if "access_token" not in token_response:
            return RedirectResponse(
                url=f"{FRONTEND_URL}/?oauth=zendesk&ok=0&error={quote_plus('token_exchange_failed')}"
            )

        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        token_type = token_response.get("token_type", "bearer")
        scope = token_response.get("scope")
        expires_in = token_response.get("expires_in")
        expires_at = _iso(datetime.now() + timedelta(seconds=expires_in)) if expires_in else None

        existing_resp = await asyncio.to_thread(
            supabase.table("zendesk_account_mapping")
            .select("account_id") 
            .eq("subdomain", subdomain)
            .execute
        )

        if existing_resp.data:
            mapped_account = existing_resp.data[0].get("account_id")
            current_account = get_account_id_from_request(request)
            if mapped_account and mapped_account != current_account:
                return RedirectResponse(
                    url=f"{FRONTEND_URL}/?oauth=zendesk&ok=0&error=subdomain_already_connected"
                )

        await asyncio.to_thread(
            supabase.table("zendesk_oauth_tokens").upsert({
                "subdomain": subdomain,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": token_type,
                "scope": scope,
                "expires_at": expires_at,
            }, on_conflict="subdomain").execute
        )


        # Store account mapping for multi-tenant support
        account_id = get_account_id_from_request(request)
        try:
            await asyncio.to_thread(
                supabase.table("zendesk_account_mapping").upsert({
                    "account_id": account_id,
                    "subdomain": subdomain
                }, on_conflict="subdomain").execute
            )
        except Exception as e:
            print(f"Warning: Failed to store Zendesk account mapping: {e}")

        integration_result = await setup_zendesk_integration(access_token, subdomain)

        # Store webhook/trigger IDs for disconnect
        if integration_result.get("status") == "success":
            integration_data = {
                "subdomain": subdomain,
                "webhook_id": integration_result.get("webhook_id"),
                "trigger_id": integration_result.get("trigger_id"),
            }
            await asyncio.to_thread(
                supabase.table("zendesk_integrations").upsert(
                    integration_data, on_conflict="subdomain"
                ).execute
            )

        intg_ok = 1 if integration_result.get("status") == "success" else 0
        asyncio.create_task(sync_zendesk_history(subdomain, 90))

        resp = RedirectResponse(
            url=f"{FRONTEND_URL}/?oauth=zendesk&ok=1&subdomain={quote_plus(subdomain)}&intg={intg_ok}"
        )
        resp.delete_cookie("zendesk_oauth_nonce", samesite=_cookie_samesite(), secure=_cookie_secure())
        return resp

    except Exception as e:
        print(f"Zendesk OAuth callback error: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/?oauth=zendesk&ok=0&error={quote_plus(str(e))}")

# --- Disconnect Endpoints ---

from pydantic import BaseModel

class SlackDisconnectBody(BaseModel):
    workspace_id: str

@app.post("/slack/disconnect")
async def slack_disconnect(request: Request, body: SlackDisconnectBody):
    """Disconnect and revoke Slack integration"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    # Get current account to verify ownership
    account_id = get_account_id_from_request(request)
    workspace_id = body.workspace_id

    # Verify ownership before disconnecting
    try:
        mapping_check = await asyncio.to_thread(
            supabase.table("slack_account_mapping")
            .select("account_id")
            .eq("workspace_id", workspace_id)
            .eq("account_id", account_id)
            .execute
        )
        
        if not mapping_check.data:
            raise HTTPException(status_code=403, detail="Workspace not found or not owned by current account")
    
    except Exception as e:
        if "not found" in str(e).lower() or "403" in str(e):
            raise HTTPException(status_code=403, detail="Workspace not found or not owned by current account")

    try:
        row = await asyncio.to_thread(
            supabase.table("slack_oauth_tokens")
            .select("access_token")
            .eq("workspace_id", workspace_id)
            .single()
            .execute
        )
        access_token = (row.data or {}).get("access_token")

        # Best-effort revoke; don't fail the whole request
        if access_token:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        "https://slack.com/api/auth.revoke",
                        data={"token": access_token},
                    )
            except Exception as e:
                print(f"Warning: Failed to revoke Slack token: {e}")

        # Remove token row
        await asyncio.to_thread(
            supabase.table("slack_oauth_tokens")
            .delete()
            .eq("workspace_id", workspace_id)
            .execute
        )

        await asyncio.to_thread(
            supabase.table("slack_account_mapping")
            .delete()
            .eq("workspace_id", workspace_id)
            .eq("account_id", account_id)
            .execute
        )
        return {"ok": True}

    except Exception as e:
        print(f"Error disconnecting Slack: {e}")
        # Idempotent success even if already deleted / revoked
        return {"ok": True}

class ZendeskDisconnectBody(BaseModel):
    subdomain: str

class ZendeskCredentialsRequest(BaseModel):
    subdomain: str
    client_id: str
    client_secret: str
    scopes: str = "read write"

class BetaApplicationRequest(BaseModel):
    name: str
    email: EmailStr
    company: str
    role: str
    current_tools: str
    time_spent_weekly: str
    pain_points: str
    company_size: str
    why_interested: str
    ready_to_pay: bool
    start_timeline: str

@app.post("/api/zendesk/credentials")
async def save_zendesk_credentials(request: Request, body: ZendeskCredentialsRequest):
    """Save and validate Zendesk OAuth credentials with existing auth flow"""
    
    # Use existing account validation
    account_id = get_account_id_from_request(request)
    if account_id == DEFAULT_ACCOUNT_ID:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Normalize subdomain (same logic as edge function)
    normalized_subdomain = normalize_subdomain_for_decrypt(body.subdomain)
    
    # Tighten subdomain validation - length 1-63 and no leading/trailing hyphen
    if not re.match(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$', normalized_subdomain):
        raise HTTPException(status_code=400, detail="Invalid subdomain format. Use only lowercase letters, numbers, and hyphens.")
    
    # Check account conflicts
    try:
        existing_resp = await asyncio.to_thread(
            lambda: supabase.table("zendesk_account_mapping")
            .select("account_id")
            .eq("subdomain", normalized_subdomain)
            .execute()
        )
        
        if (existing_resp.data and 
            existing_resp.data[0]["account_id"] != account_id):
            raise HTTPException(status_code=409, detail="This Zendesk subdomain is already connected to another account")
    except Exception as e:
        if "409" in str(e):
            raise
        logger.error(f"Error checking account conflicts: {e}")
    
    # Validate Zendesk instance exists
    try:
        async with httpx.AsyncClient() as client:
            response = await client.head(
                f"https://{normalized_subdomain}.zendesk.com/oauth/authorizations/new",
                headers={"User-Agent": "Catchalyze-Setup-Check/1.0"},
                timeout=10.0
            )
            if response.status_code == 404:
                raise HTTPException(status_code=400, detail="Zendesk subdomain not found")
    except httpx.TimeoutException:
        raise HTTPException(status_code=400, detail="Unable to verify Zendesk subdomain")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="Unable to verify Zendesk subdomain")
    
    # Test OAuth app configuration using form-encoded data
    try:
        async with httpx.AsyncClient() as client:
            test_response = await client.post(
                f"https://{normalized_subdomain}.zendesk.com/oauth/tokens",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "authorization_code",
                    "code": "test-validation-code",
                    "client_id": body.client_id,
                    "client_secret": body.client_secret,
                    "redirect_uri": f"{PUBLIC_BASE_URL}/zendesk/oauth/callback"
                },
                timeout=10.0
            )
            
            result = test_response.json()
            
            if result.get("error") == "invalid_client":
                raise HTTPException(status_code=400, detail="Invalid client credentials")
            elif result.get("error") == "redirect_uri_mismatch":
                raise HTTPException(status_code=400, detail="Redirect URI mismatch in OAuth app")
            # "invalid_grant" is expected and means credentials are valid
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=400, detail="Unable to validate OAuth configuration")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="Unable to validate OAuth configuration")
    
    # Encrypt client secret using existing encryption function
    encrypted_secret = encrypt_aes_gcm_credential(body.client_secret, normalized_subdomain)
    
    # Store credentials
    try:
        await asyncio.to_thread(
            lambda: supabase.table("zendesk_oauth_clients").upsert({
                "subdomain": normalized_subdomain,
                "client_id": body.client_id,
                "client_secret_enc": encrypted_secret,
                "encryption_version": "v1",
                "scopes": body.scopes,
                "redirect_uri": f"{PUBLIC_BASE_URL}/zendesk/oauth/callback"
            }, on_conflict="subdomain").execute()
        )
        
        # Update account mapping
        await asyncio.to_thread(
            lambda: supabase.table("zendesk_account_mapping").upsert({
                "subdomain": normalized_subdomain,
                "account_id": account_id
            }, on_conflict="subdomain").execute()
        )
        
        logger.info(f"Zendesk credentials stored successfully for subdomain: {normalized_subdomain}")
        
        return {
            "success": True,
            "subdomain": normalized_subdomain,
            "message": "Zendesk credentials validated and stored successfully"
        }
    except Exception as e:
        logger.error(f"Error storing Zendesk credentials: {e}")
        raise HTTPException(status_code=500, detail="Failed to store credentials")

@app.get("/api/zendesk/credentials")
async def get_zendesk_credentials_status(request: Request):
    """Get current Zendesk configuration status"""
    
    account_id = get_account_id_from_request(request)
    
    try:
        # Check for existing mapping
        mapping_resp = await asyncio.to_thread(
            lambda: supabase.table("zendesk_account_mapping")
            .select("subdomain")
            .eq("account_id", account_id)
            .single()
            .execute()
        )
        
        if not mapping_resp.data:
            return {"configured": False}
        
        subdomain = mapping_resp.data["subdomain"]
        
        # Get credentials metadata - handle case where mapping exists but no oauth row
        try:
            creds_resp = await asyncio.to_thread(
                lambda: supabase.table("zendesk_oauth_clients")
                .select("client_id, scopes, encryption_version")
                .eq("subdomain", subdomain)
                .single()
                .execute()
            )
            
            if not creds_resp.data:
                return {"configured": False}
            
            return {
                "configured": True,
                "subdomain": subdomain,
                "client_id": creds_resp.data.get("client_id", ""),
                "scopes": creds_resp.data.get("scopes", "read write"),
                "encryption_version": creds_resp.data.get("encryption_version", "legacy"),
                "needs_security_upgrade": creds_resp.data.get("encryption_version") != "v1"
            }
        except Exception:
            # Mapping exists but no credentials row - return not configured
            return {"configured": False}
        
    except Exception:
        return {"configured": False}

def sanitize_input(text: str) -> str:
    """Remove HTML tags and sanitize input"""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Escape remaining HTML entities
    text = html.escape(text)
    return text.strip()

def check_rate_limit(ip: str, window_minutes: int = 60, max_attempts: int = 3) -> bool:
    """Simple rate limiting implementation"""
    now = time.time()
    window_start = now - (window_minutes * 60)
    
    # Clean old entries
    rate_limit_store[ip] = [t for t in rate_limit_store[ip] if t > window_start]
    
    # Check if over limit
    if len(rate_limit_store[ip]) >= max_attempts:
        return False
    
    # Add current attempt
    rate_limit_store[ip].append(now)
    return True

@app.post("/api/beta/application")
async def submit_beta_application(request: Request, body: BetaApplicationRequest):
    """Handle beta application form submissions"""
    
    # Rate limiting
    client_ip = request.client.host
    if not check_rate_limit(client_ip):
        raise HTTPException(429, "Too many applications. Please try again in an hour.")
    
    # Sanitize all text inputs
    sanitized_data = {
        "name": sanitize_input(body.name),
        "email": body.email,  # EmailStr already validates
        "company": sanitize_input(body.company),
        "role": sanitize_input(body.role),
        "current_tools": sanitize_input(body.current_tools),
        "time_spent_weekly": sanitize_input(body.time_spent_weekly),
        "pain_points": sanitize_input(body.pain_points),
        "company_size": sanitize_input(body.company_size),
        "why_interested": sanitize_input(body.why_interested),
        "ready_to_pay": body.ready_to_pay,
        "start_timeline": sanitize_input(body.start_timeline)
    }
    
    # Basic validation
    if len(sanitized_data["name"]) < 2:
        raise HTTPException(400, "Name must be at least 2 characters")
    if len(sanitized_data["company"]) < 2:
        raise HTTPException(400, "Company name must be at least 2 characters")
    
    # Check for duplicate applications
    try:
        existing = await asyncio.to_thread(
            supabase.table("beta_applications")
            .select("id")
            .eq("email", body.email)
            .execute
        )
        if existing.data:
            raise HTTPException(409, "Application already exists for this email")
    except Exception as e:
        if "409" in str(e):
            raise
    
    try:
        # Store with additional tracking data
        application_data = {
            **sanitized_data,
            "ip_address": client_ip,
            "user_agent": request.headers.get("user-agent", ""),
            "submitted_at": datetime.now().isoformat(),
            "status": "pending_review"
        }
        
        await asyncio.to_thread(
            supabase.table("beta_applications").insert(application_data).execute
        )
        
        # Send email notification with error handling
        try:
            await send_beta_application_email(sanitized_data)
        except Exception as email_error:
            # Still save to database even if email fails
            print(f"Email failed but application saved: {email_error}")
        
        return {
            "success": True,
            "message": "Application submitted successfully. We'll review and contact you within 2 business days."
        }
        
    except Exception as e:
        print(f"Error processing beta application: {e}")
        raise HTTPException(500, "Failed to submit application")

async def send_beta_application_email(data: dict):
    """Send actionable email optimized for Gmail review"""
    
    subject = f"New Beta Application - {data['company']}"
    
    # Actionable email format for quick Gmail decision-making
    body_text = f"""
NEW BETA APPLICATION - {data['company']}

QUICK DECISION FACTORS:
Ready to pay $129: {"YES" if data['ready_to_pay'] else "NO"}
Company size: {data['company_size']}
Start timeline: {data['start_timeline']}

APPLICANT:
{data['name']} ({data['role']}) at {data['company']}
Email: {data['email']}

CURRENT PAIN: {data['pain_points']}
WHY CATCHALYZE: {data['why_interested']}

QUICK ACTIONS:
- APPROVE: Send PayPal invoice to {data['email']} for $129
- REJECT: Reply with feedback or timeline
- FOLLOW-UP: Schedule call to learn more

Tools they use now: {data['current_tools']}
Time spent weekly: {data['time_spent_weekly']}

Application submitted: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    """
    
    # For development/testing, always log to console
    print(f"[EMAIL TO support@catchalyze.com]")
    print(f"Subject: {subject}")
    print(body_text)
    
    # Send actual email if configured
    if GMAIL_SMTP_ENABLED and EMAIL_USERNAME and EMAIL_PASSWORD:
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_USERNAME
            msg['To'] = "support@catchalyze.com"
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body_text, 'plain'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Email sent successfully to support@catchalyze.com")
            
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            # Console log serves as backup

async def approve_beta_user(email: str):
    """Approve a beta user by setting beta_access = True"""
    try:
        result = await asyncio.to_thread(
            supabase.table("users").update({
                "beta_access": True
            }).eq("email", email).execute
        )
        
        if result.data:
            print(f"Beta access approved for {email}")
            return {"success": True, "message": f"Beta access approved for {email}"}
        else:
            print(f"User not found: {email}")
            return {"success": False, "message": f"User not found: {email}"}
            
    except Exception as e:
        print(f"Error approving beta user {email}: {e}")
        return {"success": False, "message": f"Error approving beta user: {str(e)}"}

@app.post("/zendesk/disconnect")
async def zendesk_disconnect(request: Request, body: ZendeskDisconnectBody):
    """Disconnect and clean up Zendesk integration"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    # Get current account to verify ownership
    account_id = get_account_id_from_request(request)
    subdomain = body.subdomain

    # Verify ownership before disconnecting
    try:
        mapping_check = await asyncio.to_thread(
            supabase.table("zendesk_account_mapping")
            .select("account_id")
            .eq("subdomain", subdomain)
            .eq("account_id", account_id)
            .execute
        )
        
        if not mapping_check.data:
            raise HTTPException(status_code=403, detail="Subdomain not found or not owned by current account")
    
    except Exception as e:
        if "not found" in str(e).lower() or "403" in str(e):
            raise HTTPException(status_code=403, detail="Subdomain not found or not owned by current account")

    try:
        # Try to get a fresh access token for cleanup (may fail if already revoked)
        access_token = None
        try:
            access_token = await refresh_zendesk_token_if_needed(subdomain)
        except Exception:
            pass

        # Load integration IDs (best-effort)
        webhook_id = trigger_id = None
        try:
            integ = await asyncio.to_thread(
                supabase.table("zendesk_integrations")
                .select("webhook_id,trigger_id")
                .eq("subdomain", subdomain)
                .single()
                .execute
            )
            if integ.data:
                webhook_id = integ.data.get("webhook_id")
                trigger_id = integ.data.get("trigger_id")
        except Exception:
            pass

        # Best-effort delete trigger & webhook
        if access_token:
            try:
                async with httpx.AsyncClient() as client:
                    if trigger_id:
                        await client.delete(
                            f"https://{subdomain}.zendesk.com/api/v2/triggers/{trigger_id}",
                            headers={"Authorization": f"Bearer {access_token}"},
                        )
                    if webhook_id:
                        await client.delete(
                            f"https://{subdomain}.zendesk.com/api/v2/webhooks/{webhook_id}",
                            headers={"Authorization": f"Bearer {access_token}"},
                        )
            except Exception as e:
                print(f"Warning: Failed to cleanup Zendesk resources: {e}")

        # Remove DB rows (idempotent)
        await asyncio.to_thread(
            supabase.table("zendesk_integrations")
            .delete()
            .eq("subdomain", subdomain)
            .execute
        )
        await asyncio.to_thread(
            supabase.table("zendesk_oauth_tokens")
            .delete()
            .eq("subdomain", subdomain)
            .execute
        )

        await asyncio.to_thread(
            supabase.table("zendesk_account_mapping")
            .delete()
            .eq("subdomain", subdomain)
            .eq("account_id", account_id)
            .execute
        )

        return {"ok": True}

    except Exception as e:
        print(f"Error disconnecting Zendesk: {e}")
        return {"ok": True}  # idempotent

# --- Google OAuth Implementation ---

@app.get("/auth/google")
async def google_oauth_start():
    """Redirect user to Google OAuth consent screen with CSRF protection."""
    print(f"DEBUG: PUBLIC_BASE_URL = {PUBLIC_BASE_URL}")
    if not GOOGLE_OAUTH_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    # CSRF protection with nonce
    nonce = secrets.token_urlsafe(32)
    state = json.dumps({"nonce": nonce})
    
    redirect_uri = quote_plus(f"{PUBLIC_BASE_URL}/auth/callback")
    scopes_param = quote_plus(GOOGLE_SCOPES)
    state_param = quote_plus(state)
    
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_OAUTH_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scopes_param}"
        f"&response_type=code"
        f"&state={state_param}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    
    # Set secure cookie for nonce validation
    response = RedirectResponse(url=google_auth_url)
    response.set_cookie(
        key="oauth_nonce",
        value=nonce,
        max_age=300,  # 5 minutes
        httponly=False,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        domain=None
    )
    return response

@app.get("/auth/callback")
async def google_oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    """Handle Google OAuth callback and create/link user accounts."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    if error:
        return RedirectResponse(url=f"{FRONTEND_URL}/?auth=error&message={quote_plus(error)}")
    if not code or not state:
        return RedirectResponse(url=f"{FRONTEND_URL}/?auth=error&message=missing_parameters")
    
    # Validate CSRF nonce
    try:
        state_data = json.loads(state)
        expected_nonce = state_data.get("nonce")
        stored_nonce = request.cookies.get("oauth_nonce")
        if not expected_nonce or not stored_nonce or expected_nonce != stored_nonce:
            return RedirectResponse(url=f"{FRONTEND_URL}/?auth=error&message=invalid_state")
    except json.JSONDecodeError:
        return RedirectResponse(url=f"{FRONTEND_URL}/?auth=error&message=invalid_state")
    
    try:
        # Exchange code for tokens
        user_data = await exchange_google_oauth_code(code)
        
        # Create or get existing user
        user_id, account_id = await create_or_link_user(user_data)
        
        # Create JWT token for session
        jwt_token = create_jwt_token(user_id, account_id)
        
        # Redirect to frontend dashboard
        response = RedirectResponse(url=FRONTEND_URL)
        response.set_cookie(
            key="auth_token",
            value=jwt_token,
            max_age=5184000,  # 2 months
            httponly=False,
            secure=_cookie_secure(),
            samesite=_cookie_samesite(),
            domain=None
        )
        # Clear nonce cookie
        # Clear nonce cookie
        response.delete_cookie("oauth_nonce", samesite=_cookie_samesite(), secure=_cookie_secure())  # Changed from "lax" to "none"
        return response
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/?auth=error&message={quote_plus(str(e))}")

async def exchange_google_oauth_code(code: str) -> dict:
    """Exchange OAuth code for user information."""
    async with httpx.AsyncClient() as client:
        # Get access token
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": f"{PUBLIC_BASE_URL}/auth/callback"
            }
        )
        token_data = token_response.json()
        
        if not token_response.status_code == 200:
            raise HTTPException(400, f"Token exchange failed: {token_data}")
        
        access_token = token_data["access_token"]
        
        # Get user info
        user_response = await client.get(
            f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}"
        )
        return user_response.json()

async def create_or_link_user(google_user_data: dict) -> tuple[str, str]:
    """Create new user and account, or return existing user's account."""
    google_id = google_user_data["id"]
    email = google_user_data["email"]
    name = google_user_data.get("name", "")
    avatar_url = google_user_data.get("picture", "")
    
    # Check if user exists
    user_resp = await asyncio.to_thread(
        supabase.table("users")
        .select("id")
        .eq("google_id", google_id)
        .execute
    )
    
    if user_resp.data:
        # Existing user - get their account
        user_id = user_resp.data[0]["id"]
        account_resp = await asyncio.to_thread(
            supabase.table("user_accounts")
            .select("account_id")
            .eq("user_id", user_id)
            .single()
            .execute
        )
        return user_id, account_resp.data["account_id"]
    else:
        # New user - create user and account
        user_data = {
            "google_id": google_id,
            "email": email,
            "name": name,
            "avatar_url": avatar_url
        }
        user_resp = await asyncio.to_thread(
            supabase.table("users").insert(user_data).execute
        )
        user_id = user_resp.data[0]["id"]
        
        # Create new account for user
        account_data = {
            "name": f"{name or email}'s Account",
            "slug": f"user-{user_id[:8]}"
        }
        account_resp = await asyncio.to_thread(
            supabase.table("accounts").insert(account_data).execute
        )
        account_id = account_resp.data[0]["id"]
        
        # Link user to account as owner
        await asyncio.to_thread(
            supabase.table("user_accounts").insert({
                "user_id": user_id,
                "account_id": account_id,
                "role": "owner"
            }).execute
        )
        
        return user_id, account_id

def create_jwt_token(user_id: str, account_id: str) -> str:
    """Create JWT token for user session."""
    import jwt
    
    payload = {
        "user_id": user_id,
        "account_id": account_id,
        "exp": datetime.now() + timedelta(days=60)
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# Account mapping functions for webhook routing
async def get_account_for_subdomain(subdomain: str) -> str:
    """Get account_id for Zendesk subdomain."""
    try:
        resp = await asyncio.to_thread(
            supabase.table("zendesk_account_mapping")
            .select("account_id")
            .eq("subdomain", subdomain)
            .single()
            .execute
        )
        return resp.data["account_id"]
    except Exception:
        # Fallback to development account for unmapped subdomains
        return DEFAULT_ACCOUNT_ID

async def get_account_for_workspace(workspace_id: str) -> str:
    """Get account_id for Slack workspace."""
    try:
        resp = await asyncio.to_thread(
            supabase.table("slack_account_mapping")
            .select("account_id")
            .eq("workspace_id", workspace_id)
            .single()
            .execute
        )
        return resp.data["account_id"]
    except Exception:
        # Fallback to development account for unmapped workspaces
        return DEFAULT_ACCOUNT_ID

def extract_subdomain_from_webhook_data(data: dict, request: Request) -> str:
    """Extract Zendesk subdomain from webhook data or headers."""
    # Try from URL (webhooks include subdomain in URL)
    host = request.headers.get("host", "")
    if ".zendesk.com" in host:
        return host.split(".zendesk.com")[0]
    
    # Fallback: extract from ticket URL or other data
    ticket = data.get("ticket", {})
    url = ticket.get("url", "")
    if url and ".zendesk.com" in url:
        return url.split("//")[1].split(".zendesk.com")[0]
    
    # Last resort: return default subdomain from env
    return ZENDESK_SUBDOMAIN or "unknown"

# --- FastAPI Endpoints ---

from typing import Optional

# SSE endpoint for real-time updates
sse_clients_by_account = {}  # Dict[str, List[asyncio.Queue]]

@app.get("/api/realtime-updates")
async def realtime_updates(request: Request):
    """Account-scoped Server-Sent Events endpoint"""
    # Get account ID from authenticated request
    account_id = get_account_id_from_request(request)
    print(f"[SSE DEBUG] Client connected for account: {account_id}")
    
    client_queue = asyncio.Queue()
    
    # Add client to account-specific list
    if account_id not in sse_clients_by_account:
        sse_clients_by_account[account_id] = []
    sse_clients_by_account[account_id].append(client_queue)
    
    async def event_stream():
        try:
            yield f"data: {json.dumps({'type': 'connected', 'account_id': account_id})}\n\n"
            
            while True:
                try:
                    event_data = await asyncio.wait_for(client_queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event_data)}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                except asyncio.CancelledError:
                    break
        finally:
            # Remove client from account-specific list
            if account_id in sse_clients_by_account:
                if client_queue in sse_clients_by_account[account_id]:
                    sse_clients_by_account[account_id].remove(client_queue)
                if not sse_clients_by_account[account_id]:
                    del sse_clients_by_account[account_id]
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")

async def broadcast_to_account_clients(account_id: str, event_data: Dict[str, Any]):
    """Broadcast only to clients for specific account"""
    print(f"[BROADCAST DEBUG] Sending {event_data.get('type')} to account: {account_id}")
    if account_id not in sse_clients_by_account:
        print(f"[BROADCAST DEBUG] No clients for account: {account_id}")
        return
    
    active_clients = []
    for client_queue in sse_clients_by_account[account_id][:]:
        try:
            await client_queue.put(event_data)
            active_clients.append(client_queue)
        except Exception:
            pass  # Client disconnected
    
    sse_clients_by_account[account_id] = active_clients

@app.get("/debug/test-trending")
async def test_trending():
    """Debug endpoint to manually trigger trend detection"""
    try:
        trends = await detect_trending_topics(time_window_minutes=180)
        
        # Add debug output
        print(f"[DEBUG] Manual endpoint found {len(trends)} trends")
        for trend in trends:
            print(f"[DEBUG] Trend: {trend.get('topic_id')} - {trend.get('name')}")
        
        return {
            "trends": trends,
            "trend_count": len(trends),
            "window_minutes": 180,
            "timestamp": datetime.now().isoformat(),
            "debug": "immediate_test"
        }
    except Exception as e:
        print(f"[DEBUG] Manual endpoint error: {e}")
        return {
            "error": str(e),
            "trends": [],
            "debug": "test_failed"
        }

# --- Testing Endpoints for Account Isolation (Milestone 9B) ---

async def get_account_data_count(table_name: str, account_id: str) -> int:
    """Get count of records for specific account."""
    try:
        resp = await asyncio.to_thread(
            supabase.table(table_name)
            .select("id", count="exact")
            .eq("account_id", account_id)
            .execute
        )
        return resp.count or 0
    except Exception:
        return 0

async def get_webhook_mappings(table_name: str, account_id: str) -> list[str]:
    """Get webhook mappings for an account."""
    try:
        if table_name == "zendesk_account_mapping":
            resp = await asyncio.to_thread(
                supabase.table(table_name)
                .select("subdomain")
                .eq("account_id", account_id)
                .execute
            )
            return [item["subdomain"] for item in resp.data]
        else:  # slack_account_mapping
            resp = await asyncio.to_thread(
                supabase.table(table_name)
                .select("workspace_id, team_name")
                .eq("account_id", account_id)
                .execute
            )
            return [f"{item['team_name'] or item['workspace_id']}" for item in resp.data]
    except Exception:
        return []

@app.get("/api/auth/me")
async def get_current_user(request: Request):
    """Get current authenticated user and account info."""
    try:
        import jwt
        auth_cookie = request.cookies.get("auth_token")
        if not auth_cookie:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        payload = jwt.decode(auth_cookie, JWT_SECRET, algorithms=["HS256"])
        user_id = payload["user_id"]
        account_id = payload["account_id"]
        
        # Get user info
        user_resp = await asyncio.to_thread(
            supabase.table("users")
            .select("id, email, name, avatar_url, beta_access")
            .eq("id", user_id)
            .single()
            .execute
        )
        
        # Get account info
        account_resp = await asyncio.to_thread(
            supabase.table("accounts")
            .select("id, name, slug")
            .eq("id", account_id)
            .single()
            .execute
        )
        
        return {
            "user": user_resp.data,
            "account": account_resp.data
        }
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/api/integration-status")
async def get_integration_status(request: Request):
    """Get integration connection status for current account"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        account_id = get_account_id_from_request(request)
        print(f"[INTEGRATION STATUS] Checking for account: {account_id}")

        # Slack mapping
        slack_resp = await asyncio.to_thread(
            supabase.table("slack_account_mapping")
            .select("workspace_id, team_name")
            .eq("account_id", account_id)
            .execute
        )
        print(f"[INTEGRATION STATUS] Slack query result: {slack_resp.data}")

        # Zendesk mapping
        zendesk_map = await asyncio.to_thread(
            supabase.table("zendesk_account_mapping")
            .select("subdomain")
            .eq("account_id", account_id)
            .single()
            .execute
        )
        zendesk_info = zendesk_map.data if zendesk_map.data else None

        # Zendesk token existence (mapping alone is not connected)
        has_token = False
        if zendesk_info:
            token_resp = await asyncio.to_thread(
                supabase.table("zendesk_oauth_tokens")
                .select("subdomain")
                .eq("subdomain", zendesk_info["subdomain"])
                .limit(1)
                .execute
            )
            has_token = bool(token_resp.data)
        print(f"[INTEGRATION STATUS] Zendesk query result: {zendesk_map.data}")

        return {
            "slack_connected": bool(slack_resp.data),
            "slack_info": slack_resp.data[0] if slack_resp.data else None,
            "zendesk_connected": has_token,
            "zendesk_info": zendesk_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking integration status: {str(e)}")

@app.post("/api/auth/logout")
async def logout():
    """Clear auth cookie and logout user."""
    response = JSONResponse({"success": True})
    response.delete_cookie(
        "auth_token",
        samesite=_cookie_samesite(),  # Must match the creation parameter
        secure=_cookie_secure(),
        domain=None  # Also match this
    )
    return response

@app.get("/test/account-info")
async def account_info_dashboard(request: Request):
    """Simple endpoint to validate account isolation and webhook mappings."""
    account_id = get_account_id_from_request(request)
    
    # Get current user info if authenticated
    user_info = None
    if account_id != DEFAULT_ACCOUNT_ID:
        try:
            import jwt
            auth_cookie = request.cookies.get("auth_token")
            if auth_cookie:
                payload = jwt.decode(auth_cookie, JWT_SECRET, algorithms=["HS256"])
                user_resp = await asyncio.to_thread(
                    supabase.table("users")
                    .select("email, name")
                    .eq("id", payload["user_id"])
                    .single()
                    .execute
                )
                user_info = user_resp.data
        except Exception:
            pass
    
    # Get account info
    try:
        account_resp = await asyncio.to_thread(
            supabase.table("accounts")
            .select("name, slug, created_at")
            .eq("id", account_id)
            .single()
            .execute
        )
        account_info = account_resp.data
    except Exception:
        account_info = {"name": "Development Account", "slug": "dev", "created_at": "N/A"}
    
    # Get data counts for this account
    tickets_count = await get_account_data_count("tickets", account_id)
    slack_messages_count = await get_account_data_count("slack_messages", account_id)
    topics_count = await get_account_data_count("topics", account_id)
    
    # Get webhook mappings for this account
    zendesk_mappings = await get_webhook_mappings("zendesk_account_mapping", account_id)
    slack_mappings = await get_webhook_mappings("slack_account_mapping", account_id)
    
    # Create simple HTML response
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Account Validation - Catchalyze</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
            .section {{ margin: 20px 0; padding: 15px; background: #f9f9f9; border-radius: 6px; }}
            .count {{ font-size: 24px; font-weight: bold; color: #007bff; }}
            .mapping {{ background: #e8f4f8; padding: 8px; margin: 5px 0; border-radius: 4px; }}
            .actions {{ margin-top: 30px; }}
            .btn {{ background: #007bff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px; margin-right: 10px; }}
            .danger {{ background: #dc3545; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Account Validation Dashboard</h1>
            
            <div class="section">
                <h2>Current Account</h2>
                <p><strong>Account:</strong> {account_info['name']}</p>
                <p><strong>Account ID:</strong> {account_id}</p>
                <p><strong>Created:</strong> {account_info.get('created_at', 'N/A')[:19]}</p>
                {f"<p><strong>User:</strong> {user_info['name']} ({user_info['email']})</p>" if user_info else "<p><strong>User:</strong> Development account (not authenticated)</p>"}
            </div>
            
            <div class="section">
                <h2>Account Data</h2>
                <p>Tickets: <span class="count">{tickets_count}</span></p>
                <p>Slack Messages: <span class="count">{slack_messages_count}</span></p>
                <p>Topics: <span class="count">{topics_count}</span></p>
            </div>
            
            <div class="section">
                <h2>Webhook Mappings</h2>
                <h3>Zendesk Subdomains:</h3>
                {(''.join([f'<div class="mapping">{subdomain}</div>' for subdomain in zendesk_mappings])) or '<p>No Zendesk mappings</p>'}
                
                <h3>Slack Workspaces:</h3>
                {(''.join([f'<div class="mapping">{workspace}</div>' for workspace in slack_mappings])) or '<p>No Slack mappings</p>'}
            </div>
            
            <div class="actions">
                <a href="/auth/google" class="btn">Login with Google</a>
                <a href="/test/create-test-data" class="btn">Create Test Data</a>
                <a href="/test/logout" class="btn danger">Logout</a>
            </div>
            
            <div style="margin-top: 40px; padding: 15px; background: #fff3cd; border-radius: 6px;">
                <h3>Validation Steps</h3>
                <ol>
                    <li>Note current account ID and data counts</li>
                    <li>Login with different Google account</li>
                    <li>Verify new account has different ID and zero data</li>
                    <li>Create test data and confirm isolation</li>
                </ol>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.get("/test/create-test-data")
async def create_test_data(request: Request):
    """Create minimal test data for the current account."""
    account_id = get_account_id_from_request(request)
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # Create one sample ticket
        sample_ticket = {
            "account_id": account_id,
            "zendesk_ticket_id": f"test-{secrets.token_hex(4)}",
            "subject": f"Test ticket for account {account_id[:8]}",
            "description": "This is test data to validate account isolation",
            "status": "open",
            "priority": "normal",
            "sentiment_score": -0.2,
            "created_at": datetime.now().isoformat()
        }
        
        await asyncio.to_thread(
            supabase.table("tickets").insert([sample_ticket]).execute
        )
        
        # Create one sample Slack message
        sample_message = {
            "account_id": account_id,
            "slack_message_id": f"test-{secrets.token_hex(8)}",
            "text": f"Test message for account isolation validation",
            "user_id": "test_user",
            "slack_channel_id": "test_channel",
            "sentiment_score": -0.1,
            "created_at": datetime.now().isoformat()
        }
        
        await asyncio.to_thread(
            supabase.table("slack_messages").insert([sample_message]).execute
        )
        
        return RedirectResponse(url="/test/account-info")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create test data: {str(e)}")

@app.get("/test/logout")
async def test_logout():
    """Clear auth cookie and redirect to account info."""
    response = RedirectResponse(url="/test/account-info")
    response.delete_cookie("auth_token", samesite=_cookie_samesite(), secure=_cookie_secure())
    return response

@app.get("/test/webhook-routing/{platform}/{identifier}")
async def test_webhook_routing(platform: str, identifier: str):
    """Test webhook routing logic without actual webhook data."""
    try:
        if platform == "zendesk":
            account_id = await get_account_for_subdomain(identifier)
        elif platform == "slack":
            account_id = await get_account_for_workspace(identifier)
        else:
            raise HTTPException(400, "Platform must be 'zendesk' or 'slack'")
        
        return {
            "platform": platform,
            "identifier": identifier,
            "resolved_account_id": account_id,
            "is_development_fallback": account_id == DEFAULT_ACCOUNT_ID,
            "routing_status": "success" if account_id != DEFAULT_ACCOUNT_ID else "fallback"
        }
        
    except Exception as e:
        raise HTTPException(500, f"Webhook routing test failed: {str(e)}")

@app.get("/test/topic-clustering-sanity")
async def test_topic_clustering_sanity(request: Request):
    """Basic sanity check that clustering respects account boundaries."""
    account_id = get_account_id_from_request(request)
    
    try:
        # Get topics for current account only
        topics_resp = await asyncio.to_thread(
            supabase.table("topics")
            .select("topic_id, name, keywords, doc_count_30d, account_id")
            .eq("account_id", account_id)
            .execute
        )
        
        # Get message counts to verify clustering scope
        messages_resp = await asyncio.to_thread(
            supabase.table("slack_messages")
            .select("id", count="exact")
            .eq("account_id", account_id)
            .execute
        )
        
        tickets_resp = await asyncio.to_thread(
            supabase.table("tickets")
            .select("id", count="exact")
            .eq("account_id", account_id)
            .execute
        )
        
        return {
            "account_id": account_id,
            "topics_found": len(topics_resp.data),
            "topics": topics_resp.data,
            "total_messages": messages_resp.count or 0,
            "total_tickets": tickets_resp.count or 0,
            "clustering_scope": "account_isolated"
        }
        
    except Exception as e:
        raise HTTPException(500, f"Topic clustering test failed: {str(e)}")

@app.get("/health")
async def root(subdomain: Optional[str] = None):
    """Health check endpoint"""
    tools = await mcp_server.get_tools()

    # Check if at least one Zendesk OAuth token exists (optionally for a specific subdomain)
    zendesk_oauth_connected = False
    if supabase:
        try:
            qb = supabase.table("zendesk_oauth_tokens").select("subdomain,expires_at")
            if subdomain:
                qb = qb.eq("subdomain", subdomain)
            qb = qb.limit(1)
            resp = await asyncio.to_thread(qb.execute)
            zendesk_oauth_connected = bool(resp.data)  # True if at least one token row
        except Exception:
            zendesk_oauth_connected = False

    return {
        "status": "healthy",
        "service": "Catchalyze MCP Server",
        "version": "1.0.0",
        "protocol_version": "2025-03-26",
        "supabase_connected": supabase is not None,
        "openai_configured": openai_client is not None,
        "slack_configured": all([SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, SLACK_SIGNING_SECRET]),
        "zendesk_configured": all([ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_API_TOKEN]),
        "zendesk_oauth_configured": all([ZENDESK_CLIENT_ID, ZENDESK_CLIENT_SECRET]),
        "zendesk_oauth_connected": zendesk_oauth_connected,
        "available_tools": list(tools.keys()),
    }

app.mount("/", mcp_app)