#!/usr/bin/env python3
"""
ALPHA OMEGA - API GATEWAY & WEBHOOKS
Expose automation via REST API with webhook triggers
Version: 2.0.0
"""

import asyncio
import json
import logging
import time
import hashlib
import hmac
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading


class HttpMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class WebhookStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class ApiKeyStatus(Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class ApiKey:
    id: str
    key: str
    name: str
    permissions: List[str] = field(default_factory=list)
    rate_limit: int = 100
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0
    last_used: float = 0
    use_count: int = 0
    status: ApiKeyStatus = ApiKeyStatus.ACTIVE

    def is_valid(self) -> bool:
        if self.status != ApiKeyStatus.ACTIVE:
            return False
        if self.expires_at > 0 and time.time() > self.expires_at:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "permissions": self.permissions,
            "rate_limit": self.rate_limit,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "last_used": self.last_used,
            "use_count": self.use_count,
            "status": self.status.value,
        }


@dataclass
class Webhook:
    id: str
    name: str
    url: str
    events: List[str] = field(default_factory=list)
    secret: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    status: WebhookStatus = WebhookStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    last_triggered: float = 0
    trigger_count: int = 0
    failure_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "events": self.events,
            "status": self.status.value,
            "created_at": self.created_at,
            "last_triggered": self.last_triggered,
            "trigger_count": self.trigger_count,
        }


@dataclass
class ApiEndpoint:
    path: str
    method: HttpMethod
    handler: str
    description: str = ""
    requires_auth: bool = True
    permissions: List[str] = field(default_factory=list)
    rate_limit: int = 100
    cache_ttl: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "method": self.method.value,
            "handler": self.handler,
            "description": self.description,
            "requires_auth": self.requires_auth,
            "permissions": self.permissions,
            "rate_limit": self.rate_limit,
        }


@dataclass
class ApiRequest:
    id: str
    path: str
    method: str
    headers: Dict[str, str]
    body: Any
    query_params: Dict[str, str]
    api_key_id: str = ""
    timestamp: float = field(default_factory=time.time)
    ip_address: str = ""
    user_agent: str = ""


@dataclass
class ApiResponse:
    status_code: int
    body: Any
    headers: Dict[str, str] = field(default_factory=dict)
    execution_time_ms: float = 0


@dataclass
class WebhookPayload:
    event: str
    timestamp: float
    data: Dict[str, Any]
    signature: str = ""

    def to_json(self) -> str:
        return json.dumps(
            {
                "event": self.event,
                "timestamp": self.timestamp,
                "data": self.data,
            }
        )


class ApiGateway:
    """API Gateway for exposing automation via REST"""

    def __init__(self, db_path: str = "data/api_gateway.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("ApiGateway")

        self._api_keys: Dict[str, ApiKey] = {}
        self._endpoints: Dict[str, ApiEndpoint] = {}
        self._handlers: Dict[str, Callable] = {}
        self._rate_limits: Dict[str, List[float]] = {}

        self._init_db()
        self._register_default_endpoints()

    def _init_db(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id TEXT PRIMARY KEY,
                    key TEXT UNIQUE,
                    name TEXT,
                    permissions TEXT,
                    rate_limit INTEGER,
                    created_at REAL,
                    expires_at REAL,
                    last_used REAL,
                    use_count INTEGER,
                    status TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS request_logs (
                    id TEXT PRIMARY KEY,
                    api_key_id TEXT,
                    path TEXT,
                    method TEXT,
                    status_code INTEGER,
                    execution_time_ms REAL,
                    timestamp REAL
                )
            """)
            conn.commit()

    def _register_default_endpoints(self):
        """Register default API endpoints"""
        default_endpoints = [
            ApiEndpoint(
                "/api/v1/status",
                HttpMethod.GET,
                "get_status",
                "Get system status",
                False,
            ),
            ApiEndpoint(
                "/api/v1/command",
                HttpMethod.POST,
                "execute_command",
                "Execute a command",
            ),
            ApiEndpoint(
                "/api/v1/automate", HttpMethod.POST, "run_automation", "Run automation"
            ),
            ApiEndpoint(
                "/api/v1/workflows", HttpMethod.GET, "list_workflows", "List workflows"
            ),
            ApiEndpoint(
                "/api/v1/workflows/{id}/run",
                HttpMethod.POST,
                "run_workflow",
                "Run workflow",
            ),
            ApiEndpoint(
                "/api/v1/schedule", HttpMethod.POST, "schedule_task", "Schedule task"
            ),
            ApiEndpoint("/api/v1/memory", HttpMethod.GET, "get_memory", "Get memory"),
            ApiEndpoint(
                "/api/v1/memory", HttpMethod.POST, "store_memory", "Store memory"
            ),
            ApiEndpoint("/api/v1/query", HttpMethod.POST, "query_llm", "Query LLM"),
        ]

        for endpoint in default_endpoints:
            self._endpoints[f"{endpoint.method.value}:{endpoint.path}"] = endpoint

    async def initialize(self) -> bool:
        """Initialize the gateway"""
        self._load_api_keys()
        self.logger.info("API Gateway initialized")
        return True

    def _load_api_keys(self):
        """Load API keys from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM api_keys WHERE status = 'active'")
            for row in cursor.fetchall():
                api_key = ApiKey(
                    id=row[0],
                    key=row[1],
                    name=row[2],
                    permissions=json.loads(row[3]) if row[3] else [],
                    rate_limit=row[4],
                    created_at=row[5],
                    expires_at=row[6],
                    last_used=row[7],
                    use_count=row[8],
                    status=ApiKeyStatus(row[9]),
                )
                self._api_keys[api_key.key] = api_key

    def register_handler(self, name: str, handler: Callable):
        """Register a handler for an endpoint"""
        self._handlers[name] = handler
        self.logger.debug(f"Registered handler: {name}")

    def register_endpoint(self, endpoint: ApiEndpoint):
        """Register a custom endpoint"""
        key = f"{endpoint.method.value}:{endpoint.path}"
        self._endpoints[key] = endpoint
        self.logger.info(
            f"Registered endpoint: {endpoint.method.value} {endpoint.path}"
        )

    def generate_api_key(
        self,
        name: str,
        permissions: List[str] = None,
        rate_limit: int = 100,
        expires_in_days: int = 0,
    ) -> ApiKey:
        """Generate a new API key"""
        import secrets

        key_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:12]
        key_value = f"ao_{secrets.token_urlsafe(32)}"

        expires_at = 0
        if expires_in_days > 0:
            expires_at = time.time() + (expires_in_days * 86400)

        api_key = ApiKey(
            id=key_id,
            key=key_value,
            name=name,
            permissions=permissions or ["*"],
            rate_limit=rate_limit,
            expires_at=expires_at,
        )

        self._api_keys[key_value] = api_key
        self._save_api_key(api_key)

        self.logger.info(f"Generated API key: {name}")
        return api_key

    def _save_api_key(self, api_key: ApiKey):
        """Save API key to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO api_keys
                (id, key, name, permissions, rate_limit, created_at, expires_at, last_used, use_count, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    api_key.id,
                    api_key.key,
                    api_key.name,
                    json.dumps(api_key.permissions),
                    api_key.rate_limit,
                    api_key.created_at,
                    api_key.expires_at,
                    api_key.last_used,
                    api_key.use_count,
                    api_key.status.value,
                ),
            )
            conn.commit()

    async def handle_request(self, request: ApiRequest) -> ApiResponse:
        """Handle an incoming API request"""
        start_time = time.time()

        endpoint_key = f"{request.method}:{request.path}"

        if endpoint_key not in self._endpoints:
            endpoint_key = self._find_dynamic_endpoint(request.method, request.path)

        if endpoint_key not in self._endpoints:
            return ApiResponse(status_code=404, body={"error": "Not found"})

        endpoint = self._endpoints[endpoint_key]

        if endpoint.requires_auth:
            auth_result = await self._authenticate(request)
            if not auth_result["valid"]:
                return ApiResponse(
                    status_code=401, body={"error": auth_result["error"]}
                )

            api_key = auth_result.get("api_key")
            if api_key:
                request.api_key_id = api_key.id

                if not self._check_rate_limit(api_key, endpoint):
                    return ApiResponse(
                        status_code=429, body={"error": "Rate limit exceeded"}
                    )

        handler = self._handlers.get(endpoint.handler)
        if not handler:
            return ApiResponse(status_code=500, body={"error": "Handler not found"})

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(request)
            else:
                result = handler(request)

            execution_time = (time.time() - start_time) * 1000

            return ApiResponse(
                status_code=200,
                body=result,
                execution_time_ms=execution_time,
            )

        except Exception as e:
            self.logger.error(f"Handler error: {e}")
            return ApiResponse(status_code=500, body={"error": str(e)})

    def _find_dynamic_endpoint(self, method: str, path: str) -> str:
        """Find endpoint with path parameters"""
        for key, endpoint in self._endpoints.items():
            if not endpoint.method.value == method:
                continue

            if self._match_path(endpoint.path, path):
                return key

        return ""

    def _match_path(self, pattern: str, path: str) -> bool:
        """Match path against pattern with parameters"""
        pattern_parts = pattern.split("/")
        path_parts = path.split("/")

        if len(pattern_parts) != len(path_parts):
            return False

        for p_part, a_part in zip(pattern_parts, path_parts):
            if p_part.startswith("{") and p_part.endswith("}"):
                continue
            if p_part != a_part:
                return False

        return True

    async def _authenticate(self, request: ApiRequest) -> Dict[str, Any]:
        """Authenticate API request"""
        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            key = auth_header[7:]
        elif "api_key" in request.query_params:
            key = request.query_params["api_key"]
        elif "api_key" in request.body and isinstance(request.body, dict):
            key = request.body.get("api_key", "")
        else:
            return {"valid": False, "error": "No API key provided"}

        if key not in self._api_keys:
            return {"valid": False, "error": "Invalid API key"}

        api_key = self._api_keys[key]

        if not api_key.is_valid():
            return {"valid": False, "error": "API key expired or revoked"}

        api_key.last_used = time.time()
        api_key.use_count += 1
        self._save_api_key(api_key)

        return {"valid": True, "api_key": api_key}

    def _check_rate_limit(self, api_key: ApiKey, endpoint: ApiEndpoint) -> bool:
        """Check rate limit"""
        now = time.time()
        key = f"{api_key.id}:{endpoint.path}"

        if key not in self._rate_limits:
            self._rate_limits[key] = []

        self._rate_limits[key] = [t for t in self._rate_limits[key] if now - t < 60]

        limit = min(api_key.rate_limit, endpoint.rate_limit)

        if len(self._rate_limits[key]) >= limit:
            return False

        self._rate_limits[key].append(now)
        return True

    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key"""
        for key, api_key in self._api_keys.items():
            if api_key.id == key_id:
                api_key.status = ApiKeyStatus.REVOKED
                self._save_api_key(api_key)
                self.logger.info(f"Revoked API key: {api_key.name}")
                return True
        return False

    def list_api_keys(self) -> List[Dict[str, Any]]:
        """List all API keys"""
        return [k.to_dict() for k in self._api_keys.values()]

    def list_endpoints(self) -> List[Dict[str, Any]]:
        """List all endpoints"""
        return [e.to_dict() for e in self._endpoints.values()]


class WebhookManager:
    """Manage webhooks for external integrations"""

    def __init__(self, db_path: str = "data/webhooks.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("WebhookManager")

        self._webhooks: Dict[str, Webhook] = {}
        self._event_subscribers: Dict[str, List[str]] = {}

        self._init_db()

    def _init_db(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS webhooks (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    url TEXT,
                    events TEXT,
                    secret TEXT,
                    headers TEXT,
                    status TEXT,
                    created_at REAL,
                    last_triggered REAL,
                    trigger_count INTEGER,
                    failure_count INTEGER
                )
            """)
            conn.commit()

    async def initialize(self) -> bool:
        """Initialize webhook manager"""
        self._load_webhooks()
        self.logger.info("Webhook Manager initialized")
        return True

    def _load_webhooks(self):
        """Load webhooks from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM webhooks WHERE status = 'active'")
            for row in cursor.fetchall():
                webhook = Webhook(
                    id=row[0],
                    name=row[1],
                    url=row[2],
                    events=json.loads(row[3]) if row[3] else [],
                    secret=row[4],
                    headers=json.loads(row[5]) if row[5] else {},
                    status=WebhookStatus(row[6]),
                    created_at=row[7],
                    last_triggered=row[8],
                    trigger_count=row[9],
                    failure_count=row[10],
                )
                self._webhooks[webhook.id] = webhook

                for event in webhook.events:
                    if event not in self._event_subscribers:
                        self._event_subscribers[event] = []
                    self._event_subscribers[event].append(webhook.id)

    def create_webhook(
        self,
        name: str,
        url: str,
        events: List[str],
        secret: str = "",
    ) -> Webhook:
        """Create a new webhook"""
        import secrets

        webhook_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:12]

        webhook = Webhook(
            id=webhook_id,
            name=name,
            url=url,
            events=events,
            secret=secret or secrets.token_urlsafe(32),
        )

        self._webhooks[webhook_id] = webhook

        for event in events:
            if event not in self._event_subscribers:
                self._event_subscribers[event] = []
            self._event_subscribers[event].append(webhook_id)

        self._save_webhook(webhook)

        self.logger.info(f"Created webhook: {name}")
        return webhook

    def _save_webhook(self, webhook: Webhook):
        """Save webhook to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO webhooks
                (id, name, url, events, secret, headers, status, created_at, last_triggered, trigger_count, failure_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    webhook.id,
                    webhook.name,
                    webhook.url,
                    json.dumps(webhook.events),
                    webhook.secret,
                    json.dumps(webhook.headers),
                    webhook.status.value,
                    webhook.created_at,
                    webhook.last_triggered,
                    webhook.trigger_count,
                    webhook.failure_count,
                ),
            )
            conn.commit()

    async def trigger_event(self, event: str, data: Dict[str, Any]):
        """Trigger an event to all subscribed webhooks"""
        if event not in self._event_subscribers:
            return

        payload = WebhookPayload(
            event=event,
            timestamp=time.time(),
            data=data,
        )

        webhook_ids = self._event_subscribers.get(event, [])

        for webhook_id in webhook_ids:
            webhook = self._webhooks.get(webhook_id)
            if webhook and webhook.status == WebhookStatus.ACTIVE:
                asyncio.create_task(self._send_webhook(webhook, payload))

    async def _send_webhook(self, webhook: Webhook, payload: WebhookPayload):
        """Send webhook request"""
        try:
            import httpx

            body = payload.to_json()

            if webhook.secret:
                signature = hmac.new(
                    webhook.secret.encode(), body.encode(), hashlib.sha256
                ).hexdigest()
                payload.signature = f"sha256={signature}"

            headers = {
                "Content-Type": "application/json",
                "X-AlphaOmega-Event": payload.event,
                "X-AlphaOmega-Signature": payload.signature,
                **webhook.headers,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook.url,
                    content=body,
                    headers=headers,
                    timeout=30.0,
                )

                if response.status_code >= 200 and response.status_code < 300:
                    webhook.trigger_count += 1
                    webhook.last_triggered = time.time()
                    self.logger.info(f"Webhook sent: {webhook.name}")
                else:
                    webhook.failure_count += 1
                    self.logger.error(
                        f"Webhook failed: {webhook.name} - {response.status_code}"
                    )

                self._save_webhook(webhook)

        except Exception as e:
            webhook.failure_count += 1
            self._save_webhook(webhook)
            self.logger.error(f"Webhook error: {e}")

    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook"""
        if webhook_id not in self._webhooks:
            return False

        webhook = self._webhooks[webhook_id]

        for event in webhook.events:
            if event in self._event_subscribers:
                self._event_subscribers[event] = [
                    wid for wid in self._event_subscribers[event] if wid != webhook_id
                ]

        del self._webhooks[webhook_id]

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM webhooks WHERE id = ?", (webhook_id,))
            conn.commit()

        return True

    def list_webhooks(self) -> List[Dict[str, Any]]:
        """List all webhooks"""
        return [w.to_dict() for w in self._webhooks.values()]

    def pause_webhook(self, webhook_id: str) -> bool:
        """Pause a webhook"""
        webhook = self._webhooks.get(webhook_id)
        if webhook:
            webhook.status = WebhookStatus.PAUSED
            self._save_webhook(webhook)
            return True
        return False

    def resume_webhook(self, webhook_id: str) -> bool:
        """Resume a webhook"""
        webhook = self._webhooks.get(webhook_id)
        if webhook:
            webhook.status = WebhookStatus.ACTIVE
            self._save_webhook(webhook)
            return True
        return False
