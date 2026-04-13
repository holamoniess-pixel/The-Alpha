#!/usr/bin/env python3
"""
ALPHA OMEGA - AUTONOMOUS TASK SCHEDULING
Background task execution with conditions
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
from datetime import datetime, timedelta
from enum import Enum
import threading
import croniter


class ScheduleType(Enum):
    ONCE = "once"
    INTERVAL = "interval"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CRON = "cron"
    CONDITIONAL = "conditional"


class TaskStatus(Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TriggerType(Enum):
    TIME = "time"
    EVENT = "event"
    CONDITION = "condition"
    WEBHOOK = "webhook"
    FILE_CHANGE = "file_change"
    API_CALL = "api_call"


@dataclass
class ScheduleConfig:
    schedule_type: ScheduleType
    interval_seconds: int = 0
    cron_expression: str = ""
    specific_time: str = ""
    days_of_week: List[int] = field(default_factory=list)
    day_of_month: int = 0
    timezone: str = "UTC"


@dataclass
class Trigger:
    trigger_type: TriggerType
    condition: str = ""
    event_name: str = ""
    file_path: str = ""
    webhook_path: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduledTask:
    id: str
    name: str
    description: str
    action: str
    action_params: Dict[str, Any] = field(default_factory=dict)
    schedule: ScheduleConfig = None
    triggers: List[Trigger] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5
    max_retries: int = 3
    retry_delay_seconds: int = 60
    timeout_seconds: int = 300
    created_at: float = field(default_factory=time.time)
    next_run: float = 0
    last_run: float = 0
    last_result: Any = None
    run_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "action": self.action,
            "action_params": self.action_params,
            "schedule": {
                "type": self.schedule.schedule_type.value if self.schedule else None,
                "interval_seconds": self.schedule.interval_seconds
                if self.schedule
                else 0,
                "cron_expression": self.schedule.cron_expression
                if self.schedule
                else "",
            },
            "triggers": [
                {"type": t.trigger_type.value, "condition": t.condition}
                for t in self.triggers
            ],
            "status": self.status.value,
            "priority": self.priority,
            "next_run": self.next_run,
            "last_run": self.last_run,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "enabled": self.enabled,
        }


@dataclass
class TaskExecution:
    id: str
    task_id: str
    started_at: float
    completed_at: float = 0
    status: TaskStatus = TaskStatus.RUNNING
    result: Any = None
    error: str = ""
    duration_ms: float = 0


class TaskScheduler:
    """Autonomous task scheduler"""

    def __init__(self, db_path: str = "data/scheduled_tasks.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("TaskScheduler")

        self._tasks: Dict[str, ScheduledTask] = {}
        self._executions: Dict[str, TaskExecution] = {}
        self._action_handlers: Dict[str, Callable] = {}
        self._event_listeners: Dict[str, List[str]] = {}

        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._lock = threading.RLock()

        self._init_db()

    def _init_db(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id TEXT PRIMARY KEY,
                    task_id TEXT,
                    started_at REAL,
                    completed_at REAL,
                    status TEXT,
                    result TEXT,
                    error TEXT
                )
            """)
            conn.commit()

    async def initialize(self) -> bool:
        """Initialize scheduler"""
        self._load_tasks()
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

        self.logger.info("Task Scheduler initialized")
        return True

    def _load_tasks(self):
        """Load tasks from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id, data FROM tasks")
            for row in cursor.fetchall():
                task_data = json.loads(row[1])
                task = self._dict_to_task(task_data)
                self._tasks[task.id] = task

    def _dict_to_task(self, data: Dict[str, Any]) -> ScheduledTask:
        """Convert dict to ScheduledTask"""
        schedule_data = data.get("schedule", {})
        schedule = ScheduleConfig(
            schedule_type=ScheduleType(schedule_data.get("type", "once")),
            interval_seconds=schedule_data.get("interval_seconds", 0),
            cron_expression=schedule_data.get("cron_expression", ""),
        )

        triggers = []
        for t in data.get("triggers", []):
            triggers.append(
                Trigger(
                    trigger_type=TriggerType(t.get("type", "time")),
                    condition=t.get("condition", ""),
                    event_name=t.get("event_name", ""),
                )
            )

        return ScheduledTask(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            action=data["action"],
            action_params=data.get("action_params", {}),
            schedule=schedule,
            triggers=triggers,
            status=TaskStatus(data.get("status", "pending")),
            priority=data.get("priority", 5),
            next_run=data.get("next_run", 0),
            last_run=data.get("last_run", 0),
            run_count=data.get("run_count", 0),
            success_count=data.get("success_count", 0),
            fail_count=data.get("fail_count", 0),
            enabled=data.get("enabled", True),
        )

    async def shutdown(self):
        """Shutdown scheduler"""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
        self.logger.info("Task Scheduler shutdown")

    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self._running:
            try:
                await self._check_and_execute_tasks()
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(5)

    async def _check_and_execute_tasks(self):
        """Check and execute due tasks"""
        current_time = time.time()

        for task in self._tasks.values():
            if not task.enabled or task.status == TaskStatus.RUNNING:
                continue

            should_run = False

            if task.next_run > 0 and current_time >= task.next_run:
                should_run = True

            for trigger in task.triggers:
                if await self._check_trigger(trigger):
                    should_run = True
                    break

            if should_run:
                asyncio.create_task(self._execute_task(task))

    async def _check_trigger(self, trigger: Trigger) -> bool:
        """Check if trigger is activated"""
        if trigger.trigger_type == TriggerType.CONDITION:
            return await self._evaluate_condition(trigger.condition)

        return False

    async def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition expression"""
        try:
            context = {"time": datetime.now(), "hour": datetime.now().hour}
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception as e:
            self.logger.error(f"Condition evaluation error: {e}")
            return False

    async def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task"""
        execution_id = hashlib.md5(f"{task.id}{time.time()}".encode()).hexdigest()[:12]

        execution = TaskExecution(
            id=execution_id,
            task_id=task.id,
            started_at=time.time(),
        )

        task.status = TaskStatus.RUNNING
        self._executions[execution_id] = execution

        self.logger.info(f"Executing task: {task.name}")

        try:
            handler = self._action_handlers.get(task.action)

            if handler:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(task.action_params)
                else:
                    result = handler(task.action_params)
            else:
                result = {"message": f"Action '{task.action}' executed"}

            execution.result = result
            execution.status = TaskStatus.COMPLETED
            task.last_result = result
            task.success_count += 1

        except Exception as e:
            execution.error = str(e)
            execution.status = TaskStatus.FAILED
            task.fail_count += 1
            self.logger.error(f"Task execution failed: {e}")

        finally:
            execution.completed_at = time.time()
            execution.duration_ms = (
                execution.completed_at - execution.started_at
            ) * 1000

            task.status = TaskStatus.SCHEDULED
            task.last_run = time.time()
            task.run_count += 1

            task.next_run = self._calculate_next_run(task)

            self._save_task(task)

    def _calculate_next_run(self, task: ScheduledTask) -> float:
        """Calculate next run time"""
        if not task.schedule:
            return 0

        now = datetime.now()

        if task.schedule.schedule_type == ScheduleType.ONCE:
            return 0

        elif task.schedule.schedule_type == ScheduleType.INTERVAL:
            return time.time() + task.schedule.interval_seconds

        elif task.schedule.schedule_type == ScheduleType.DAILY:
            tomorrow = now + timedelta(days=1)
            return tomorrow.timestamp()

        elif task.schedule.schedule_type == ScheduleType.WEEKLY:
            days_ahead = 7 - now.weekday()
            next_week = now + timedelta(days=days_ahead)
            return next_week.timestamp()

        elif task.schedule.schedule_type == ScheduleType.CRON:
            try:
                cron = croniter.croniter(task.schedule.cron_expression, now)
                return cron.get_next_timestamp()
            except Exception as e:
                self.logger.error(f"Cron parse error: {e}")
                return 0

        return 0

    def _save_task(self, task: ScheduledTask):
        """Save task to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO tasks (id, data, created_at) VALUES (?, ?, ?)",
                (task.id, json.dumps(task.to_dict()), task.created_at),
            )
            conn.commit()

    def register_action_handler(self, action: str, handler: Callable):
        """Register handler for an action type"""
        self._action_handlers[action] = handler
        self.logger.debug(f"Registered handler for action: {action}")

    def create_task(
        self,
        name: str,
        action: str,
        action_params: Dict[str, Any] = None,
        schedule: ScheduleConfig = None,
        triggers: List[Trigger] = None,
    ) -> ScheduledTask:
        """Create a new scheduled task"""
        task_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:12]

        task = ScheduledTask(
            id=task_id,
            name=name,
            description="",
            action=action,
            action_params=action_params or {},
            schedule=schedule,
            triggers=triggers or [],
            status=TaskStatus.SCHEDULED,
        )

        task.next_run = self._calculate_next_run(task)

        self._tasks[task_id] = task
        self._save_task(task)

        self.logger.info(f"Created task: {name}")
        return task

    def create_interval_task(
        self,
        name: str,
        action: str,
        interval_seconds: int,
        action_params: Dict[str, Any] = None,
    ) -> ScheduledTask:
        """Create an interval-based task"""
        schedule = ScheduleConfig(
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=interval_seconds,
        )
        return self.create_task(name, action, action_params, schedule)

    def create_cron_task(
        self,
        name: str,
        action: str,
        cron_expression: str,
        action_params: Dict[str, Any] = None,
    ) -> ScheduledTask:
        """Create a cron-based task"""
        schedule = ScheduleConfig(
            schedule_type=ScheduleType.CRON,
            cron_expression=cron_expression,
        )
        return self.create_task(name, action, action_params, schedule)

    def create_conditional_task(
        self,
        name: str,
        action: str,
        condition: str,
        action_params: Dict[str, Any] = None,
    ) -> ScheduledTask:
        """Create a condition-triggered task"""
        trigger = Trigger(
            trigger_type=TriggerType.CONDITION,
            condition=condition,
        )
        return self.create_task(name, action, action_params, triggers=[trigger])

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get task by ID"""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[ScheduledTask]:
        """Get all tasks"""
        return list(self._tasks.values())

    def enable_task(self, task_id: str) -> bool:
        """Enable a task"""
        task = self.get_task(task_id)
        if task:
            task.enabled = True
            self._save_task(task)
            return True
        return False

    def disable_task(self, task_id: str) -> bool:
        """Disable a task"""
        task = self.get_task(task_id)
        if task:
            task.enabled = False
            self._save_task(task)
            return True
        return False

    def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                conn.commit()
            return True
        return False

    async def run_task_now(self, task_id: str) -> Optional[TaskExecution]:
        """Run a task immediately"""
        task = self.get_task(task_id)
        if not task:
            return None

        await self._execute_task(task)
        return self._executions.get(list(self._executions.keys())[-1])

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        return {
            "total_tasks": len(self._tasks),
            "enabled_tasks": sum(1 for t in self._tasks.values() if t.enabled),
            "total_runs": sum(t.run_count for t in self._tasks.values()),
            "total_successes": sum(t.success_count for t in self._tasks.values()),
            "total_failures": sum(t.fail_count for t in self._tasks.values()),
        }
