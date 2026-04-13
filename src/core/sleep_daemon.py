"""
ALPHA OMEGA - Sleep Daemon
Background Service for Sleep Mode Operation
Version: 2.0.0
"""

import os
import sys
import time
import logging
import threading
import json
from pathlib import Path
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import subprocess

logger = logging.getLogger("SleepDaemon")


@dataclass
class ScheduledTask:
    task_id: str
    name: str
    task_type: str
    scheduled_time: float
    interval_seconds: Optional[float] = None
    recurring: bool = False
    callback_name: Optional[str] = None
    params: dict = field(default_factory=dict)
    enabled: bool = True
    last_run: Optional[float] = None
    next_run: Optional[float] = None
    status: str = "pending"


class SleepDaemon:
    _is_windows = os.name == "nt"

    def __init__(self, config: dict = None, data_dir: str = None):
        self.config = config or {}
        self.data_dir = Path(data_dir or "C:/AlphaOmega/data")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._paused = False
        self._threads: List[threading.Thread] = []
        self._task_callbacks: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._state_file = self.data_dir / "daemon_state.json"

        self._load_state()

    def _load_state(self):
        try:
            if self._state_file.exists():
                data = json.loads(self._state_file.read_text())
                for task_data in data.get("tasks", []):
                    task = ScheduledTask(**task_data)
                    self._tasks[task.task_id] = task
                logger.info(f"Loaded {len(self._tasks)} tasks from state")
        except Exception as e:
            logger.error(f"Failed to load state: {e}")

    def _save_state(self):
        try:
            data = {
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "name": t.name,
                        "task_type": t.task_type,
                        "scheduled_time": t.scheduled_time,
                        "interval_seconds": t.interval_seconds,
                        "recurring": t.recurring,
                        "callback_name": t.callback_name,
                        "params": t.params,
                        "enabled": t.enabled,
                        "last_run": t.last_run,
                        "next_run": t.next_run,
                        "status": t.status,
                    }
                    for t in self._tasks.values()
                ],
                "last_saved": time.time(),
            }
            self._state_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def start(self) -> bool:
        if self._running:
            logger.warning("Daemon already running")
            return False

        self._running = True
        self._paused = False

        task_thread = threading.Thread(target=self._task_loop, daemon=True)
        task_thread.start()
        self._threads.append(task_thread)

        heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        self._threads.append(heartbeat_thread)

        network_thread = threading.Thread(target=self._network_keepalive, daemon=True)
        network_thread.start()
        self._threads.append(network_thread)

        logger.info("Sleep daemon started")
        return True

    def stop(self) -> bool:
        self._running = False
        self._save_state()

        for thread in self._threads:
            thread.join(timeout=5)

        self._threads.clear()
        logger.info("Sleep daemon stopped")
        return True

    def pause(self):
        self._paused = True
        logger.info("Daemon paused")

    def resume(self):
        self._paused = False
        logger.info("Daemon resumed")

    def is_running(self) -> bool:
        return self._running

    def is_paused(self) -> bool:
        return self._paused

    def add_task(self, task: ScheduledTask) -> bool:
        with self._lock:
            if task.task_id in self._tasks:
                logger.warning(f"Task {task.task_id} already exists")
                return False

            task.next_run = task.scheduled_time
            self._tasks[task.task_id] = task
            self._save_state()
            logger.info(f"Added task: {task.name} ({task.task_id})")
            return True

    def remove_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id not in self._tasks:
                return False

            del self._tasks[task_id]
            self._save_state()
            logger.info(f"Removed task: {task_id}")
            return True

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        return self._tasks.get(task_id)

    def get_active_tasks(self) -> List[ScheduledTask]:
        return [t for t in self._tasks.values() if t.enabled]

    def register_callback(self, name: str, callback: Callable):
        self._task_callbacks[name] = callback

    def _task_loop(self):
        while self._running:
            if self._paused:
                time.sleep(1)
                continue

            try:
                now = time.time()

                for task in list(self._tasks.values()):
                    if not task.enabled or task.next_run is None:
                        continue

                    if now >= task.next_run:
                        self._execute_task(task)

            except Exception as e:
                logger.error(f"Task loop error: {e}")

            time.sleep(1)

    def _execute_task(self, task: ScheduledTask):
        logger.info(f"Executing task: {task.name}")
        task.status = "running"

        try:
            if task.callback_name and task.callback_name in self._task_callbacks:
                callback = self._task_callbacks[task.callback_name]
                callback(task.params)
            elif task.task_type == "script":
                self._run_script(task.params.get("script_path"))
            elif task.task_type == "command":
                self._run_command(task.params.get("command"))
            elif task.task_type == "backup":
                self._run_backup(task.params)

            task.last_run = time.time()
            task.status = "completed"

            if task.recurring and task.interval_seconds:
                task.next_run = task.last_run + task.interval_seconds
            else:
                task.next_run = None
                task.enabled = False

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            task.status = "failed"

        self._save_state()

    def _run_script(self, script_path: str):
        if not script_path or not Path(script_path).exists():
            raise ValueError(f"Script not found: {script_path}")

        result = subprocess.run(
            [sys.executable, script_path], capture_output=True, text=True, timeout=300
        )

        if result.returncode != 0:
            raise Exception(result.stderr)

    def _run_command(self, command: str):
        if not command:
            raise ValueError("No command specified")

        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=60
        )

        if result.returncode != 0:
            raise Exception(result.stderr)

    def _run_backup(self, params: dict):
        source = params.get("source")
        dest = params.get("destination")

        if not source or not dest:
            raise ValueError("Missing source or destination for backup")

        import shutil

        shutil.copytree(source, dest, dirs_exist_ok=True)

    def _heartbeat_loop(self):
        heartbeat_file = self.data_dir / "heartbeat.json"

        while self._running:
            try:
                heartbeat = {
                    "timestamp": time.time(),
                    "running": self._running,
                    "paused": self._paused,
                    "task_count": len(self._tasks),
                    "active_tasks": len([t for t in self._tasks.values() if t.enabled]),
                }
                heartbeat_file.write_text(json.dumps(heartbeat))
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

            time.sleep(10)

    def _network_keepalive(self):
        if not self.config.get("keep_network_alive", False):
            return

        while self._running:
            try:
                if self.config.get("network_ping_url"):
                    import urllib.request

                    urllib.request.urlopen(self.config["network_ping_url"], timeout=10)
                    logger.debug("Network keepalive ping sent")
            except Exception as e:
                logger.debug(f"Network keepalive error: {e}")

            time.sleep(60)

    def schedule_wake_and_run(self, wake_time: float, task: ScheduledTask) -> bool:
        from src.core.power_manager import PowerManager

        pm = PowerManager(self.config)
        wake_id = pm.schedule_wake(wake_time, f"task_{task.task_id}")

        if wake_id:
            task.params["wake_id"] = wake_id
            return self.add_task(task)

        return False

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "paused": self._paused,
            "task_count": len(self._tasks),
            "active_tasks": len([t for t in self._tasks.values() if t.enabled]),
            "threads": len(self._threads),
        }
