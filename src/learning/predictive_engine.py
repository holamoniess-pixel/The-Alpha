#!/usr/bin/env python3
"""
ALPHA OMEGA - PREDICTIVE AUTOMATION ENGINE
Learn user patterns and predict next actions
Version: 2.0.0
"""

import asyncio
import json
import logging
import time
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import threading
import math


@dataclass
class UserAction:
    action_type: str
    action_data: Dict[str, Any]
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.action_type,
            "data": self.action_data,
            "timestamp": self.timestamp,
            "context": self.context,
        }


@dataclass
class Pattern:
    id: str
    pattern_type: str
    sequence: List[str]
    frequency: int
    confidence: float
    time_context: Dict[str, Any] = field(default_factory=dict)
    conditions: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_matched: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.pattern_type,
            "sequence": self.sequence,
            "frequency": self.frequency,
            "confidence": self.confidence,
            "time_context": self.time_context,
            "conditions": self.conditions,
            "created_at": self.created_at,
            "last_matched": self.last_matched,
        }


@dataclass
class Prediction:
    action_type: str
    action_data: Dict[str, Any]
    confidence: float
    pattern_id: str
    reasoning: str
    suggested_time: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "action_data": self.action_data,
            "confidence": self.confidence,
            "pattern_id": self.pattern_id,
            "reasoning": self.reasoning,
            "suggested_time": self.suggested_time,
        }


class PatternMiner:
    """Mine patterns from user action sequences"""

    def __init__(self, min_support: int = 3, min_confidence: float = 0.6):
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.logger = logging.getLogger("PatternMiner")

    def mine_sequences(
        self,
        actions: List[UserAction],
        max_pattern_length: int = 5,
    ) -> List[Tuple[List[str], int, float]]:
        """Mine frequent sequences from actions"""
        sequences = [a.action_type for a in actions]

        patterns = []

        for length in range(2, min(max_pattern_length + 1, len(sequences) + 1)):
            for i in range(len(sequences) - length + 1):
                pattern = sequences[i : i + length]
                patterns.append(tuple(pattern))

        pattern_counts = Counter(patterns)

        frequent_patterns = []
        for pattern, count in pattern_counts.items():
            if count >= self.min_support:
                confidence = count / len(sequences)
                if confidence >= self.min_confidence:
                    frequent_patterns.append((list(pattern), count, confidence))

        frequent_patterns.sort(key=lambda x: x[2], reverse=True)

        return frequent_patterns

    def mine_temporal_patterns(
        self,
        actions: List[UserAction],
    ) -> List[Dict[str, Any]]:
        """Mine time-based patterns"""
        patterns = []

        hourly_actions = defaultdict(list)
        for action in actions:
            hour = datetime.fromtimestamp(action.timestamp).hour
            hourly_actions[hour].append(action.action_type)

        for hour, action_list in hourly_actions.items():
            if len(action_list) >= self.min_support:
                action_counts = Counter(action_list)
                for action_type, count in action_counts.most_common(3):
                    if count >= self.min_support:
                        patterns.append(
                            {
                                "type": "hourly",
                                "hour": hour,
                                "action": action_type,
                                "frequency": count,
                                "confidence": count / len(action_list),
                            }
                        )

        dow_actions = defaultdict(list)
        for action in actions:
            dow = datetime.fromtimestamp(action.timestamp).weekday()
            dow_actions[dow].append(action.action_type)

        for dow, action_list in dow_actions.items():
            if len(action_list) >= self.min_support:
                action_counts = Counter(action_list)
                for action_type, count in action_counts.most_common(3):
                    if count >= self.min_support:
                        patterns.append(
                            {
                                "type": "day_of_week",
                                "day": dow,
                                "action": action_type,
                                "frequency": count,
                                "confidence": count / len(action_list),
                            }
                        )

        return patterns

    def find_transitions(
        self,
        actions: List[UserAction],
    ) -> Dict[str, Dict[str, int]]:
        """Find transition probabilities between actions"""
        transitions = defaultdict(lambda: defaultdict(int))

        for i in range(len(actions) - 1):
            current = actions[i].action_type
            next_action = actions[i + 1].action_type
            transitions[current][next_action] += 1

        transition_probs = {}
        for current, nexts in transitions.items():
            total = sum(nexts.values())
            transition_probs[current] = {
                next_action: count / total for next_action, count in nexts.items()
            }

        return transition_probs


class PredictiveEngine:
    """Predictive automation engine"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("PredictiveEngine")

        db_path = self.config.get("db_path", "data/predictive_patterns.db")
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.miner = PatternMiner(
            min_support=self.config.get("min_support", 3),
            min_confidence=self.config.get("min_confidence", 0.6),
        )

        self._lock = threading.RLock()
        self._patterns: Dict[str, Pattern] = {}
        self._transitions: Dict[str, Dict[str, float]] = {}
        self._action_history: List[UserAction] = []
        self._max_history = 1000

        self._predictions_enabled = True
        self._learning_enabled = True

        self._stats = {
            "actions_recorded": 0,
            "patterns_found": 0,
            "predictions_made": 0,
            "predictions_correct": 0,
        }

        self._init_db()

    def _init_db(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    sequence TEXT NOT NULL,
                    frequency INTEGER,
                    confidence REAL,
                    time_context TEXT,
                    conditions TEXT,
                    created_at REAL,
                    last_matched REAL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    data TEXT,
                    timestamp REAL,
                    context TEXT
                )
            """)

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_pattern_type ON patterns(type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_action_time ON actions(timestamp)"
            )

            conn.commit()

    async def initialize(self) -> bool:
        """Initialize the engine"""
        self.logger.info("Initializing Predictive Engine...")

        self._load_patterns()

        self.logger.info(f"Loaded {len(self._patterns)} patterns")
        self.logger.info("Predictive Engine initialized")
        return True

    def _load_patterns(self):
        """Load patterns from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT * FROM patterns")
                for row in cursor.fetchall():
                    pattern = Pattern(
                        id=row[0],
                        pattern_type=row[1],
                        sequence=json.loads(row[2]),
                        frequency=row[3],
                        confidence=row[4],
                        time_context=json.loads(row[5]) if row[5] else {},
                        conditions=json.loads(row[6]) if row[6] else {},
                        created_at=row[7],
                        last_matched=row[8],
                    )
                    self._patterns[pattern.id] = pattern
        except Exception as e:
            self.logger.error(f"Error loading patterns: {e}")

    def _save_pattern(self, pattern: Pattern):
        """Save pattern to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO patterns
                    (id, type, sequence, frequency, confidence, time_context, conditions, created_at, last_matched)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pattern.id,
                        pattern.pattern_type,
                        json.dumps(pattern.sequence),
                        pattern.frequency,
                        pattern.confidence,
                        json.dumps(pattern.time_context),
                        json.dumps(pattern.conditions),
                        pattern.created_at,
                        pattern.last_matched,
                    ),
                )
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error saving pattern: {e}")

    async def record_action(
        self,
        action_type: str,
        action_data: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
    ):
        """Record a user action"""
        if not self._learning_enabled:
            return

        with self._lock:
            action = UserAction(
                action_type=action_type,
                action_data=action_data or {},
                timestamp=time.time(),
                context=context or {},
            )

            self._action_history.append(action)
            if len(self._action_history) > self._max_history:
                self._action_history = self._action_history[-self._max_history :]

            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT INTO actions (type, data, timestamp, context)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            action_type,
                            json.dumps(action_data or {}),
                            action.timestamp,
                            json.dumps(context or {}),
                        ),
                    )
                    conn.commit()
            except Exception as e:
                self.logger.error(f"Error saving action: {e}")

            self._stats["actions_recorded"] += 1

            if len(self._action_history) % 10 == 0:
                await self._update_patterns()

    async def _update_patterns(self):
        """Update patterns from recent actions"""
        if len(self._action_history) < self.miner.min_support:
            return

        sequences = self.miner.mine_sequences(self._action_history[-100:])

        for seq, freq, conf in sequences[:10]:
            pattern_id = "|".join(seq)

            if pattern_id in self._patterns:
                self._patterns[pattern_id].frequency = freq
                self._patterns[pattern_id].confidence = max(
                    self._patterns[pattern_id].confidence, conf
                )
            else:
                pattern = Pattern(
                    id=pattern_id,
                    pattern_type="sequence",
                    sequence=seq,
                    frequency=freq,
                    confidence=conf,
                )
                self._patterns[pattern_id] = pattern
                self._stats["patterns_found"] += 1

            self._save_pattern(self._patterns[pattern_id])

        temporal_patterns = self.miner.mine_temporal_patterns(
            self._action_history[-200:]
        )

        for tp in temporal_patterns:
            pattern_id = f"temporal_{tp['type']}_{tp.get('hour', tp.get('day', ''))}_{tp['action']}"

            pattern = Pattern(
                id=pattern_id,
                pattern_type=tp["type"],
                sequence=[tp["action"]],
                frequency=tp["frequency"],
                confidence=tp["confidence"],
                time_context={
                    "hour": tp.get("hour"),
                    "day": tp.get("day"),
                },
            )

            self._patterns[pattern_id] = pattern
            self._save_pattern(pattern)

        self._transitions = self.miner.find_transitions(self._action_history[-100:])

    async def predict_next_action(
        self,
        current_context: Dict[str, Any] = None,
    ) -> Optional[Prediction]:
        """Predict the next action based on patterns"""
        if not self._predictions_enabled or not self._patterns:
            return None

        context = current_context or {}
        current_time = time.time()
        current_hour = datetime.fromtimestamp(current_time).hour
        current_dow = datetime.fromtimestamp(current_time).weekday()

        temporal_predictions = []
        for pattern in self._patterns.values():
            if pattern.pattern_type in ["hourly", "day_of_week"]:
                if pattern.pattern_type == "hourly":
                    if pattern.time_context.get("hour") == current_hour:
                        temporal_predictions.append((pattern, pattern.confidence))
                elif pattern.pattern_type == "day_of_week":
                    if pattern.time_context.get("day") == current_dow:
                        temporal_predictions.append((pattern, pattern.confidence))

        if temporal_predictions:
            temporal_predictions.sort(key=lambda x: x[1], reverse=True)
            best_pattern = temporal_predictions[0][0]

            return Prediction(
                action_type=best_pattern.sequence[0],
                action_data={"predicted": True},
                confidence=best_pattern.confidence,
                pattern_id=best_pattern.id,
                reasoning=f"Based on {best_pattern.pattern_type} pattern",
            )

        if self._action_history:
            last_action = self._action_history[-1].action_type

            if last_action in self._transitions:
                transitions = self._transitions[last_action]
                if transitions:
                    best_next = max(transitions.items(), key=lambda x: x[1])

                    return Prediction(
                        action_type=best_next[0],
                        action_data={"predicted": True},
                        confidence=best_next[1],
                        pattern_id="transition",
                        reasoning=f"After '{last_action}', usually follows '{best_next[0]}'",
                    )

        return None

    async def predict_sequence(
        self,
        starting_action: str,
        length: int = 3,
    ) -> List[Prediction]:
        """Predict a sequence of actions"""
        predictions = []
        current_action = starting_action

        for _ in range(length):
            if current_action not in self._transitions:
                break

            transitions = self._transitions[current_action]
            if not transitions:
                break

            best_next = max(transitions.items(), key=lambda x: x[1])

            predictions.append(
                Prediction(
                    action_type=best_next[0],
                    action_data={"predicted": True},
                    confidence=best_next[1],
                    pattern_id="transition",
                    reasoning=f"Follows from {current_action}",
                )
            )

            current_action = best_next[0]

        return predictions

    async def get_suggestions(
        self,
        context: Dict[str, Any] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get action suggestions based on patterns"""
        suggestions = []

        prediction = await self.predict_next_action(context)
        if prediction:
            suggestions.append(
                {
                    "action": prediction.action_type,
                    "confidence": prediction.confidence,
                    "reasoning": prediction.reasoning,
                    "type": "predicted_next",
                }
            )

        current_time = time.time()
        current_hour = datetime.fromtimestamp(current_time).hour

        for pattern in self._patterns.values():
            if pattern.pattern_type == "hourly":
                if pattern.time_context.get("hour") == current_hour:
                    suggestions.append(
                        {
                            "action": pattern.sequence[0],
                            "confidence": pattern.confidence,
                            "reasoning": f"Usually done at {current_hour}:00",
                            "type": "time_based",
                        }
                    )

        if self._action_history:
            recent = [a.action_type for a in self._action_history[-10:]]
            action_counts = Counter(recent)

            for action, count in action_counts.most_common(3):
                suggestions.append(
                    {
                        "action": action,
                        "confidence": count / len(recent),
                        "reasoning": "Frequently used recently",
                        "type": "frequent",
                    }
                )

        suggestions.sort(key=lambda x: x["confidence"], reverse=True)

        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s["action"] not in seen:
                seen.add(s["action"])
                unique_suggestions.append(s)

        return unique_suggestions[:limit]

    async def record_prediction_result(
        self,
        prediction_id: str,
        was_correct: bool,
    ):
        """Record whether a prediction was correct"""
        self._stats["predictions_made"] += 1
        if was_correct:
            self._stats["predictions_correct"] += 1

    def enable_predictions(self, enabled: bool = True):
        """Enable or disable predictions"""
        self._predictions_enabled = enabled

    def enable_learning(self, enabled: bool = True):
        """Enable or disable learning"""
        self._learning_enabled = enabled

    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get statistics about patterns"""
        return {
            "total_patterns": len(self._patterns),
            "sequence_patterns": sum(
                1 for p in self._patterns.values() if p.pattern_type == "sequence"
            ),
            "temporal_patterns": sum(
                1
                for p in self._patterns.values()
                if p.pattern_type in ["hourly", "day_of_week"]
            ),
            "transitions": len(self._transitions),
            "history_size": len(self._action_history),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        accuracy = 0.0
        if self._stats["predictions_made"] > 0:
            accuracy = (
                self._stats["predictions_correct"] / self._stats["predictions_made"]
            )

        return {
            **self._stats,
            "accuracy": round(accuracy, 3),
            "patterns": self.get_pattern_stats(),
        }

    async def analyze_patterns(self) -> Dict[str, Any]:
        """Analyze current patterns"""
        analysis = {
            "top_sequences": [],
            "top_actions": [],
            "time_distribution": {},
            "transitions": {},
        }

        sorted_patterns = sorted(
            self._patterns.values(),
            key=lambda p: p.confidence,
            reverse=True,
        )

        for pattern in sorted_patterns[:10]:
            if pattern.pattern_type == "sequence":
                analysis["top_sequences"].append(
                    {
                        "sequence": " → ".join(pattern.sequence),
                        "frequency": pattern.frequency,
                        "confidence": round(pattern.confidence, 3),
                    }
                )

        if self._action_history:
            action_counts = Counter(a.action_type for a in self._action_history)
            for action, count in action_counts.most_common(10):
                analysis["top_actions"].append(
                    {
                        "action": action,
                        "count": count,
                    }
                )

        hourly_dist = defaultdict(int)
        for action in self._action_history:
            hour = datetime.fromtimestamp(action.timestamp).hour
            hourly_dist[hour] += 1

        analysis["time_distribution"] = dict(sorted(hourly_dist.items()))

        for current, nexts in self._transitions.items():
            top_transitions = sorted(nexts.items(), key=lambda x: x[1], reverse=True)[
                :3
            ]
            analysis["transitions"][current] = [
                {"next": n, "probability": round(p, 3)} for n, p in top_transitions
            ]

        return analysis

    async def clear_history(self):
        """Clear action history"""
        with self._lock:
            self._action_history.clear()

            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM actions")
                    conn.commit()
            except Exception as e:
                self.logger.error(f"Error clearing history: {e}")

    async def clear_patterns(self):
        """Clear all patterns"""
        with self._lock:
            self._patterns.clear()
            self._transitions.clear()

            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM patterns")
                    conn.commit()
            except Exception as e:
                self.logger.error(f"Error clearing patterns: {e}")
