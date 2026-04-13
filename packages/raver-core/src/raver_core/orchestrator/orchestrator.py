"""Core orchestrator for RAVER system."""

import asyncio
from typing import Dict, List, Optional, Any
from uuid import UUID

from raver_shared.schemas import Intent, PolicyDecision, Status, SystemPause
from ..policy.engine import PolicyEngine
from ..audit.logger import AuditLogger


class CoreOrchestrator:
    """Main orchestrator for RAVER system."""
    
    def __init__(self):
        self.policy_engine = PolicyEngine()
        self.audit_logger = AuditLogger()
        self.active_intents: Dict[UUID, Intent] = {}
        self.system_paused: bool = False
        self.pause_context: Optional[SystemPause] = None
        
    async def process_intent(self, intent: Intent) -> PolicyDecision:
        """Process user intent through policy engine."""
        # Store active intent
        self.active_intents[intent.intent_id] = intent
        
        # Log intent received
        await self.audit_logger.log_event(
            event_type="intent_received",
            source="orchestrator",
            action="process_intent",
            result="received",
            user_id=intent.user_id,
            intent_id=intent.intent_id
        )
        
        # Check for system pause
        if intent.command.lower() in ["pause", "stop", "halt"]:
            return await self._handle_system_pause(intent)
        
        # Evaluate against policy
        decision = self.policy_engine.evaluate_intent(intent)
        
        # Log decision
        await self.audit_logger.log_event(
            event_type="policy_decision",
            source="orchestrator",
            action="evaluate_intent",
            result="approved" if decision.approved else "rejected",
            user_id=intent.user_id,
            intent_id=intent.intent_id,
            details={
                "risk_score": decision.risk_score,
                "risk_level": decision.risk_level,
                "approval_method": decision.approval_method
            }
        )
        
        return decision
    
    async def _handle_system_pause(self, intent: Intent) -> PolicyDecision:
        """Handle system pause command."""
        self.system_paused = True
        self.pause_context = SystemPause(
            user_id=intent.user_id,
            reason="User requested pause"
        )
        
        await self.audit_logger.log_event(
            event_type="system_pause",
            source="orchestrator",
            action="pause_system",
            result="paused",
            user_id=intent.user_id
        )
        
        return PolicyDecision(
            intent_id=intent.intent_id,
            risk_score=0.0,
            risk_level="low",
            approved=True,
            reason="System paused by user request"
        )
    
    async def resume_system(self, user_id: UUID) -> bool:
        """Resume system from pause."""
        if not self.system_paused:
            return False
        
        self.system_paused = False
        if self.pause_context:
            self.pause_context.resumed_at = None
        
        await self.audit_logger.log_event(
            event_type="system_resume",
            source="orchestrator",
            action="resume_system",
            result="resumed",
            user_id=user_id
        )
        
        return True
    
    def is_system_paused(self) -> bool:
        """Check if system is paused."""
        return self.system_paused
