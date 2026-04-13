#!/usr/bin/env python3
"""
ALPHA OMEGA - WORKFLOW RECORDING & PLAYBACK
Record complex workflows as single commands
Version: 2.0.0
"""

import asyncio
import json
import logging
import time
import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading


class WorkflowStatus(Enum):
    DRAFT = "draft"
    RECORDING = "recording"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class StepType(Enum):
    ACTION = "action"
    WAIT = "wait"
    CONDITION = "condition"
    LOOP = "loop"
    BRANCH = "branch"
    VARIABLE = "variable"
    COMMENT = "comment"


@dataclass
class WorkflowStep:
    id: str
    step_type: StepType
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    delay_ms: int = 0
    retry_count: int = 0
    retry_delay_ms: int = 1000
    on_failure: str = "stop"  # stop, skip, retry
    enabled: bool = True
    order: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "step_type": self.step_type.value,
            "action": self.action,
            "parameters": self.parameters,
            "conditions": self.conditions,
            "delay_ms": self.delay_ms,
            "retry_count": self.retry_count,
            "retry_delay_ms": self.retry_delay_ms,
            "on_failure": self.on_failure,
            "enabled": self.enabled,
            "order": self.order,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowStep":
        return cls(
            id=data["id"],
            step_type=StepType(data["step_type"]),
            action=data["action"],
            parameters=data.get("parameters", {}),
            conditions=data.get("conditions", []),
            delay_ms=data.get("delay_ms", 0),
            retry_count=data.get("retry_count", 0),
            retry_delay_ms=data.get("retry_delay_ms", 1000),
            on_failure=data.get("on_failure", "stop"),
            enabled=data.get("enabled", True),
            order=data.get("order", 0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Workflow:
    id: str
    name: str
    description: str
    steps: List[WorkflowStep] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    triggers: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_run: float = 0
    run_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    avg_duration_ms: float = 0
    author: str = "system"
    version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "variables": self.variables,
            "triggers": self.triggers,
            "tags": self.tags,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_run": self.last_run,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "avg_duration_ms": self.avg_duration_ms,
            "author": self.author,
            "version": self.version,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workflow":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            steps=[WorkflowStep.from_dict(s) for s in data.get("steps", [])],
            variables=data.get("variables", {}),
            triggers=data.get("triggers", []),
            tags=data.get("tags", []),
            status=WorkflowStatus(data.get("status", "draft")),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            last_run=data.get("last_run", 0),
            run_count=data.get("run_count", 0),
            success_count=data.get("success_count", 0),
            fail_count=data.get("fail_count", 0),
            avg_duration_ms=data.get("avg_duration_ms", 0),
            author=data.get("author", "system"),
            version=data.get("version", "1.0"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class WorkflowExecution:
    id: str
    workflow_id: str
    status: WorkflowStatus
    current_step: int = 0
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "current_step": self.current_step,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "results": self.results,
            "errors": self.errors,
            "variables": self.variables,
        }


class WorkflowRecorder:
    """Records user actions as workflows"""
    
    def __init__(self):
        self.logger = logging.getLogger("WorkflowRecorder")
        
        self._recording = False
        self._current_workflow: Optional[Workflow] = None
        self._recorded_steps: List[Dict[str, Any]] = []
        self._start_time: float = 0
        self._last_action_time: float = 0
    
    def start_recording(self, name: str, description: str = "") -> str:
        """Start recording a new workflow"""
        if self._recording:
            self.logger.warning("Already recording")
            return ""
        
        workflow_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:12]
        
        self._current_workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            status=WorkflowStatus.RECORDING,
        )
        
        self._recording = True
        self._recorded_steps = []
        self._start_time = time.time()
        self._last_action_time = self._start_time
        
        self.logger.info(f"Started recording workflow: {name}")
        return workflow_id
    
    def record_action(
        self,
        action: str,
        parameters: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
    ):
        """Record an action during recording"""
        if not self._recording:
            return
        
        current_time = time.time()
        delay_ms = int((current_time - self._last_action_time) * 1000)
        
        step_id = hashlib.md5(f"{action}{current_time}".encode()).hexdigest()[:8]
        
        step_data = {
            "id": step_id,
            "step_type": StepType.ACTION.value,
            "action": action,
            "parameters": parameters or {},
            "delay_ms": delay_ms,
            "metadata": metadata or {},
            "timestamp": current_time,
        }
        
        self._recorded_steps.append(step_data)
        self._last_action_time = current_time
        
        self.logger.debug(f"Recorded action: {action}")
    
    def record_wait(self, duration_ms: int, condition: Dict[str, Any] = None):
        """Record a wait step"""
        if not self._recording:
            return
        
        step_id = hashlib.md5(f"wait{time.time()}".encode()).hexdigest()[:8]
        
        step_data = {
            "id": step_id,
            "step_type": StepType.WAIT.value,
            "action": "wait",
            "parameters": {"duration_ms": duration_ms},
            "delay_ms": 0,
            "metadata": {"condition": condition} if condition else {},
        }
        
        self._recorded_steps.append(step_data)
        self.logger.debug(f"Recorded wait: {duration_ms}ms")
    
    def add_comment(self, comment: str):
        """Add a comment to the recording"""
        if not self._recording:
            return
        
        step_id = hashlib.md5(f"comment{time.time()}".encode()).hexdigest()[:8]
        
        step_data = {
            "id": step_id,
            "step_type": StepType.COMMENT.value,
            "action": "comment",
            "parameters": {"text": comment},
            "delay_ms": 0,
        }
        
        self._recorded_steps.append(step_data)
    
    def stop_recording(self) -> Optional[Workflow]:
        """Stop recording and return the workflow"""
        if not self._recording:
            return None
        
        self._recording = False
        
        if self._current_workflow:
            steps = []
            for i, step_data in enumerate(self._recorded_steps):
                step = WorkflowStep(
                    id=step_data["id"],
                    step_type=StepType(step_data["step_type"]),
                    action=step_data["action"],
                    parameters=step_data.get("parameters", {}),
                    delay_ms=step_data.get("delay_ms", 0),
                    order=i,
                    metadata=step_data.get("metadata", {}),
                )
                steps.append(step)
            
            self._current_workflow.steps = steps
            self._current_workflow.status = WorkflowStatus.READY
            self._current_workflow.updated_at = time.time()
        
        self.logger.info(f"Stopped recording. Steps: {len(self._recorded_steps)}")
        return self._current_workflow
    
    def cancel_recording(self):
        """Cancel current recording"""
        self._recording = False
        self._current_workflow = None
        self._recorded_steps = []
        self.logger.info("Recording cancelled")
    
    def is_recording(self) -> bool:
        """Check if recording"""
        return self._recording
    
    def get_current_workflow(self) -> Optional[Workflow]:
        """Get current workflow being recorded"""
        return self._current_workflow


class WorkflowRunner:
    """Runs workflows"""
    
    def __init__(
        self,
        action_executor: Callable[[str, Dict[str, Any]], Awaitable[Any]] = None,
    ):
        self.logger = logging.getLogger("WorkflowRunner")
        self.action_executor = action_executor
        
        self._running_executions: Dict[str, WorkflowExecution] = {}
        self._paused_executions: Set[str] = set()
        self._stop_requested: Set[str] = set()
    
    async def run_workflow(
        self,
        workflow: Workflow,
        variables: Dict[str, Any] = None,
        step_callback: Callable[[int, Dict[str, Any]], Awaitable[None]] = None,
    ) -> WorkflowExecution:
        """Run a workflow"""
        execution_id = hashlib.md5(f"{workflow.id}{time.time()}".encode()).hexdigest()[:12]
        
        execution = WorkflowExecution(
            id=execution_id,
            workflow_id=workflow.id,
            status=WorkflowStatus.RUNNING,
            variables={**workflow.variables, **(variables or {})},
        )
        
        self._running_executions[execution_id] = execution
        
        self.logger.info(f"Starting workflow: {workflow.name} ({execution_id})")
        
        try:
            sorted_steps = sorted(workflow.steps, key=lambda s: s.order)
            
            for i, step in enumerate(sorted_steps):
                if execution_id in self._stop_requested:
                    execution.status = WorkflowStatus.FAILED
                    execution.errors.append("Workflow stopped by user")
                    break
                
                while execution_id in self._paused_executions:
                    await asyncio.sleep(0.5)
                
                if not step.enabled:
                    continue
                
                execution.current_step = i
                
                if step.delay_ms > 0:
                    await asyncio.sleep(step.delay_ms / 1000)
                
                result = await self._execute_step(step, execution, workflow)
                
                execution.results.append(result)
                
                if step_callback:
                    await step_callback(i, result)
                
                if not result.get("success", False):
                    if step.on_failure == "stop":
                        execution.status = WorkflowStatus.FAILED
                        execution.errors.append(result.get("error", "Step failed"))
                        break
                    elif step.on_failure == "skip":
                        continue
                    elif step.on_failure == "retry" and step.retry_count > 0:
                        for retry in range(step.retry_count):
                            await asyncio.sleep(step.retry_delay_ms / 1000)
                            result = await self._execute_step(step, execution, workflow)
                            if result.get("success", False):
                                break
            
            if execution.status == WorkflowStatus.RUNNING:
                execution.status = WorkflowStatus.COMPLETED
            
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.errors.append(str(e))
            self.logger.error(f"Workflow error: {e}")
        
        finally:
            execution.completed_at = time.time()
            if execution_id in self._running_executions:
                del self._running_executions[execution_id]
        
        self.logger.info(f"Workflow {execution_id} {execution.status.value}")
        return execution
    
    async def _execute_step(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
        workflow: Workflow,
    ) -> Dict[str, Any]:
        """Execute a single step"""
        result = {
            "step_id": step.id,
            "action": step.action,
            "success": False,
            "error": "",
            "output": None,
        }
        
        try:
            if step.step_type == StepType.ACTION:
                if self.action_executor:
                    params = self._resolve_variables(step.parameters, execution.variables)
                    output = await self.action_executor(step.action, params)
                    result["success"] = True
                    result["output"] = output
                else:
                    result["success"] = True
                    result["output"] = {"message": f"Executed: {step.action}"}
            
            elif step.step_type == StepType.WAIT:
                duration = step.parameters.get("duration_ms", 1000)
                await asyncio.sleep(duration / 1000)
                result["success"] = True
            
            elif step.step_type == StepType.VARIABLE:
                var_name = step.parameters.get("name")
                var_value = step.parameters.get("value")
                if var_name:
                    execution.variables[var_name] = var_value
                result["success"] = True
            
            elif step.step_type == StepType.CONDITION:
                condition_met = self._evaluate_condition(
                    step.conditions,
                    execution.variables
                )
                result["success"] = True
                result["output"] = {"condition_met": condition_met}
            
            elif step.step_type == StepType.COMMENT:
                result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
            self.logger.error(f"Step error: {e}")
        
        return result
    
    def _resolve_variables(
        self,
        params: Dict[str, Any],
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Resolve variable references in parameters"""
        resolved = {}
        
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                resolved[key] = variables.get(var_name, value)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_variables(value, variables)
            else:
                resolved[key] = value
        
        return resolved
    
    def _evaluate_condition(
        self,
        conditions: List[Dict[str, Any]],
        variables: Dict[str, Any],
    ) -> bool:
        """Evaluate conditions"""
        for condition in conditions:
            var_name = condition.get("variable")
            operator = condition.get("operator", "==")
            expected = condition.get("value")
            
            actual = variables.get(var_name)
            
            if operator == "==":
                if actual != expected:
                    return False
            elif operator == "!=":
                if actual == expected:
                    return False
            elif operator == ">":
                if not (actual > expected):
                    return False
            elif operator == "<":
                if not (actual < expected):
                    return False
            elif operator == "contains":
                if expected not in str(actual):
                    return False
        
        return True
    
    def pause_execution(self, execution_id: str):
        """Pause a running execution"""
        self._paused_executions.add(execution_id)
        self.logger.info(f"Paused execution: {execution_id}")
    
    def resume_execution(self, execution_id: str):
        """Resume a paused execution"""
        self._paused_executions.discard(execution_id)
        self.logger.info(f"Resumed execution: {execution_id}")
    
    def stop_execution(self, execution_id: str):
        """Stop a running execution"""
        self._stop_requested.add(execution_id)
        self.logger.info(f"Stop requested for: {execution_id}")
    
    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get execution by ID"""
        return self._running_executions.get(execution_id)


class WorkflowManager:
    """Manages workflows with persistence"""
    
    def __init__(self, db_path: str = "data/workflows.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("WorkflowManager")
        
        self.recorder = WorkflowRecorder()
        self.runner = WorkflowRunner()
        
        self._workflows: Dict[str, Workflow] = {}
        self._lock = threading.RLock()
        
        self._init_db()
    
    def _init_db(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    data TEXT NOT NULL,
                    created_at REAL,
                    updated_at REAL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT,
                    status TEXT,
                    started_at REAL,
                    completed_at REAL,
                    results TEXT,
                    errors TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
                )
            """)
            
            conn.commit()
    
    async def initialize(self) -> bool:
        """Initialize the manager"""
        self._load_workflows()
        self.logger.info(f"WorkflowManager initialized. Loaded {len(self._workflows)} workflows")
        return True
    
    def _load_workflows(self):
        """Load workflows from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT id, data FROM workflows")
                for row in cursor.fetchall():
                    workflow_data = json.loads(row[1])
                    workflow = Workflow.from_dict(workflow_data)
                    self._workflows[workflow.id] = workflow
        except Exception as e:
            self.logger.error(f"Error loading workflows: {e}")
    
    def _save_workflow(self, workflow: Workflow):
        """Save workflow to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO workflows (id, name, description, data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        workflow.id,
                        workflow.name,
                        workflow.description,
                        json.dumps(workflow.to_dict()),
                        workflow.created_at,
                        workflow.updated_at,
                    ),
                )
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error saving workflow: {e}")
    
    def create_workflow(
        self,
        name: str,
        description: str = "",
        steps: List[WorkflowStep] = None,
        variables: Dict[str, Any] = None,
        triggers: List[Dict[str, Any]] = None,
        tags: List[str] = None,
    ) -> Workflow:
        """Create a new workflow"""
        workflow_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:12]
        
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            steps=steps or [],
            variables=variables or {},
            triggers=triggers or [],
            tags=tags or [],
        )
        
        self._workflows[workflow_id] = workflow
        self._save_workflow(workflow)
        
        self.logger.info(f"Created workflow: {name}")
        return workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID"""
        return self._workflows.get(workflow_id)
    
    def get_workflow_by_name(self, name: str) -> Optional[Workflow]:
        """Get workflow by name"""
        for workflow in self._workflows.values():
            if workflow.name.lower() == name.lower():
                return workflow
        return None
    
    def list_workflows(
        self,
        tag: str = None,
        status: WorkflowStatus = None,
    ) -> List[Workflow]:
        """List workflows"""
        workflows = list(self._workflows.values())
        
        if tag:
            workflows = [w for w in workflows if tag in w.tags]
        
        if status:
            workflows = [w for w in workflows if w.status == status]
        
        return sorted(workflows, key=lambda w: w.updated_at, reverse=True)
    
    def update_workflow(self, workflow: Workflow) -> bool:
        """Update a workflow"""
        if workflow.id not in self._workflows:
            return False
        
        workflow.updated_at = time.time()
        self._workflows[workflow.id] = workflow
        self._save_workflow(workflow)
        
        self.logger.info(f"Updated workflow: {workflow.name}")
        return True
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow"""
        if workflow_id not in self._workflows:
            return False
        
        del self._workflows[workflow_id]
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error deleting workflow: {e}")
        
        self.logger.info(f"Deleted workflow: {workflow_id}")
        return True
    
    async def run_workflow(
        self,
        workflow_id: str,
        variables: Dict[str, Any] = None,
    ) -> WorkflowExecution:
        """Run a workflow by ID"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        execution = await self.runner.run_workflow(workflow, variables)
        
        workflow.last_run = time.time()
        workflow.run_count += 1
        
        if execution.status == WorkflowStatus.COMPLETED:
            workflow.success_count += 1
        else:
            workflow.fail_count += 1
        
        duration = execution.completed_at - execution.started_at
        if workflow.avg_duration_ms == 0:
            workflow.avg_duration_ms = duration * 1000
        else:
            workflow.avg_duration_ms = (workflow.avg_duration_ms + duration * 1000) / 2
        
        self._save_workflow(workflow)
        
        return execution
    
    async def run_workflow_by_name(
        self,
        name: str,
        variables: Dict[str, Any] = None,
    ) -> WorkflowExecution:
        """Run a workflow by name"""
        workflow = self.get_workflow_by_name(name)
        if not workflow:
            raise ValueError(f"Workflow not found: {name}")
        
        return await self.run_workflow(workflow.id, variables)
    
    def start_recording(self, name: str, description: str = "") -> str:
        """Start recording a workflow"""
        return self.recorder.start_recording(name, description)
    
    def record_action(self, action: str, parameters: Dict[str, Any] = None):
        """Record an action"""
        self.recorder.record_action(action, parameters)
    
    def stop_recording(self) -> Optional[Workflow]:
        """Stop recording and save workflow"""
        workflow = self.recorder.stop_recording()
        if workflow:
            self._workflows[workflow.id] = workflow
            self._save_workflow(workflow)
        return workflow
    
    def cancel_recording(self):
        """Cancel recording"""
        self.recorder.cancel_recording()
    
    def duplicate_workflow(self, workflow_id: str, new_name: str = None) -> Optional[Workflow]:
        """Duplicate a workflow"""
        original = self.get_workflow(workflow_id)
        if not original:
            return None
        
        new_workflow = Workflow(
            id=hashlib.md5(f"{new_name or original.name}{time.time()}".encode()).hexdigest()[:12],
            name=new_name or f"{original.name} (copy)",
            description=original.description,
            steps=[WorkflowStep.from_dict(s.to_dict()) for s in original.steps],
            variables=dict(original.variables),
            triggers=list(original.triggers),
            tags=list(original.tags),
        )
        
        self._workflows[new_workflow.id] = new_workflow
        self._save_workflow(new_workflow)
        
        return new_workflow
    
    def export_workflow(self, workflow_id: str) -> str:
        """Export workflow as JSON"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return ""
        
        return json.dumps(workflow.to_dict(), indent=2)
    
    def import_workflow(self, json_data: str) -> Optional[Workflow]:
        """Import workflow from JSON"""
        try:
            data = json.loads(json_data)
            workflow = Workflow.from_dict(data)
            
            workflow.id = hashlib.md5(f"{workflow.name}{time.time()}".encode()).hexdigest()[:12]
            
            self._workflows[workflow.id] = workflow
            self._save_workflow(workflow)
            
            return workflow
        except Exception as e:
            self.logger.error(f"Import error: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get workflow statistics"""
        total = len(self._workflows)
        
        return {
            "total_workflows": total,
            "ready_workflows": sum(1 for w in self._workflows.values() if w.status == WorkflowStatus.READY),
            "total_runs": sum(w.run_count for w in self._workflows.values()),
            "total_successes": sum(w.success_count for w in self._workflows.values()),
            "total_failures": sum(w.fail_count for w in self._workflows.values()),
        }
