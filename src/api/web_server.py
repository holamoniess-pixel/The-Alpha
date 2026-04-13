#!/usr/bin/env python3
"""
ALPHA OMEGA - WEB API SERVER
FastAPI Backend with WebSocket Support
Version: 2.0.0
"""

import asyncio
import json
import logging
import time
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    Depends,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.system import AlphaOmegaCore, SystemConfig, get_system

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebAPI")

app = FastAPI(
    title="Alpha Omega API", description="AI Assistant Control API", version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CommandRequest(BaseModel):
    command: str = Field(..., description="Voice or text command")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context"
    )


class CommandResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    processing_time_ms: float


class StatusResponse(BaseModel):
    state: str
    uptime: str
    components: Dict[str, Any]
    metrics: Dict[str, Any]


class VaultRequest(BaseModel):
    action: str
    service: Optional[str] = None
    label: Optional[str] = None
    secret_data: Optional[str] = None
    secret_id: Optional[str] = None


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        async with self._lock:
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)

            for conn in disconnected:
                self.active_connections.remove(conn)


manager = ConnectionManager()

_system: Optional[AlphaOmegaCore] = None


@app.on_event("startup")
async def startup_event():
    global _system

    config_path = Path("config.yaml")
    if config_path.exists():
        config = SystemConfig.from_yaml(str(config_path))
    else:
        config = SystemConfig()

    _system = get_system(config)

    success = await _system.initialize()

    if success:
        asyncio.create_task(_system.start())
        logger.info("System started successfully")
    else:
        logger.error("System initialization failed")


@app.on_event("shutdown")
async def shutdown_event():
    global _system

    if _system:
        await _system.shutdown()
        logger.info("System shutdown complete")


@app.get("/")
async def root():
    return {
        "name": "Alpha Omega API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "status": "/status",
            "command": "/command",
            "chat": "/chat",
            "vault": "/vault",
            "vision": "/vision",
            "ws": "/ws",
        },
    }


@app.get("/status", response_model=StatusResponse)
async def get_status():
    if not _system:
        raise HTTPException(status_code=503, detail="System not initialized")

    status_str = _system.get_status()
    metrics = _system.metrics.to_dict()

    components = {}
    for name, component in _system._components.items():
        if hasattr(component, "get_stats"):
            components[name] = component.get_stats()
        else:
            components[name] = {"status": "active"}

    return StatusResponse(
        state=_system.state.name,
        uptime=metrics.get("uptime_formatted", "0:00:00"),
        components=components,
        metrics=metrics,
    )


@app.post("/command", response_model=CommandResponse)
async def execute_command(request: CommandRequest):
    if not _system:
        raise HTTPException(status_code=503, detail="System not initialized")

    start_time = time.time()

    result = await _system.process_command(request.command, request.context)

    processing_time = (time.time() - start_time) * 1000

    return CommandResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        data=result.get("data"),
        processing_time_ms=processing_time,
    )


@app.post("/chat")
async def chat(request: CommandRequest):
    if not _system:
        raise HTTPException(status_code=503, detail="System not initialized")

    intelligence = _system.get_component("intelligence")
    if not intelligence:
        raise HTTPException(status_code=503, detail="Intelligence engine not available")

    intent = await intelligence.process_command(request.command, request.context)

    if intent.intent_type.name == "QUERY":
        response = await intelligence.answer_query(intent)
    else:
        response = await _system.process_command(request.command, request.context)

    await manager.broadcast(
        {
            "type": "chat",
            "command": request.command,
            "response": response,
            "timestamp": time.time(),
        }
    )

    return response


@app.get("/vault")
async def vault_status():
    if not _system:
        raise HTTPException(status_code=503, detail="System not initialized")

    vault = _system.get_component("vault")
    if not vault:
        raise HTTPException(status_code=503, detail="Vault not available")

    return vault.get_vault_info()


@app.post("/vault/unlock")
async def vault_unlock(password: str, user_id: str = "default"):
    if not _system:
        raise HTTPException(status_code=503, detail="System not initialized")

    vault = _system.get_component("vault")
    if not vault:
        raise HTTPException(status_code=503, detail="Vault not available")

    success = vault.unlock_vault(password, user_id)

    return {"success": success, "unlocked": vault.is_unlocked()}


@app.post("/vault/lock")
async def vault_lock():
    if not _system:
        raise HTTPException(status_code=503, detail="System not initialized")

    vault = _system.get_component("vault")
    if not vault:
        raise HTTPException(status_code=503, detail="Vault not available")

    vault.lock_vault()
    return {"success": True, "unlocked": False}


@app.post("/vault/secrets")
async def vault_create_secret(request: VaultRequest):
    if not _system:
        raise HTTPException(status_code=503, detail="System not initialized")

    vault = _system.get_component("vault")
    if not vault or not vault.is_unlocked():
        raise HTTPException(status_code=403, detail="Vault is locked")

    from src.vault.vault_manager import SecretType

    secret_type = SecretType.PASSWORD
    if request.action == "create":
        secret_id = vault.create_secret(
            service=request.service,
            label=request.label,
            secret_data=request.secret_data,
            secret_type=secret_type,
        )

        if secret_id:
            return {"success": True, "secret_id": secret_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to create secret")

    elif request.action == "get":
        secret = vault.get_secret(request.secret_id)
        if secret:
            return {"success": True, "secret": secret}
        else:
            raise HTTPException(status_code=404, detail="Secret not found")

    elif request.action == "list":
        secrets = vault.list_secrets(service=request.service)
        return {"success": True, "secrets": secrets}

    elif request.action == "delete":
        success = vault.delete_secret(request.secret_id)
        return {"success": success}

    else:
        raise HTTPException(status_code=400, detail="Invalid action")


@app.get("/vault/logs")
async def vault_logs(limit: int = 100):
    if not _system:
        raise HTTPException(status_code=503, detail="System not initialized")

    vault = _system.get_component("vault")
    if not vault or not vault.is_unlocked():
        raise HTTPException(status_code=403, detail="Vault is locked")

    logs = vault.get_access_logs(limit=limit)
    return {"success": True, "logs": logs}


@app.get("/vision")
async def vision_analyze():
    if not _system:
        raise HTTPException(status_code=503, detail="System not initialized")

    vision = _system.get_component("vision")
    if not vision:
        raise HTTPException(status_code=503, detail="Vision system not available")

    analysis = vision.analyze_screen()

    return {
        "success": True,
        "analysis": analysis.to_dict(),
        "summary": vision.get_screen_summary(),
    }


@app.get("/vision/image")
async def vision_image():
    if not _system:
        raise HTTPException(status_code=503, detail="System not initialized")

    vision = _system.get_component("vision")
    if not vision:
        raise HTTPException(status_code=503, detail="Vision system not available")

    image_b64 = vision.encode_image_base64()

    return {"success": True, "image": image_b64}


@app.get("/learning/patterns")
async def learning_patterns(limit: int = 20):
    if not _system:
        raise HTTPException(status_code=503, detail="System not initialized")

    learning = _system.get_component("learning")
    if not learning:
        raise HTTPException(status_code=503, detail="Learning system not available")

    patterns = learning.get_patterns(limit=limit)
    return {"success": True, "patterns": [p.to_dict() for p in patterns]}


@app.get("/learning/suggestions")
async def learning_suggestions(limit: int = 10):
    if not _system:
        raise HTTPException(status_code=503, detail="System not initialized")

    learning = _system.get_component("learning")
    if not learning:
        raise HTTPException(status_code=503, detail="Learning system not available")

    suggestions = learning.get_suggestions(limit=limit)
    return {"success": True, "suggestions": suggestions}


@app.get("/audit")
async def audit_logs(event_type: str = None, limit: int = 100):
    if not _system:
        raise HTTPException(status_code=503, detail="System not initialized")

    security = _system.get_component("security")
    if not security:
        raise HTTPException(status_code=503, detail="Security system not available")

    events = security.audit_logger.get_events(event_type=event_type, limit=limit)

    return {"success": True, "events": [e.__dict__ for e in events]}


@app.post("/system/pause")
async def system_pause(reason: str = "Manual pause"):
    if not _system:
        raise HTTPException(status_code=503, detail="System not initialized")

    result = await _system.pause(reason)
    return result


@app.post("/system/resume")
async def system_resume():
    if not _system:
        raise HTTPException(status_code=503, detail="System not initialized")

    result = await _system.resume()
    return result


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        await websocket.send_json(
            {
                "type": "connected",
                "message": "WebSocket connected",
                "timestamp": time.time(),
            }
        )

        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                if message.get("type") == "command":
                    result = await _system.process_command(
                        message.get("command", ""), message.get("context")
                    )

                    await websocket.send_json(
                        {
                            "type": "command_result",
                            "result": result,
                            "timestamp": time.time(),
                        }
                    )

                elif message.get("type") == "ping":
                    await websocket.send_json(
                        {"type": "pong", "timestamp": time.time()}
                    )

            except json.JSONDecodeError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Invalid JSON",
                        "timestamp": time.time(),
                    }
                )

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "system_initialized": _system is not None and _system.initialized,
    }


class UIMessage(BaseModel):
    type: str
    data: Optional[Dict[str, Any]] = None


@app.on_event("startup")
async def broadcast_status():
    asyncio.create_task(status_broadcaster())


async def status_broadcaster():
    while True:
        try:
            await asyncio.sleep(5)

            if _system and _system.initialized:
                await manager.broadcast(
                    {
                        "type": "status_update",
                        "state": _system.state.name,
                        "metrics": _system.metrics.to_dict(),
                        "timestamp": time.time(),
                    }
                )
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Status broadcast error: {e}")


def run_server(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
