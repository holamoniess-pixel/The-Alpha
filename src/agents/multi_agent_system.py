#!/usr/bin/env python3
"""
ALPHA OMEGA - MULTI-AGENT ORCHESTRATION SYSTEM
Spawn specialized sub-agents for complex tasks
Version: 2.0.0
"""

import asyncio
import json
import logging
import time
import uuid
import threading
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from collections import defaultdict
import queue


class AgentRole(Enum):
    ORCHESTRATOR = "orchestrator"
    RESEARCHER = "researcher"
    CODER = "coder"
    ANALYZER = "analyzer"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"
    PLANNER = "planner"
    COMMUNICATOR = "communicator"
    SPECIALIST = "specialist"
    WORKER = "worker"


class AgentStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentTask:
    id: str
    name: str
    description: str
    assigned_agent: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: List[str] = field(default_factory=list)
    result: Any = None
    error: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: float = 0
    completed_at: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "assigned_agent": self.assigned_agent,
            "status": self.status.value,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }


@dataclass
class AgentMessage:
    id: str
    sender_id: str
    receiver_id: str
    message_type: str
    content: Any
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Agent:
    id: str
    name: str
    role: AgentRole
    capabilities: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "current_task": self.current_task,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "created_at": self.created_at,
            "last_active": self.last_active,
        }


class AgentCommunication:
    """Inter-agent communication system"""

    def __init__(self):
        self._message_queues: Dict[str, asyncio.Queue] = {}
        self._broadcast_subscribers: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.Lock()

    def register_agent(self, agent_id: str):
        """Register an agent for communication"""
        with self._lock:
            if agent_id not in self._message_queues:
                self._message_queues[agent_id] = asyncio.Queue()

    def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        with self._lock:
            if agent_id in self._message_queues:
                del self._message_queues[agent_id]

    async def send_message(
        self,
        sender_id: str,
        receiver_id: str,
        message_type: str,
        content: Any,
    ) -> str:
        """Send a message to another agent"""
        message = AgentMessage(
            id=str(uuid.uuid4())[:8],
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=message_type,
            content=content,
        )

        if receiver_id in self._message_queues:
            await self._message_queues[receiver_id].put(message)

        return message.id

    async def broadcast(
        self,
        sender_id: str,
        message_type: str,
        content: Any,
        exclude_self: bool = True,
    ) -> List[str]:
        """Broadcast message to all agents"""
        message_ids = []

        for agent_id in self._message_queues:
            if exclude_self and agent_id == sender_id:
                continue

            message_id = await self.send_message(
                sender_id, agent_id, message_type, content
            )
            message_ids.append(message_id)

        return message_ids

    async def receive_message(
        self,
        agent_id: str,
        timeout: float = 1.0,
    ) -> Optional[AgentMessage]:
        """Receive a message"""
        if agent_id not in self._message_queues:
            return None

        try:
            message = await asyncio.wait_for(
                self._message_queues[agent_id].get(), timeout=timeout
            )
            return message
        except asyncio.TimeoutError:
            return None

    def get_queue_size(self, agent_id: str) -> int:
        """Get pending messages for an agent"""
        if agent_id in self._message_queues:
            return self._message_queues[agent_id].qsize()
        return 0


class AgentWorker:
    """Worker that executes tasks for an agent"""

    def __init__(
        self,
        agent: Agent,
        communication: AgentCommunication,
        task_executor: Callable,
    ):
        self.agent = agent
        self.communication = communication
        self.task_executor = task_executor
        self.logger = logging.getLogger(f"AgentWorker-{agent.name}")

        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the agent worker"""
        self._running = True
        self.communication.register_agent(self.agent.id)
        self._task = asyncio.create_task(self._run_loop())
        self.logger.info(f"Agent {self.agent.name} started")

    async def stop(self):
        """Stop the agent worker"""
        self._running = False
        self.communication.unregister_agent(self.agent.id)
        if self._task:
            self._task.cancel()
        self.logger.info(f"Agent {self.agent.name} stopped")

    async def _run_loop(self):
        """Main agent loop"""
        while self._running:
            try:
                message = await self.communication.receive_message(
                    self.agent.id, timeout=1.0
                )

                if message:
                    await self._handle_message(message)

                if self.agent.status == AgentStatus.IDLE:
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in agent loop: {e}")
                await asyncio.sleep(1.0)

    async def _handle_message(self, message: AgentMessage):
        """Handle incoming message"""
        self.agent.last_active = time.time()

        if message.message_type == "task_assign":
            await self._execute_task(message.content)

        elif message.message_type == "task_cancel":
            self.agent.status = AgentStatus.IDLE
            self.agent.current_task = None

        elif message.message_type == "status_request":
            await self.communication.send_message(
                self.agent.id,
                message.sender_id,
                "status_response",
                self.agent.to_dict(),
            )

        elif message.message_type == "ping":
            await self.communication.send_message(
                self.agent.id,
                message.sender_id,
                "pong",
                {"timestamp": time.time()},
            )

    async def _execute_task(self, task_data: Dict[str, Any]):
        """Execute a task"""
        task_id = task_data.get("task_id")
        task_description = task_data.get("description", "")

        self.agent.status = AgentStatus.WORKING
        self.agent.current_task = task_id

        try:
            self.logger.info(f"Executing task: {task_id}")

            result = await self.task_executor(
                task_description,
                task_data.get("context", {}),
            )

            self.agent.tasks_completed += 1
            self.agent.status = AgentStatus.IDLE
            self.agent.current_task = None

            await self.communication.send_message(
                self.agent.id,
                "orchestrator",
                "task_complete",
                {"task_id": task_id, "result": result},
            )

        except Exception as e:
            self.logger.error(f"Task failed: {e}")
            self.agent.tasks_failed += 1
            self.agent.status = AgentStatus.IDLE
            self.agent.current_task = None

            await self.communication.send_message(
                self.agent.id,
                "orchestrator",
                "task_failed",
                {"task_id": task_id, "error": str(e)},
            )


class MultiAgentOrchestrator:
    """Orchestrator for multi-agent system"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("MultiAgentOrchestrator")

        self.communication = AgentCommunication()
        self.agents: Dict[str, Agent] = {}
        self.workers: Dict[str, AgentWorker] = {}
        self.tasks: Dict[str, AgentTask] = {}

        self._running = False
        self._orchestrator_task: Optional[asyncio.Task] = None

        self._stats = {
            "tasks_created": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "messages_sent": 0,
        }

    async def initialize(self) -> bool:
        """Initialize the orchestrator"""
        self.logger.info("Initializing Multi-Agent Orchestrator...")

        self._running = True
        self._orchestrator_task = asyncio.create_task(self._orchestrator_loop())

        self.logger.info("Multi-Agent Orchestrator initialized")
        return True

    async def shutdown(self):
        """Shutdown the orchestrator"""
        self._running = False

        for worker in self.workers.values():
            await worker.stop()

        if self._orchestrator_task:
            self._orchestrator_task.cancel()

        self.logger.info("Multi-Agent Orchestrator shutdown")

    async def _orchestrator_loop(self):
        """Main orchestrator loop"""
        while self._running:
            try:
                message = await self.communication.receive_message(
                    "orchestrator", timeout=1.0
                )

                if message:
                    await self._handle_message(message)

                await self._assign_pending_tasks()

                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Orchestrator error: {e}")
                await asyncio.sleep(1.0)

    async def _handle_message(self, message: AgentMessage):
        """Handle messages from agents"""
        if message.message_type == "task_complete":
            task_id = message.content.get("task_id")
            result = message.content.get("result")

            if task_id in self.tasks:
                self.tasks[task_id].result = result
                self.tasks[task_id].status = TaskStatus.COMPLETED
                self.tasks[task_id].completed_at = time.time()
                self._stats["tasks_completed"] += 1

                self.logger.info(f"Task {task_id} completed")

        elif message.message_type == "task_failed":
            task_id = message.content.get("task_id")
            error = message.content.get("error")

            if task_id in self.tasks:
                self.tasks[task_id].error = error
                self.tasks[task_id].status = TaskStatus.FAILED
                self._stats["tasks_failed"] += 1

                self.logger.error(f"Task {task_id} failed: {error}")

    async def _assign_pending_tasks(self):
        """Assign pending tasks to available agents"""
        for task_id, task in self.tasks.items():
            if task.status != TaskStatus.PENDING:
                continue

            if task.dependencies:
                deps_met = all(
                    self.tasks.get(dep, AgentTask("", "", "")).status
                    == TaskStatus.COMPLETED
                    for dep in task.dependencies
                )
                if not deps_met:
                    continue

            available_agents = [
                agent
                for agent in self.agents.values()
                if agent.status == AgentStatus.IDLE
                and self._agent_can_handle(agent, task)
            ]

            if available_agents:
                agent = self._select_best_agent(available_agents, task)
                await self._assign_task(agent, task)

    def _agent_can_handle(self, agent: Agent, task: AgentTask) -> bool:
        """Check if agent can handle the task"""
        required = task.metadata.get("required_capabilities", [])
        return all(cap in agent.capabilities for cap in required)

    def _select_best_agent(self, agents: List[Agent], task: AgentTask) -> Agent:
        """Select the best agent for a task"""
        agents.sort(key=lambda a: (-a.tasks_completed, a.tasks_failed, a.last_active))
        return agents[0]

    async def _assign_task(self, agent: Agent, task: AgentTask):
        """Assign a task to an agent"""
        task.status = TaskStatus.ASSIGNED
        task.assigned_agent = agent.id
        task.started_at = time.time()

        agent.status = AgentStatus.WORKING
        agent.current_task = task.id

        await self.communication.send_message(
            "orchestrator",
            agent.id,
            "task_assign",
            task.to_dict(),
        )

        self.logger.info(f"Assigned task {task.id} to agent {agent.name}")

    def create_agent(
        self,
        name: str,
        role: AgentRole,
        capabilities: List[str] = None,
        task_executor: Callable = None,
    ) -> Agent:
        """Create a new agent"""
        agent_id = str(uuid.uuid4())[:8]

        agent = Agent(
            id=agent_id,
            name=name,
            role=role,
            capabilities=capabilities or [],
        )

        self.agents[agent_id] = agent

        async def default_executor(description: str, context: Dict) -> Any:
            self.logger.info(f"Agent {name} executing: {description}")
            await asyncio.sleep(1.0)
            return {"status": "completed", "description": description}

        worker = AgentWorker(
            agent,
            self.communication,
            task_executor or default_executor,
        )

        self.workers[agent_id] = worker

        self.logger.info(f"Created agent: {name} ({role.value})")
        return agent

    async def start_agent(self, agent_id: str):
        """Start an agent"""
        if agent_id in self.workers:
            await self.workers[agent_id].start()

    async def stop_agent(self, agent_id: str):
        """Stop an agent"""
        if agent_id in self.workers:
            await self.workers[agent_id].stop()

    async def start_all_agents(self):
        """Start all agents"""
        for agent_id in self.workers:
            await self.start_agent(agent_id)

    def create_task(
        self,
        name: str,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        dependencies: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> AgentTask:
        """Create a new task"""
        task_id = str(uuid.uuid4())[:8]

        task = AgentTask(
            id=task_id,
            name=name,
            description=description,
            priority=priority,
            dependencies=dependencies or [],
            metadata=metadata or {},
        )

        self.tasks[task_id] = task
        self._stats["tasks_created"] += 1

        self.logger.info(f"Created task: {name}")
        return task

    async def wait_for_task(
        self,
        task_id: str,
        timeout: float = 300.0,
    ) -> AgentTask:
        """Wait for a task to complete"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    return task
            await asyncio.sleep(0.5)

        raise asyncio.TimeoutError(f"Task {task_id} did not complete in time")

    async def execute_workflow(
        self,
        tasks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute a workflow of tasks"""
        created_tasks = []

        for task_def in tasks:
            task = self.create_task(
                name=task_def["name"],
                description=task_def["description"],
                priority=TaskPriority(task_def.get("priority", 2)),
                dependencies=task_def.get("dependencies", []),
                metadata=task_def.get("metadata", {}),
            )
            created_tasks.append(task)

        results = {}
        for task in created_tasks:
            try:
                completed = await self.wait_for_task(task.id)
                results[task.id] = {
                    "status": completed.status.value,
                    "result": completed.result,
                    "error": completed.error,
                }
            except asyncio.TimeoutError:
                results[task.id] = {
                    "status": "timeout",
                    "error": "Task timed out",
                }

        return results

    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an agent"""
        if agent_id in self.agents:
            return self.agents[agent_id].to_dict()
        return None

    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Get all agents"""
        return [agent.to_dict() for agent in self.agents.values()]

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task"""
        if task_id in self.tasks:
            return self.tasks[task_id].to_dict()
        return None

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks"""
        return [task.to_dict() for task in self.tasks.values()]

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        return {
            **self._stats,
            "agents": len(self.agents),
            "active_agents": sum(
                1 for a in self.agents.values() if a.status == AgentStatus.WORKING
            ),
            "pending_tasks": sum(
                1 for t in self.tasks.values() if t.status == TaskStatus.PENDING
            ),
            "active_tasks": sum(
                1 for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS
            ),
        }

    async def broadcast_to_agents(
        self,
        message_type: str,
        content: Any,
    ):
        """Broadcast message to all agents"""
        await self.communication.broadcast(
            "orchestrator",
            message_type,
            content,
        )

    async def create_swarm(
        self,
        task_description: str,
        num_agents: int = 3,
        consensus_threshold: float = 0.7,
    ) -> Dict[str, Any]:
        """Create a swarm of agents for a task with consensus voting"""
        agents = []
        results = []

        for i in range(num_agents):
            agent = self.create_agent(
                name=f"swarm_agent_{i}",
                role=AgentRole.WORKER,
                capabilities=["research", "analyze"],
            )
            await self.start_agent(agent.id)
            agents.append(agent)

        for agent in agents:
            task = self.create_task(
                name=f"swarm_task_{agent.id}",
                description=task_description,
                priority=TaskPriority.HIGH,
            )
            await self._assign_task(agent, task)

        for agent in agents:
            try:
                completed = await self.wait_for_task(agent.current_task)
                results.append(completed.result)
            except:
                results.append(None)

        if results:
            result_counts = {}
            for result in results:
                if result:
                    key = json.dumps(result, sort_keys=True)
                    result_counts[key] = result_counts.get(key, 0) + 1

            if result_counts:
                best_result_key = max(result_counts, key=result_counts.get)
                best_count = result_counts[best_result_key]

                if best_count / num_agents >= consensus_threshold:
                    return {
                        "consensus": True,
                        "result": json.loads(best_result_key),
                        "agreement": best_count / num_agents,
                    }

        return {
            "consensus": False,
            "results": results,
            "agreement": 0,
        }


class SpecializedAgents:
    """Factory for creating specialized agents"""

    @staticmethod
    def create_research_agent() -> Dict[str, Any]:
        return {
            "name": "researcher",
            "role": AgentRole.RESEARCHER,
            "capabilities": ["web_search", "summarize", "analyze"],
        }

    @staticmethod
    def create_coder_agent() -> Dict[str, Any]:
        return {
            "name": "coder",
            "role": AgentRole.CODER,
            "capabilities": ["write_code", "debug", "test", "refactor"],
        }

    @staticmethod
    def create_analyzer_agent() -> Dict[str, Any]:
        return {
            "name": "analyzer",
            "role": AgentRole.ANALYZER,
            "capabilities": ["analyze", "report", "visualize"],
        }

    @staticmethod
    def create_executor_agent() -> Dict[str, Any]:
        return {
            "name": "executor",
            "role": AgentRole.EXECUTOR,
            "capabilities": ["execute", "monitor", "report"],
        }

    @staticmethod
    def create_reviewer_agent() -> Dict[str, Any]:
        return {
            "name": "reviewer",
            "role": AgentRole.REVIEWER,
            "capabilities": ["review", "validate", "approve"],
        }
