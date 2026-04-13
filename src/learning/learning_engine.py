#!/usr/bin/env python3
"""
ALPHA OMEGA - LEARNING ENGINE
Pattern Recognition, Behavior Prediction, and Workflow Automation
Version: 2.0.0
"""

import asyncio
import json
import logging
import time
import threading
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import statistics


@dataclass
class Pattern:
    pattern_id: str
    pattern_type: str
    sequence: List[str]
    frequency: int
    confidence: float
    first_seen: float
    last_seen: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "sequence": self.sequence,
            "frequency": self.frequency,
            "confidence": self.confidence,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "metadata": self.metadata,
        }


@dataclass
class Workflow:
    workflow_id: str
    name: str
    steps: List[Dict[str, Any]]
    trigger: Optional[str] = None
    schedule: Optional[str] = None
    enabled: bool = True
    success_rate: float = 1.0
    execution_count: int = 0
    last_executed: Optional[float] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "steps": self.steps,
            "trigger": self.trigger,
            "schedule": self.schedule,
            "enabled": self.enabled,
            "success_rate": self.success_rate,
            "execution_count": self.execution_count,
            "last_executed": self.last_executed,
            "created_at": self.created_at,
        }


class SequenceAnalyzer:
    def __init__(self, min_sequence_length: int = 2, max_sequence_length: int = 10):
        self.min_length = min_sequence_length
        self.max_length = max_sequence_length
        self._sequences = defaultdict(int)
        self._sequence_positions = defaultdict(list)

    def add_sequence(self, sequence: List[str]):
        for length in range(
            self.min_length, min(len(sequence) + 1, self.max_length + 1)
        ):
            for i in range(len(sequence) - length + 1):
                subseq = tuple(sequence[i : i + length])
                self._sequences[subseq] += 1
                self._sequence_positions[subseq].append(i)

    def find_patterns(
        self, min_frequency: int = 2
    ) -> List[Tuple[Tuple[str, ...], int]]:
        patterns = [
            (seq, freq)
            for seq, freq in self._sequences.items()
            if freq >= min_frequency
        ]
        patterns.sort(key=lambda x: (len(x[0]), x[1]), reverse=True)
        return patterns

    def predict_next(
        self, sequence: List[str], top_k: int = 3
    ) -> List[Tuple[str, float]]:
        if not sequence:
            return []

        predictions = defaultdict(float)

        for length in range(1, min(len(sequence) + 1, self.max_length)):
            recent = tuple(sequence[-length:])

            for seq, freq in self._sequences.items():
                if len(seq) > length and seq[:length] == recent:
                    next_item = seq[length]
                    predictions[next_item] += freq / (len(seq) - length + 1)

        if predictions:
            total = sum(predictions.values())
            predictions = {k: v / total for k, v in predictions.items()}

        sorted_predictions = sorted(
            predictions.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_predictions[:top_k]

    def clear(self):
        self._sequences.clear()
        self._sequence_positions.clear()


class BehaviorAnalyzer:
    def __init__(self):
        self._command_times = defaultdict(list)
        self._command_intervals = defaultdict(list)
        self._time_of_day_usage = defaultdict(lambda: defaultdict(int))
        self._day_of_week_usage = defaultdict(lambda: defaultdict(int))
        self._command_co_occurrences = defaultdict(lambda: defaultdict(int))
        self._session_commands = []
        self._session_start = time.time()

    def record_command(self, command: str, context: Dict[str, Any] = None):
        now = time.time()
        dt = datetime.fromtimestamp(now)

        self._command_times[command].append(now)

        if len(self._command_times[command]) > 1:
            interval = now - self._command_times[command][-2]
            self._command_intervals[command].append(interval)

        hour = dt.hour
        self._time_of_day_usage[command][hour] += 1

        day = dt.weekday()
        self._day_of_week_usage[command][day] += 1

        if self._session_commands:
            last_command = self._session_commands[-1]
            self._command_co_occurrences[last_command][command] += 1

        self._session_commands.append(command)

        if now - self._session_start > 3600:
            self._session_commands = self._session_commands[-100:]
            self._session_start = now

    def get_command_frequency(self, command: str) -> int:
        return len(self._command_times.get(command, []))

    def get_average_interval(self, command: str) -> float:
        intervals = self._command_intervals.get(command, [])
        return statistics.mean(intervals) if intervals else 0

    def get_peak_hours(self, command: str) -> List[int]:
        hourly = self._time_of_day_usage.get(command, {})
        if not hourly:
            return []
        sorted_hours = sorted(hourly.items(), key=lambda x: x[1], reverse=True)
        return [h for h, _ in sorted_hours[:3]]

    def get_related_commands(
        self, command: str, top_k: int = 5
    ) -> List[Tuple[str, int]]:
        related = self._command_co_occurrences.get(command, {})
        sorted_related = sorted(related.items(), key=lambda x: x[1], reverse=True)
        return sorted_related[:top_k]

    def get_habit_strength(self, command: str) -> float:
        frequency = self.get_command_frequency(command)
        if frequency < 3:
            return 0.0

        intervals = self._command_intervals.get(command, [])
        if len(intervals) < 2:
            return 0.0

        mean_interval = statistics.mean(intervals)
        std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0

        consistency = 1.0 - min(
            std_interval / mean_interval if mean_interval > 0 else 1, 1.0
        )
        recency = self._get_recency_score(command)

        strength = (frequency / 100.0) * 0.3 + consistency * 0.4 + recency * 0.3
        return min(strength, 1.0)

    def _get_recency_score(self, command: str) -> float:
        times = self._command_times.get(command, [])
        if not times:
            return 0.0

        last_used = times[-1]
        hours_since = (time.time() - last_used) / 3600

        if hours_since < 1:
            return 1.0
        elif hours_since < 24:
            return 0.8
        elif hours_since < 168:
            return 0.5
        else:
            return 0.2

    def export_data(self) -> Dict[str, Any]:
        return {
            "command_times": {k: v[-100:] for k, v in self._command_times.items()},
            "time_of_day_usage": {
                k: dict(v) for k, v in self._time_of_day_usage.items()
            },
            "day_of_week_usage": {
                k: dict(v) for k, v in self._day_of_week_usage.items()
            },
            "co_occurrences": {
                k: dict(v) for k, v in self._command_co_occurrences.items()
            },
        }


class WorkflowManager:
    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path("data/workflows.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._workflows: Dict[str, Workflow] = {}
        self._load_workflows()
        self._lock = threading.Lock()

    def _load_workflows(self):
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                for wf_data in data.get("workflows", []):
                    workflow = Workflow(
                        workflow_id=wf_data["workflow_id"],
                        name=wf_data["name"],
                        steps=wf_data["steps"],
                        trigger=wf_data.get("trigger"),
                        schedule=wf_data.get("schedule"),
                        enabled=wf_data.get("enabled", True),
                        success_rate=wf_data.get("success_rate", 1.0),
                        execution_count=wf_data.get("execution_count", 0),
                        last_executed=wf_data.get("last_executed"),
                        created_at=wf_data.get("created_at", time.time()),
                    )
                    self._workflows[workflow.workflow_id] = workflow
            except Exception:
                self._workflows = {}

    def _save_workflows(self):
        with self._lock:
            data = {
                "workflows": [w.to_dict() for w in self._workflows.values()],
                "updated_at": time.time(),
            }
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)

    def create_workflow(
        self,
        name: str,
        steps: List[Dict[str, Any]],
        trigger: str = None,
        schedule: str = None,
    ) -> Workflow:
        workflow_id = hashlib.sha256(f"{name}{time.time()}".encode()).hexdigest()[:16]

        workflow = Workflow(
            workflow_id=workflow_id,
            name=name,
            steps=steps,
            trigger=trigger,
            schedule=schedule,
        )

        self._workflows[workflow_id] = workflow
        self._save_workflows()

        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        return self._workflows.get(workflow_id)

    def list_workflows(self, enabled_only: bool = False) -> List[Workflow]:
        if enabled_only:
            return [w for w in self._workflows.values() if w.enabled]
        return list(self._workflows.values())

    def update_workflow(self, workflow_id: str, **kwargs) -> Optional[Workflow]:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        for key, value in kwargs.items():
            if hasattr(workflow, key):
                setattr(workflow, key, value)

        self._save_workflows()
        return workflow

    def delete_workflow(self, workflow_id: str) -> bool:
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            self._save_workflows()
            return True
        return False

    def record_execution(self, workflow_id: str, success: bool):
        workflow = self._workflows.get(workflow_id)
        if workflow:
            workflow.execution_count += 1
            workflow.last_executed = time.time()

            total = workflow.execution_count
            if success:
                successes = workflow.success_rate * (total - 1) + 1
            else:
                successes = workflow.success_rate * (total - 1)
            workflow.success_rate = successes / total

            self._save_workflows()


class LearningEngine:
    def __init__(self, config: Dict[str, Any], memory_system=None):
        self.config = config
        self.memory = memory_system
        self.logger = logging.getLogger("LearningEngine")

        self.enabled = config.get("learning_enabled", True)
        self.pattern_threshold = config.get("pattern_threshold", 3)
        self.min_confidence = config.get("min_confidence", 0.6)
        self.adaptation_rate = config.get("adaptation_rate", 0.1)

        self.sequence_analyzer = SequenceAnalyzer()
        self.behavior_analyzer = BehaviorAnalyzer()
        self.workflow_manager = WorkflowManager()

        self._command_buffer = deque(maxlen=1000)
        self._patterns: Dict[str, Pattern] = {}
        self._predictions: Dict[str, float] = {}
        self._suggestions: List[Dict[str, Any]] = []

        self._running = False
        self._learning_active = False

        self._voice_system = None
        self._automation_engine = None
        self._intelligence_engine = None

        self._stats = {
            "patterns_detected": 0,
            "workflows_created": 0,
            "predictions_made": 0,
            "suggestions_generated": 0,
        }

    async def initialize(self) -> bool:
        self.logger.info("Initializing Learning Engine...")

        if self.memory:
            patterns = await self.memory.get_patterns(limit=100)
            for p in patterns:
                self._patterns[p["id"]] = Pattern(
                    pattern_id=str(p["id"]),
                    pattern_type=p["type"],
                    sequence=p["data"].get("sequence", []),
                    frequency=p["frequency"],
                    confidence=p["confidence"],
                    first_seen=p.get("first_seen", time.time()),
                    last_seen=p.get("last_seen", time.time()),
                )

        self._running = True
        self.logger.info(f"Learning Engine initialized (enabled={self.enabled})")
        return True

    def connect_to_voice(self, voice_system):
        self._voice_system = voice_system

    def connect_to_automation(self, automation_engine):
        self._automation_engine = automation_engine

    def connect_to_intelligence(self, intelligence_engine):
        self._intelligence_engine = intelligence_engine

    def record_command(self, command: str, result: Dict[str, Any] = None):
        if not self.enabled:
            return

        timestamp = time.time()
        self._command_buffer.append(
            {"command": command, "timestamp": timestamp, "result": result}
        )

        self.behavior_analyzer.record_command(command, {"result": result})

        self._analyze_recent_commands()

    def _analyze_recent_commands(self):
        if len(self._command_buffer) < self.pattern_threshold:
            return

        recent_commands = [c["command"] for c in list(self._command_buffer)[-50:]]
        self.sequence_analyzer.add_sequence(recent_commands)

        patterns = self.sequence_analyzer.find_patterns(
            min_frequency=self.pattern_threshold
        )

        for seq, freq in patterns:
            pattern_id = hashlib.sha256("|".join(seq).encode()).hexdigest()[:16]

            if pattern_id not in self._patterns:
                confidence = min(freq / 10.0, 1.0)

                pattern = Pattern(
                    pattern_id=pattern_id,
                    pattern_type="command_sequence",
                    sequence=list(seq),
                    frequency=freq,
                    confidence=confidence,
                    first_seen=time.time(),
                    last_seen=time.time(),
                )

                self._patterns[pattern_id] = pattern
                self._stats["patterns_detected"] += 1

                if self.memory:
                    asyncio.create_task(
                        self.memory.store_pattern(
                            "command_sequence", {"sequence": list(seq)}, confidence
                        )
                    )

                if confidence > self.min_confidence and len(seq) >= 2:
                    self._generate_workflow_suggestion(pattern)

    def _generate_workflow_suggestion(self, pattern: Pattern):
        suggestion = {
            "pattern_id": pattern.pattern_id,
            "sequence": pattern.sequence,
            "confidence": pattern.confidence,
            "frequency": pattern.frequency,
            "suggested_workflow_name": f"Auto-detected: {' → '.join(pattern.sequence[:3])}...",
            "created_at": time.time(),
        }

        self._suggestions.append(suggestion)
        self._stats["suggestions_generated"] += 1

        self.logger.info(f"Workflow suggestion generated: {pattern.sequence}")

    async def start_learning(self):
        self.logger.info("Learning loop started")
        self._learning_active = True

        while self._running:
            try:
                await asyncio.sleep(60)

                self._update_predictions()

                self._cleanup_old_patterns()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Learning loop error: {e}")
                await asyncio.sleep(30)

        self._learning_active = False

    def _update_predictions(self):
        if len(self._command_buffer) < 2:
            return

        recent = [c["command"] for c in list(self._command_buffer)[-10:]]
        predictions = self.sequence_analyzer.predict_next(recent)

        self._predictions = dict(predictions)
        self._stats["predictions_made"] += len(predictions)

    def _cleanup_old_patterns(self):
        cutoff = time.time() - 86400 * 7

        to_remove = [
            pid
            for pid, p in self._patterns.items()
            if p.last_seen < cutoff and p.frequency < self.pattern_threshold
        ]

        for pid in to_remove:
            del self._patterns[pid]

    def get_next_prediction(
        self, context: Dict[str, Any] = None
    ) -> Optional[Tuple[str, float]]:
        if not self._predictions:
            return None

        best = max(self._predictions.items(), key=lambda x: x[1])
        return best if best[1] > self.min_confidence else None

    def get_patterns(self, limit: int = 20) -> List[Pattern]:
        sorted_patterns = sorted(
            self._patterns.values(),
            key=lambda p: (p.frequency, p.confidence),
            reverse=True,
        )
        return sorted_patterns[:limit]

    def get_suggestions(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self._suggestions[-limit:]

    def create_workflow_from_pattern(
        self, pattern_id: str, name: str = None
    ) -> Optional[Workflow]:
        pattern = self._patterns.get(pattern_id)
        if not pattern:
            return None

        steps = []
        for i, cmd in enumerate(pattern.sequence):
            steps.append({"step": i + 1, "command": cmd, "type": "automation"})

        workflow_name = name or f"Workflow from pattern {pattern_id[:8]}"

        workflow = self.workflow_manager.create_workflow(
            name=workflow_name, steps=steps, trigger=f"pattern:{pattern_id}"
        )

        self._stats["workflows_created"] += 1
        self.logger.info(f"Created workflow: {workflow.workflow_id}")

        return workflow

    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        workflow = self.workflow_manager.get_workflow(workflow_id)
        if not workflow or not workflow.enabled:
            return {"success": False, "message": "Workflow not found or disabled"}

        if not self._automation_engine:
            return {"success": False, "message": "Automation engine not connected"}

        results = []
        for step in workflow.steps:
            command = step.get("command", "")
            params = step.get("parameters", {})

            result = await self._automation_engine.execute_command(command, params)
            results.append(result.to_dict() if hasattr(result, "to_dict") else result)

            if not result.success:
                self.workflow_manager.record_execution(workflow_id, False)
                return {
                    "success": False,
                    "message": f"Workflow failed at step {step.get('step')}",
                    "results": results,
                }

        self.workflow_manager.record_execution(workflow_id, True)

        return {
            "success": True,
            "message": f"Workflow {workflow.name} completed successfully",
            "results": results,
            "workflow_id": workflow_id,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "patterns_count": len(self._patterns),
            "workflows_count": len(self.workflow_manager.list_workflows()),
            "command_buffer_size": len(self._command_buffer),
            "learning_active": self._learning_active,
            "predictions_available": len(self._predictions),
        }

    def is_learning(self) -> bool:
        return self._learning_active

    async def stop(self):
        self._running = False
        self.logger.info("Learning engine stopped")
