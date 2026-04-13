"""Main FastAPI application for RAVER Gateway."""

import asyncio
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from raver_core.orchestrator import CoreOrchestrator
from raver_vault import Vault
from raver_shared.schemas import Intent, PolicyDecision, WebSocketMessage


app = FastAPI(
    title="RAVER Gateway API",
    description="Gateway API for RAVER system with WebSocket support",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
orchestrator = CoreOrchestrator()
vault = Vault()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[UUID, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: UUID):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: UUID):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    async def send_personal_message(self, message: dict, user_id: UUID):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()

# Pydantic models for API
class IntentRequest(BaseModel):
    user_id: UUID
    command: str
    context: Optional[Dict] = None

class IntentResponse(BaseModel):
    intent_id: UUID
    approved: bool
    risk_level: str
    risk_score: float
    requires_approval: bool
    reason: str

class VaultStoreRequest(BaseModel):
    user_id: UUID
    service: str
    label: str
    secret_data: str

class VaultRetrieveRequest(BaseModel):
    user_id: UUID
    secret_id: UUID
    user_roles: List[str]

# API Endpoints
@app.post("/api/v1/intent", response_model=IntentResponse)
async def process_intent(request: IntentRequest):
    """Process user intent through policy engine."""
    try:
        # Create intent
        intent = Intent(
            user_id=request.user_id,
            command=request.command,
            context=request.context or {}
        )
        
        # Process through orchestrator
        decision = await orchestrator.process_intent(intent)
        
        # Send WebSocket notification
        await manager.send_personal_message({
            "type": "intent_processed",
            "intent_id": str(intent.intent_id),
            "approved": decision.approved,
            "risk_level": decision.risk_level,
            "reason": decision.reason
        }, request.user_id)
        
        return IntentResponse(
            intent_id=intent.intent_id,
            approved=decision.approved,
            risk_level=decision.risk_level,
            risk_score=decision.risk_score,
            requires_approval=decision.approval_method != "none",
            reason=decision.reason
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/vault/store")
async def store_secret(request: VaultStoreRequest):
    """Store a secret in the vault."""
    try:
        secret_id = vault.store_secret(
            service=request.service,
            label=request.label,
            secret_data=request.secret_data,
            owner_user_id=request.user_id
        )
        
        return {"secret_id": str(secret_id), "status": "stored"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/vault/retrieve")
async def retrieve_secret(request: VaultRetrieveRequest):
    """Retrieve a secret from the vault."""
    try:
        secret_data = vault.retrieve_secret(
            secret_id=request.secret_id,
            requesting_user_id=request.user_id,
            user_roles=request.user_roles
        )
        
        if secret_data is None:
            raise HTTPException(status_code=404, detail="Secret not found or access denied")
        
        return {"secret_data": secret_data}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/vault/secrets")
async def list_secrets(user_id: UUID, user_roles: List[str]):
    """List secrets accessible to user."""
    try:
        secrets = vault.list_secrets(user_id, user_roles)
        
        return {
            "secrets": [
                {
                    "secret_id": str(secret.secret_id),
                    "service": secret.service,
                    "label": secret.label,
                    "created_at": secret.created_at.isoformat(),
                    "updated_at": secret.updated_at.isoformat()
                }
                for secret in secrets
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/system/pause")
async def pause_system(user_id: UUID):
    """Pause system operations."""
    try:
        intent = Intent(
            user_id=user_id,
            command="pause",
            context={"source": "api"}
        )
        
        decision = await orchestrator.process_intent(intent)
        
        if decision.approved:
            # Broadcast pause notification
            await manager.broadcast({
                "type": "system_paused",
                "user_id": str(user_id),
                "timestamp": asyncio.get_event_loop().time()
            })
        
        return {"paused": decision.approved, "reason": decision.reason}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/system/resume")
async def resume_system(user_id: UUID):
    """Resume system operations."""
    try:
        resumed = await orchestrator.resume_system(user_id)
        
        if resumed:
            # Broadcast resume notification
            await manager.broadcast({
                "type": "system_resumed",
                "user_id": str(user_id),
                "timestamp": asyncio.get_event_loop().time()
            })
        
        return {"resumed": resumed}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/system/status")
async def system_status():
    """Get system status."""
    return {
        "paused": orchestrator.is_system_paused(),
        "active_intents": len(orchestrator.active_intents),
        "connected_clients": len(manager.active_connections)
    }

# WebSocket endpoint
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: UUID):
    """WebSocket endpoint for real-time communication."""
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Handle WebSocket messages
            message_type = data.get("type")
            
            if message_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif message_type == "subscribe_status":
                await websocket.send_json({
                    "type": "status_update",
                    "paused": orchestrator.is_system_paused(),
                    "active_intents": len(orchestrator.active_intents)
                })
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RAVER Gateway API",
        "version": "0.1.0",
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
