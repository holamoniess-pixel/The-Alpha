#!/usr/bin/env python3
"""
ALPHA OMEGA - PRODUCTION CORE SYSTEM
High-performance, low-latency AI assistant orchestrator
with Self-Extension capabilities
Version: 2.1.0
"""

import asyncio
import logging
import time
import threading
import queue
import signal
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum, auto
from concurrent.futures import ThreadPoolExecutor
import traceback
import json
import yaml


class SystemState(Enum):
    UNINITIALIZED = auto()
    INITIALIZING = auto()
    READY = auto()
    LISTENING = auto()
    PROCESSING = auto()
    SPEAKING = auto()
    PAUSED = auto()
    ERROR = auto()
    SHUTTING_DOWN = auto()


class Priority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class SystemConfig:
    name: str = "AlphaOmega"
    version: str = "2.1.0"
    wake_word: str = "hey alpha"
    language: str = "en-US"
    offline_mode: bool = True
    debug_mode: bool = False
    max_memory_mb: int = 4096
    cpu_limit_percent: int = 80
    response_timeout_ms: int = 500
    log_level: str = "INFO"

    @classmethod
    def from_yaml(cls, path: str) -> "SystemConfig":
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}
            return cls(
                name=data.get("system", {}).get("name", "AlphaOmega"),
                version=data.get("system", {}).get("version", "2.1.0"),
                wake_word=data.get("system", {}).get("wake_word", "hey alpha"),
                language=data.get("system", {}).get("language", "en-US"),
                offline_mode=data.get("system", {}).get("offline_mode", True),
                debug_mode=data.get("system", {}).get("debug_mode", False),
                max_memory_mb=data.get("performance", {}).get("max_memory_mb", 4096),
                cpu_limit_percent=data.get("performance", {}).get("cpu_limit", 80),
                response_timeout_ms=data.get("performance", {}).get(
                    "response_time_ms", 500
                ),
                log_level=data.get("logging", {}).get("level", "INFO"),
            )
        except Exception:
            return cls()


class PerformanceMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.commands_processed = 0
        self.commands_successful = 0
        self.commands_failed = 0
        self.total_processing_time_ms = 0
        self.avg_response_time_ms = 0
        self._lock = threading.Lock()

    def record_command(self, success: bool, processing_time_ms: float):
        with self._lock:
            self.commands_processed += 1
            if success:
                self.commands_successful += 1
            else:
                self.commands_failed += 1
            self.total_processing_time_ms += processing_time_ms
            self.avg_response_time_ms = (
                self.total_processing_time_ms / self.commands_processed
            )

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            uptime = time.time() - self.start_time
            return {
                "uptime_seconds": uptime,
                "uptime_formatted": str(timedelta(seconds=int(uptime))),
                "commands_total": self.commands_processed,
                "commands_successful": self.commands_successful,
                "commands_failed": self.commands_failed,
                "success_rate": (
                    self.commands_successful / self.commands_processed * 100
                )
                if self.commands_processed > 0
                else 0,
                "avg_response_ms": round(self.avg_response_time_ms, 2),
            }


class AlphaOmegaCore:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: SystemConfig = None):
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.config = config or SystemConfig()
        self.state = SystemState.UNINITIALIZED
        self.metrics = PerformanceMetrics()

        self._command_queue = queue.PriorityQueue()
        self._response_queue = queue.Queue()
        self._executor = ThreadPoolExecutor(
            max_workers=8, thread_name_prefix="AlphaWorker"
        )
        self._event_loop = None
        self._running = False
        self._paused = False
        self._pause_reason = ""

        self._components = {}
        self._component_status = {}

        self._setup_logging()
        self._setup_signal_handlers()

        self._initialized = True
        self.logger.info(f"AlphaOmega Core v{self.config.version} initialized")

    def _setup_logging(self):
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        log_file = log_dir / f"alpha_omega_{datetime.now().strftime('%Y%m%d')}.log"

        handlers = [
            logging.StreamHandler(sys.stdout),
            logging.handlers.RotatingFileHandler(
                log_file, maxBytes=50 * 1024 * 1024, backupCount=10, encoding="utf-8"
            ),
        ]

        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper()),
            format=log_format,
            handlers=handlers,
        )

        self.logger = logging.getLogger("AlphaOmega")

    def _setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(self.shutdown())

    def register_component(self, name: str, component: Any):
        self._components[name] = component
        self._component_status[name] = {
            "status": "registered",
            "last_check": time.time(),
        }
        self.logger.info(f"Component registered: {name}")

    def get_component(self, name: str) -> Optional[Any]:
        return self._components.get(name)

    async def initialize(self) -> bool:
        self.state = SystemState.INITIALIZING
        self.logger.info("=" * 60)
        self.logger.info("ALPHA OMEGA SYSTEM INITIALIZATION")
        self.logger.info("=" * 60)

        try:
            init_order = [
                ("memory", "src.memory.memory_system.MemorySystem"),
                ("security", "src.security.security_framework.SecurityFramework"),
                ("voice", "src.voice.voice_system.VoiceSystem"),
                (
                    "intelligence",
                    "src.intelligence.intelligence_engine.IntelligenceEngine",
                ),
                ("automation", "src.automation.automation_engine.AutomationEngine"),
                ("learning", "src.learning.learning_engine.LearningEngine"),
                ("vision", "src.vision.vision_system.VisionSystem"),
                ("vault", "src.vault.vault_manager.VaultManager"),
                ("self_extension", "src.core.self_extension.SelfExtensionEngine"),
            ]

            for comp_name, comp_path in init_order:
                try:
                    module_path, class_name = comp_path.rsplit(".", 1)
                    module = __import__(module_path, fromlist=[class_name])
                    component_class = getattr(module, class_name)

                    if comp_name == "memory":
                        component = component_class(self.config.__dict__)
                    elif comp_name == "vault":
                        component = component_class()
                    elif comp_name == "self_extension":
                        component = component_class(
                            self._components.get("automation"),
                            self._components.get("intelligence"),
                            self._components.get("memory"),
                        )
                    else:
                        component = component_class(
                            self.config.__dict__, self._components.get("memory")
                        )

                    if hasattr(component, "initialize"):
                        success = await component.initialize()
                        if not success:
                            self.logger.warning(
                                f"Component {comp_name} initialization returned False"
                            )

                    self.register_component(comp_name, component)
                    self.logger.info(f"[OK] {comp_name.upper()} initialized")

                except Exception as e:
                    self.logger.warning(f"[SKIP] {comp_name.upper()}: {e}")
                    self._component_status[comp_name] = {
                        "status": "failed",
                        "error": str(e),
                    }

            self.state = SystemState.READY
            self._running = True

            self.logger.info("=" * 60)
            self.logger.info("SYSTEM READY - ALL COMPONENTS OPERATIONAL")
            self.logger.info(f"Wake Word: '{self.config.wake_word}'")
            self.logger.info(
                f"Mode: {'OFFLINE' if self.config.offline_mode else 'ONLINE'}"
            )
            self.logger.info("=" * 60)

            return True

        except Exception as e:
            self.logger.error(f"CRITICAL: Initialization failed: {e}")
            self.logger.error(traceback.format_exc())
            self.state = SystemState.ERROR
            return False

    async def start(self):
        if self.state not in [SystemState.READY, SystemState.PAUSED]:
            self.logger.error(f"Cannot start: system state is {self.state.name}")
            return False

        self.logger.info("Starting Alpha Omega system...")
        self._running = True

        tasks = []

        if "voice" in self._components:
            voice = self._components["voice"]
            if hasattr(voice, "start_listening"):
                tasks.append(self._run_component_task("voice", voice.start_listening()))

        if "memory" in self._components:
            memory = self._components["memory"]
            if hasattr(memory, "start_maintenance"):
                tasks.append(
                    self._run_component_task("memory", memory.start_maintenance())
                )

        if "learning" in self._components:
            learning = self._components["learning"]
            if hasattr(learning, "start_learning"):
                tasks.append(
                    self._run_component_task("learning", learning.start_learning())
                )

        if "security" in self._components:
            security = self._components["security"]
            if hasattr(security, "start_monitoring"):
                tasks.append(
                    self._run_component_task("security", security.start_monitoring())
                )

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        return True

    async def _run_component_task(self, name: str, coro):
        try:
            await coro
        except asyncio.CancelledError:
            self.logger.info(f"{name} task cancelled")
        except Exception as e:
            self.logger.error(f"{name} task error: {e}")

    async def process_command(
        self, command: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        self.state = SystemState.PROCESSING

        try:
            if self._paused:
                return {
                    "success": False,
                    "message": f"System paused: {self._pause_reason}",
                    "state": "paused",
                }

            security = self._components.get("security")
            if security and hasattr(security, "is_command_allowed"):
                if not security.is_command_allowed(command):
                    return {
                        "success": False,
                        "message": "Command blocked by security policy",
                        "state": "blocked",
                    }

            intelligence = self._components.get("intelligence")
            if not intelligence:
                return {
                    "success": False,
                    "message": "Intelligence engine not available",
                }

            intent = await intelligence.process_command(command, context)
            intent_type = intent.get("type", "unknown")

            # Check if this is a complex task that needs self-extension
            self_extension = self._components.get("self_extension")
            complex_keywords = [
                "send",
                "message",
                "email",
                "whatsapp",
                "discord",
                "all my",
                "multiple",
                "and then",
            ]
            is_complex = any(kw in command.lower() for kw in complex_keywords)

            if is_complex and self_extension:
                self.logger.info(f"Using self-extension for complex task: {command}")
                result = await self_extension.process_request(command, context)
                response = {
                    "success": result.get("success", False),
                    "message": result.get("result", {}).get(
                        "message", "Task processed"
                    ),
                    "data": result,
                }
            elif intent_type == "automation":
                automation = self._components.get("automation")
                if automation:
                    result = await automation.execute_command(
                        intent.get("command", command), intent.get("parameters", {})
                    )
                    response = {
                        "success": result.success
                        if hasattr(result, "success")
                        else True,
                        "message": result.message
                        if hasattr(result, "message")
                        else str(result),
                        "data": result.data if hasattr(result, "data") else None,
                    }
                else:
                    response = {
                        "success": False,
                        "message": "Automation engine not available",
                    }

            elif intent_type == "query":
                response = await intelligence.answer_query(intent)

            elif intent_type == "system":
                response = await self._handle_system_command(intent)

            else:
                response = await intelligence.generate_response(command, intent)

            learning = self._components.get("learning")
            if learning and response.get("success"):
                if hasattr(learning, "record_command"):
                    learning.record_command(command, response)

            processing_time = (time.time() - start_time) * 1000
            self.metrics.record_command(response.get("success", False), processing_time)

            self.state = SystemState.READY
            return response

        except Exception as e:
            self.logger.error(f"Command processing error: {e}")
            self.logger.error(traceback.format_exc())
            self.state = SystemState.ERROR
            return {
                "success": False,
                "message": f"Error processing command: {str(e)}",
                "error": str(e),
            }

    async def _handle_system_command(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        command = intent.get("command", "").lower()

        if command == "status":
            return {
                "success": True,
                "message": self.get_status(),
                "data": self.metrics.to_dict(),
            }
        elif command == "help":
            return {"success": True, "message": self._get_help_text()}
        elif command == "pause":
            return await self.pause("User requested pause")
        elif command == "resume":
            return await self.resume()
        elif command == "shutdown":
            await self.shutdown()
            return {"success": True, "message": "System shutting down..."}
        else:
            return {"success": False, "message": f"Unknown system command: {command}"}

    async def pause(self, reason: str = "Manual pause") -> Dict[str, Any]:
        self._paused = True
        self._pause_reason = reason
        self.state = SystemState.PAUSED
        self.logger.info(f"System paused: {reason}")
        return {
            "success": True,
            "message": f"System paused: {reason}",
            "state": "paused",
        }

    async def resume(self) -> Dict[str, Any]:
        if not self._paused:
            return {"success": False, "message": "System is not paused"}
        self._paused = False
        self._pause_reason = ""
        self.state = SystemState.READY
        self.logger.info("System resumed")
        return {"success": True, "message": "System resumed", "state": "running"}

    def get_status(self) -> str:
        components_status = []
        for name, status in self._component_status.items():
            state = status.get("status", "unknown")
            components_status.append(f"{name}: {state}")

        return f"""Alpha Omega System Status v{self.config.version}
{"=" * 50}
State: {self.state.name}
Paused: {self._paused}
Uptime: {self.metrics.to_dict()["uptime_formatted"]}
Commands Processed: {self.metrics.commands_processed}
Success Rate: {self.metrics.to_dict()["success_rate"]:.1f}%
Avg Response: {self.metrics.avg_response_time_ms:.1f}ms
{"=" * 50}
Components: {", ".join(components_status)}
{"=" * 50}"""

    def _get_help_text(self) -> str:
        return f"""Alpha Omega Help - v{self.config.version}
{"=" * 50}
VOICE COMMANDS:
  "{self.config.wake_word}" - Activate voice control
  "{self.config.wake_word}, what time is it?" - Query
  "{self.config.wake_word}, open [app]" - Launch app
  "{self.config.wake_word}, pause" - Pause system

SYSTEM COMMANDS:
  status - Show system status
  help - Show this help
  pause/resume - Control system state

AUTOMATION:
  open [app] - Launch applications
  close [app] - Close applications
  type [text] - Type text
  click [x] [y] - Click position
  screenshot - Capture screen

SELF-EXTENSION:
  send message to [contact] on whatsapp - Auto-creates tool
  email [address] about [subject] - Auto-creates tool
{"=" * 50}"""

    async def shutdown(self):
        self.logger.info("Initiating graceful shutdown...")
        self.state = SystemState.SHUTTING_DOWN
        self._running = False

        shutdown_tasks = []
        for name, component in self._components.items():
            if hasattr(component, "stop"):
                self.logger.info(f"Stopping {name}...")
                try:
                    if asyncio.iscoroutinefunction(component.stop):
                        shutdown_tasks.append(component.stop())
                    else:
                        component.stop()
                except Exception as e:
                    self.logger.error(f"Error stopping {name}: {e}")

        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)

        self._executor.shutdown(wait=True)
        self.logger.info("=" * 60)
        self.logger.info("ALPHA OMEGA SHUTDOWN COMPLETE")
        self.logger.info("=" * 60)


_system_instance = None


def get_system(config: SystemConfig = None) -> AlphaOmegaCore:
    global _system_instance
    if _system_instance is None:
        _system_instance = AlphaOmegaCore(config)
    return _system_instance


async def main():
    config = SystemConfig.from_yaml("config.yaml")
    system = get_system(config)

    try:
        success = await system.initialize()
        if not success:
            print("System initialization failed")
            return 1

        await system.start()

        while system._running:
            await asyncio.sleep(1)

        return 0

    except KeyboardInterrupt:
        print("\nShutdown requested...")
        await system.shutdown()
        return 0
    except Exception as e:
        print(f"Fatal error: {e}")
        await system.shutdown()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
