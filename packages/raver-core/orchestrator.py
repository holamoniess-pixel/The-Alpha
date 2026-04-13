"""
RAVER Core Orchestrator

Central coordination component that manages intent processing, tool routing,
and coordinates between policy engine, audit logging, and action execution.
"""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from .policy import PolicyEngine, RiskScore, ApprovalMethod
from .audit import AuditLogger, AuditEvent, EventType


class IntentType(Enum):
    """Types of intents the orchestrator can process."""
    AUTOMATION = "automation"
    SYSTEM_CONTROL = "system_control"
    VAULT_ACCESS = "vault_access"
    NETWORK_ACTION = "network_action"
    UI_INTERACTION = "ui_interaction"
    SECURITY_ACTION = "security_action"


@dataclass
class Intent:
    """Represents a user intent that needs to be processed."""
    intent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    intent_type: IntentType = IntentType.AUTOMATION
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    user_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    requires_approval: bool = False
    risk_score: RiskScore = RiskScore.LOW


@dataclass
class ActionResult:
    """Result of an executed action."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None


class SystemPauseController:
    """Controls system-wide pause functionality."""
    
    def __init__(self):
        self._paused = False
        self._pause_reason = ""
        self._paused_tasks: List[str] = []
    
    def pause(self, reason: str = "User requested pause") -> bool:
        """Pause all automated operations."""
        self._paused = True
        self._pause_reason = reason
        return True
    
    def resume(self) -> bool:
        """Resume paused operations."""
        self._paused = False
        self._pause_reason = ""
        self._paused_tasks.clear()
        return True
    
    def is_paused(self) -> bool:
        """Check if system is paused."""
        return self._paused
    
    def get_pause_reason(self) -> str:
        """Get the reason for pause."""
        return self._pause_reason
    
    def add_paused_task(self, task_id: str):
        """Add a task to the paused tasks list."""
        if task_id not in self._paused_tasks:
            self._paused_tasks.append(task_id)
    
    def get_paused_tasks(self) -> List[str]:
        """Get list of paused tasks."""
        return self._paused_tasks.copy()


class CoreOrchestrator:
    """Main orchestrator for RAVER system operations."""
    
    def __init__(self, policy_engine: PolicyEngine, audit_logger: AuditLogger):
        self.policy_engine = policy_engine
        self.audit_logger = audit_logger
        self.pause_controller = SystemPauseController()
        self.active_intents: Dict[str, Intent] = {}
        self.tool_registry: Dict[str, Callable] = {}
        self._shutdown_event = asyncio.Event()
    
    def register_tool(self, name: str, tool_func: Callable):
        """Register a tool that can be executed by the orchestrator."""
        self.tool_registry[name] = tool_func
    
    async def process_intent(self, intent: Intent) -> ActionResult:
        """
        Process an intent through the full pipeline:
        Intent -> Policy -> Approval -> Execute -> Audit
        """
        # Check if system is paused
        if self.pause_controller.is_paused():
            self.pause_controller.add_paused_task(intent.intent_id)
            await self.audit_logger.log_event(
                AuditEvent(
                    event_type=EventType.SYSTEM_PAUSED,
                    description=f"Intent {intent.intent_id} queued due to system pause",
                    user_id=intent.user_id,
                    metadata={"intent_id": intent.intent_id, "pause_reason": self.pause_controller.get_pause_reason()}
                )
            )
            return ActionResult(
                success=False,
                message="System is paused. Intent queued for later execution.",
                data={"queued": True, "pause_reason": self.pause_controller.get_pause_reason()}
            )
        
        # Store active intent
        self.active_intents[intent.intent_id] = intent
        
        try:
            # Log intent received
            await self.audit_logger.log_event(
                AuditEvent(
                    event_type=EventType.INTENT_RECEIVED,
                    description=f"Received intent: {intent.description}",
                    user_id=intent.user_id,
                    metadata={"intent_id": intent.intent_id, "intent_type": intent.intent_type.value}
                )
            )
            
            # Policy evaluation
            policy_result = await self.policy_engine.evaluate_intent(intent)
            if not policy_result.allowed:
                await self.audit_logger.log_event(
                    AuditEvent(
                        event_type=EventType.POLICY_DENIED,
                        description=f"Intent denied by policy: {policy_result.reason}",
                        user_id=intent.user_id,
                        metadata={"intent_id": intent.intent_id, "policy_reason": policy_result.reason}
                    )
                )
                return ActionResult(
                    success=False,
                    message=f"Intent denied by policy: {policy_result.reason}",
                    error="POLICY_DENIED"
                )
            
            # Check if approval is required
            if policy_result.requires_approval:
                await self.audit_logger.log_event(
                    AuditEvent(
                        event_type=EventType.APPROVAL_REQUIRED,
                        description=f"Intent requires approval: {policy_result.approval_method.value}",
                        user_id=intent.user_id,
                        metadata={"intent_id": intent.intent_id, "approval_method": policy_result.approval_method.value}
                    )
                )
                return ActionResult(
                    success=False,
                    message="Intent requires user approval",
                    data={
                        "requires_approval": True,
                        "approval_method": policy_result.approval_method.value,
                        "intent_id": intent.intent_id
                    }
                )
            
            # Execute the intent
            result = await self._execute_intent(intent)
            
            # Log execution result
            await self.audit_logger.log_event(
                AuditEvent(
                    event_type=EventType.ACTION_EXECUTED if result.success else EventType.ACTION_FAILED,
                    description=f"Intent execution: {result.message}",
                    user_id=intent.user_id,
                    metadata={
                        "intent_id": intent.intent_id,
                        "success": result.success,
                        "error": result.error
                    }
                )
            )
            
            return result
            
        except Exception as e:
            # Log unexpected error
            await self.audit_logger.log_event(
                AuditEvent(
                    event_type=EventType.SYSTEM_ERROR,
                    description=f"Unexpected error processing intent: {str(e)}",
                    user_id=intent.user_id,
                    metadata={"intent_id": intent.intent_id, "error": str(e)}
                )
            )
            return ActionResult(
                success=False,
                message=f"Unexpected error: {str(e)}",
                error="SYSTEM_ERROR"
            )
        finally:
            # Clean up active intent
            self.active_intents.pop(intent.intent_id, None)
    
    async def _execute_intent(self, intent: Intent) -> ActionResult:
        """Execute the intent by routing to appropriate tool."""
        start_time = datetime.utcnow()
        
        try:
            # Route to appropriate tool based on intent type and parameters
            tool_name = intent.parameters.get("tool")
            if not tool_name:
                return ActionResult(
                    success=False,
                    message="No tool specified in intent parameters",
                    error="MISSING_TOOL"
                )
            
            if tool_name not in self.tool_registry:
                return ActionResult(
                    success=False,
                    message=f"Tool '{tool_name}' not found",
                    error="TOOL_NOT_FOUND"
                )
            
            # Execute the tool
            tool_func = self.tool_registry[tool_name]
            result_data = await tool_func(intent.parameters)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ActionResult(
                success=True,
                message="Intent executed successfully",
                data=result_data,
                execution_time_ms=int(execution_time)
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return ActionResult(
                success=False,
                message=f"Tool execution failed: {str(e)}",
                error=str(e),
                execution_time_ms=int(execution_time)
            )
    
    async def approve_intent(self, intent_id: str, approver_id: str) -> ActionResult:
        """Approve a pending intent that requires approval."""
        if intent_id not in self.active_intents:
            return ActionResult(
                success=False,
                message="Intent not found or expired",
                error="INTENT_NOT_FOUND"
            )
        
        intent = self.active_intents[intent_id]
        
        await self.audit_logger.log_event(
            AuditEvent(
                event_type=EventType.APPROVAL_GRANTED,
                description=f"Intent approved by {approver_id}",
                user_id=approver_id,
                metadata={"intent_id": intent_id, "original_user": intent.user_id}
            )
        )
        
        # Execute the approved intent
        return await self._execute_intent(intent)
    
    def pause_system(self, reason: str = "User requested pause") -> bool:
        """Pause all automated operations."""
        return self.pause_controller.pause(reason)
    
    def resume_system(self) -> bool:
        """Resume all paused operations."""
        return self.pause_controller.resume()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            "paused": self.pause_controller.is_paused(),
            "pause_reason": self.pause_controller.get_pause_reason(),
            "paused_tasks": self.pause_controller.get_paused_tasks(),
            "active_intents": len(self.active_intents),
            "registered_tools": list(self.tool_registry.keys())
        }
    
    async def shutdown(self):
        """Gracefully shutdown the orchestrator."""
        self._shutdown_event.set()
        
        # Cancel all active intents
        for intent_id in list(self.active_intents.keys()):
            await self.audit_logger.log_event(
                AuditEvent(
                    event_type=EventType.SYSTEM_SHUTDOWN,
                    description=f"Intent cancelled due to shutdown: {intent_id}",
                    user_id="system",
                    metadata={"intent_id": intent_id}
                )
            )
        
        self.active_intents.clear()
