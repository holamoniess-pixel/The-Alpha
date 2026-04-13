"""
RAVER Gateway API

FastAPI server providing REST endpoints and WebSocket support for RAVER UI.
Handles authentication, authorization, and communication with core orchestrator.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import asyncio
import json
import uuid
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'packages'))

from raver_core.orchestrator import CoreOrchestrator, Intent, IntentType
from raver_core.policy import PolicyEngine, Role
from raver_core.audit import AuditLogger, AuditEvent, EventType
from raver_vault.vault import VaultManager


# Pydantic models
class UserAuth(BaseModel):
    user_id: str
    password: str


class IntentRequest(BaseModel):
    intent_type: str
    description: str
    parameters: Dict[str, Any] = {}


class ApprovalRequest(BaseModel):
    intent_id: str
    approver_id: str
    approved: bool
    reason: Optional[str] = None


class SystemControlRequest(BaseModel):
    action: str  # pause, resume
    reason: Optional[str] = None


# Initialize FastAPI app
app = FastAPI(
    title="RAVER Gateway API",
    description="Gateway API for RAVER system",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React UI
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Global components
orchestrator: Optional[CoreOrchestrator] = None
vault_manager: Optional[VaultManager] = None
policy_engine: Optional[PolicyEngine] = None
audit_logger: Optional[AuditLogger] = None

# WebSocket connections
active_connections: List[WebSocket] = []


# Initialize components
async def initialize_components():
    global orchestrator, vault_manager, policy_engine, audit_logger
    
    # Initialize core components
    policy_engine = PolicyEngine()
    audit_logger = AuditLogger()
    orchestrator = CoreOrchestrator(policy_engine, audit_logger)
    vault_manager = VaultManager()
    
    # Register demo tools
    async def demo_tool(params: Dict[str, Any]) -> Dict[str, Any]:
        return {"message": "Demo tool executed", "params": params}
    
    orchestrator.register_tool("demo", demo_tool)


# Authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # Simple token validation (in production, use proper JWT)
    if token.startswith("user_"):
        user_id = token[5:]
        policy_engine.set_user_role(user_id, Role.USER)
        return user_id
    elif token.startswith("admin_"):
        user_id = token[6:]
        policy_engine.set_user_role(user_id, Role.ADMIN)
        return user_id
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)


manager = ConnectionManager()


# API Routes
@app.on_event("startup")
async def startup_event():
    await initialize_components()


@app.post("/auth/login")
async def login(auth: UserAuth):
    """Authenticate user and return token."""
    # Simple authentication (in production, use proper auth)
    if auth.user_id == "admin" and auth.password == "admin123":
        token = f"admin_{auth.user_id}"
    elif auth.user_id == "user" and auth.password == "user123":
        token = f"user_{auth.user_id}"
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    return {"access_token": token, "token_type": "bearer"}


@app.post("/intents")
async def create_intent(
    intent_request: IntentRequest,
    current_user: str = Depends(get_current_user)
):
    """Create and process a new intent."""
    try:
        intent = Intent(
            intent_type=IntentType(intent_request.intent_type),
            description=intent_request.description,
            parameters=intent_request.parameters,
            user_id=current_user
        )
        
        result = await orchestrator.process_intent(intent)
        
        return {
            "intent_id": intent.intent_id,
            "success": result.success,
            "message": result.message,
            "data": result.data,
            "requires_approval": result.data.get("requires_approval", False) if result.data else False
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/intents/{intent_id}/approve")
async def approve_intent(
    intent_id: str,
    approval: ApprovalRequest,
    current_user: str = Depends(get_current_user)
):
    """Approve or deny a pending intent."""
    try:
        if approval.approved:
            result = await orchestrator.approve_intent(intent_id, current_user)
        else:
            # Deny the intent
            result = {"success": True, "message": "Intent denied"}
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/system/status")
async def get_system_status(current_user: str = Depends(get_current_user)):
    """Get current system status."""
    return orchestrator.get_system_status()


@app.post("/system/control")
async def control_system(
    control: SystemControlRequest,
    current_user: str = Depends(get_current_user)
):
    """Control system pause/resume."""
    try:
        if control.action == "pause":
            success = orchestrator.pause_system(control.reason or "User requested pause")
            message = "System paused" if success else "Failed to pause system"
        elif control.action == "resume":
            success = orchestrator.resume_system()
            message = "System resumed" if success else "Failed to resume system"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action"
            )
        
        return {"success": success, "message": message}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/vault/status")
async def get_vault_status(current_user: str = Depends(get_current_user)):
    """Get vault status."""
    return vault_manager.get_vault_info()


@app.post("/vault/unlock")
async def unlock_vault(
    auth: UserAuth,
    current_user: str = Depends(get_current_user)
):
    """Unlock the vault."""
    try:
        vault_manager.set_current_user(current_user)
        success = vault_manager.unlock_vault(auth.password, current_user)
        
        return {"success": success, "message": "Vault unlocked" if success else "Failed to unlock vault"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/vault/secrets")
async def list_secrets(current_user: str = Depends(get_current_user)):
    """List accessible secrets."""
    try:
        secrets = vault_manager.list_secrets()
        return {"secrets": secrets}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/vault/secrets")
async def create_secret(
    secret_data: Dict[str, Any],
    current_user: str = Depends(get_current_user)
):
    """Create a new secret."""
    try:
        secret_id = vault_manager.create_secret(
            service=secret_data.get("service", ""),
            label=secret_data.get("label", ""),
            secret_data=secret_data.get("data", ""),
            description=secret_data.get("description", ""),
            tags=secret_data.get("tags", [])
        )
        
        if secret_id:
            return {"success": True, "secret_id": secret_id}
        else:
            return {"success": False, "message": "Failed to create secret"}
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/audit/logs")
async def get_audit_logs(
    limit: int = 100,
    current_user: str = Depends(get_current_user)
):
    """Get audit logs."""
    try:
        events = await audit_logger.query_events(limit=limit)
        return {"events": events}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message["type"] == "ping":
                await manager.send_personal_message(json.dumps({"type": "pong"}), websocket)
            elif message["type"] == "status":
                status = orchestrator.get_system_status()
                await manager.send_personal_message(json.dumps({"type": "status", "data": status}), websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
