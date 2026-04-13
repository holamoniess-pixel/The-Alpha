"""
Core Orchestrator - Main coordination hub for RAVER operations.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

from ..policy import PolicyEngine, RiskScore, ApprovalMethod
from ..audit import AuditLogger, AuditEvent
from ..ipc import IPCClient
from ...raver_shared.schemas import (
    ActionRequest, PolicyDecision, UserRole, ActionType, 
    SystemPauseRequest, SystemPauseResponse
)
from .intent_engine import IntentEngine
from .system_controller import SystemController, SystemPauseManager


logger = logging.getLogger(__name__)


class CoreOrchestrator:
    """Main orchestrator that coordinates all RAVER components."""
    
    def __init__(self):
        self.policy_engine = PolicyEngine()
        self.audit_logger = AuditLogger()
        self.intent_engine = IntentEngine()
        self.system_controller = SystemController()
        self.pause_manager = SystemPauseManager()
        self.ipc_client = IPCClient("core-orchestrator")
        
        self.active_requests: Dict[str, ActionRequest] = {}
        self.pending_approvals: Dict[str, PolicyDecision] = {}
        
        # System state
        self.is_paused = False
        self.pause_reason: Optional[str] = None
        self.paused_operations: List[str] = []
        
        logger.info("Core Orchestrator initialized")
    
    async def start(self):
        """Start the orchestrator and initialize subsystems."""
        logger.info("Starting Core Orchestrator...")
        
        # Initialize subsystems
        await self.policy_engine.initialize()
        await self.audit_logger.initialize()
        await self.intent_engine.initialize()
        await self.system_controller.initialize()
        
        # Subscribe to IPC messages
        self.ipc_client.subscribe_to_messages(
            ["action_request", "pause_request", "approval_response"],
            self._handle_ipc_message
        )
        
        logger.info("Core Orchestrator started successfully")
    
    async def stop(self):
        """Stop the orchestrator and cleanup resources."""
        logger.info("Stopping Core Orchestrator...")
        
        # Cancel all active requests
        for request_id in list(self.active_requests.keys()):
            await self.cancel_request(request_id, "System shutdown")
        
        # Stop subsystems
        await self.system_controller.cleanup()
        await self.audit_logger.cleanup()
        
        logger.info("Core Orchestrator stopped")
    
    async def process_user_request(self, user_id: str, user_roles: List[UserRole],
                                  request_text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a user request through the intent engine and policy system.
        
        Returns:
            Dictionary with request status and details
        """
        try:
            # Check if system is paused
            if self.is_paused:
                return {
                    "status": "paused",
                    "message": f"System is paused: {self.pause_reason}",
                    "pause_reason": self.pause_reason,
                    "paused_operations": self.paused_operations
                }
            
            # Parse intent
            intent = await self.intent_engine.parse_intent(request_text, context)
            
            # Create action request
            action_request = ActionRequest(
                request_id=str(uuid.uuid4()),
                user_id=user_id,
                action_type=intent.action_type,
                target_resource=intent.target_resource,
                parameters=intent.parameters,
                context=context or {},
                timestamp=datetime.now()
            )
            
            # Store active request
            self.active_requests[action_request.request_id] = action_request
            
            # Evaluate policy
            policy_decision = await self.policy_engine.evaluate_request(
                action_request, user_roles
            )
            
            # Log the request and decision
            await self.audit_logger.log_request(action_request, policy_decision)
            
            # Handle the decision
            if policy_decision.approved:
                if policy_decision.approval_method == ApprovalMethod.NONE:
                    # Execute immediately
                    result = await self._execute_action(action_request)
                    await self.audit_logger.log_execution(action_request, result)
                    
                    return {
                        "status": "completed",
                        "request_id": action_request.request_id,
                        "result": result
                    }
                else:
                    # Request approval
                    self.pending_approvals[action_request.request_id] = policy_decision
                    
                    # Send approval request via IPC
                    await self.ipc_client.send_message(
                        "ui-gateway",
                        "approval_request",
                        {
                            "request_id": action_request.request_id,
                            "action_type": action_request.action_type.value,
                            "target_resource": action_request.target_resource,
                            "risk_level": policy_decision.risk_level.value,
                            "approval_method": policy_decision.approval_method.value,
                            "reason": policy_decision.reason
                        }
                    )
                    
                    return {
                        "status": "pending_approval",
                        "request_id": action_request.request_id,
                        "approval_method": policy_decision.approval_method.value,
                        "reason": policy_decision.reason
                    }
            else:
                # Request denied
                await self.audit_logger.log_denial(action_request, policy_decision)
                
                return {
                    "status": "denied",
                    "request_id": action_request.request_id,
                    "reason": policy_decision.reason,
                    "risk_level": policy_decision.risk_level.value
                }
                
        except Exception as e:
            logger.error(f"Error processing user request: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def handle_approval_response(self, request_id: str, approved: bool, 
                                     approval_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle user response to approval request."""
        try:
            if request_id not in self.pending_approvals:
                return {"status": "error", "error": "Request not found"}
            
            action_request = self.active_requests.get(request_id)
            if not action_request:
                return {"status": "error", "error": "Active request not found"}
            
            policy_decision = self.pending_approvals[request_id]
            
            if approved:
                # Execute the action
                result = await self._execute_action(action_request)
                await self.audit_logger.log_execution(action_request, result)
                
                # Clean up
                del self.pending_approvals[request_id]
                del self.active_requests[request_id]
                
                return {
                    "status": "completed",
                    "request_id": request_id,
                    "result": result
                }
            else:
                # User denied approval
                await self.audit_logger.log_denial(action_request, policy_decision)
                
                # Clean up
                del self.pending_approvals[request_id]
                del self.active_requests[request_id]
                
                return {
                    "status": "cancelled",
                    "request_id": request_id,
                    "reason": "User denied approval"
                }
                
        except Exception as e:
            logger.error(f"Error handling approval response: {e}")
            return {"status": "error", "error": str(e)}
    
    async def pause_system(self, user_id: str, reason: str = None) -> SystemPauseResponse:
        """Pause all system operations."""
        try:
            # Create pause request
            pause_request = SystemPauseRequest(
                user_id=user_id,
                reason=reason,
                timestamp=datetime.now()
            )
            
            # Pause the system
            pause_result = await self.pause_manager.pause_system(pause_request)
            
            if pause_result.paused:
                self.is_paused = True
                self.pause_reason = reason or "Manual pause"
                self.paused_operations = pause_result.paused_operations
                
                # Log the pause
                await self.audit_logger.log_system_pause(pause_request)
                
                # Notify all subsystems
                await self.ipc_client.send_message(
                    "broadcast",
                    "system_paused",
                    {
                        "reason": self.pause_reason,
                        "operations": self.paused_operations
                    }
                )
            
            return pause_result
            
        except Exception as e:
            logger.error(f"Error pausing system: {e}")
            return SystemPauseResponse(
                paused=False,
                paused_operations=[],
                message=f"Error: {str(e)}",
                timestamp=datetime.now()
            )
    
    async def resume_system(self, user_id: str) -> Dict[str, Any]:
        """Resume system operations."""
        try:
            if not self.is_paused:
                return {"status": "error", "error": "System is not paused"}
            
            # Resume the system
            resume_result = await self.pause_manager.resume_system(user_id)
            
            if resume_result["success"]:
                self.is_paused = False
                self.pause_reason = None
                self.paused_operations = []
                
                # Log the resume
                await self.audit_logger.log_system_resume(user_id)
                
                # Notify all subsystems
                await self.ipc_client.send_message(
                    "broadcast",
                    "system_resumed",
                    {"user_id": user_id}
                )
            
            return resume_result
            
        except Exception as e:
            logger.error(f"Error resuming system: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            "orchestrator": {
                "status": "running" if not self.is_paused else "paused",
                "paused": self.is_paused,
                "pause_reason": self.pause_reason,
                "paused_operations": self.paused_operations,
                "active_requests": len(self.active_requests),
                "pending_approvals": len(self.pending_approvals)
            },
            "subsystems": {
                "policy_engine": await self.policy_engine.get_status(),
                "audit_logger": await self.audit_logger.get_status(),
                "intent_engine": await self.intent_engine.get_status(),
                "system_controller": await self.system_controller.get_status()
            }
        }
    
    async def _execute_action(self, request: ActionRequest) -> Dict[str, Any]:
        """Execute an approved action."""
        try:
            # Route to appropriate handler
            if request.action_type == ActionType.PROCESS_TERMINATE:
                return await self.system_controller.terminate_process(
                    request.target_resource, request.parameters
                )
            elif request.action_type == ActionType.FILE_MODIFY:
                return await self.system_controller.modify_file(
                    request.target_resource, request.parameters
                )
            elif request.action_type == ActionType.VAULT_ACCESS:
                return await self.system_controller.access_vault(
                    request.target_resource, request.parameters
                )
            elif request.action_type == ActionType.UI_AUTOMATION:
                return await self.system_controller.execute_ui_automation(
                    request.target_resource, request.parameters
                )
            elif request.action_type == ActionType.LINK_INSPECT:
                return await self.system_controller.inspect_link(
                    request.target_resource, request.parameters
                )
            else:
                return {
                    "success": False,
                    "error": f"Unsupported action type: {request.action_type}"
                }
                
        except Exception as e:
            logger.error(f"Error executing action: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_ipc_message(self, message):
        """Handle incoming IPC messages."""
        try:
            if message.message_type == "action_request":
                data = message.data
                result = await self.process_user_request(
                    data["user_id"],
                    [UserRole(role) for role in data["user_roles"]],
                    data["request_text"],
                    data.get("context", {})
                )
                
                # Send response
                await self.ipc_client.send_message(
                    message.source,
                    "action_response",
                    result
                )
                
            elif message.message_type == "pause_request":
                data = message.data
                pause_result = await self.pause_system(
                    data["user_id"],
                    data.get("reason")
                )
                
                await self.ipc_client.send_message(
                    message.source,
                    "pause_response",
                    pause_result.dict()
                )
                
            elif message.message_type == "approval_response":
                data = message.data
                result = await self.handle_approval_response(
                    data["request_id"],
                    data["approved"],
                    data.get("context", {})
                )
                
                await self.ipc_client.send_message(
                    message.source,
                    "approval_result",
                    result
                )
                
        except Exception as e:
            logger.error(f"Error handling IPC message: {e}")
    
    async def cancel_request(self, request_id: str, reason: str) -> bool:
        """Cancel an active request."""
        try:
            if request_id in self.active_requests:
                request = self.active_requests[request_id]
                await self.audit_logger.log_cancellation(request, reason)
                
                # Remove from active requests
                del self.active_requests[request_id]
                
                # Remove from pending approvals if present
                if request_id in self.pending_approvals:
                    del self.pending_approvals[request_id]
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling request: {e}")
            return False
