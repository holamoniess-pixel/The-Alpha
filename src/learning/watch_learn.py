"""
ALPHA OMEGA - Watch & Learn Engine
Learn from User Actions and Create Automations
Version: 2.0.0
"""

import os
import sys
import time
import logging
import threading
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import queue

logger = logging.getLogger("WatchLearn")


@dataclass
class Action:
    action_id: str
    action_type: str
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "timestamp": self.timestamp,
            "details": self.details,
            "confidence": self.confidence,
        }


@dataclass
class LearnedPattern:
    pattern_id: str
    name: str
    description: str
    actions: List[Action]
    trigger: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    use_count: int = 0
    last_used: Optional[float] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "description": self.description,
            "actions": [a.to_dict() for a in self.actions],
            "trigger": self.trigger,
            "created_at": self.created_at,
            "use_count": self.use_count,
            "last_used": self.last_used,
            "tags": self.tags,
        }


@dataclass
class Skill:
    skill_id: str
    name: str
    description: str
    pattern_id: str
    script_content: str
    script_type: str
    created_at: float = field(default_factory=time.time)
    exported: bool = False

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "pattern_id": self.pattern_id,
            "script_content": self.script_content,
            "script_type": self.script_type,
            "created_at": self.created_at,
            "exported": self.exported,
        }


class WatchLearnEngine:
    def __init__(self, config: dict = None, skills_dir: str = None):
        self.config = config or {}
        self.skills_dir = Path(skills_dir or "C:/AlphaOmega/skills")
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        self._watching = False
        self._paused = False
        self._recording = False
        self._action_queue: queue.Queue = queue.Queue()
        self._current_session: List[Action] = []
        self._patterns: Dict[str, LearnedPattern] = {}
        self._skills: Dict[str, Skill] = {}
        self._session_start: Optional[float] = None

        self._action_callbacks: List = []
        self._pattern_callbacks: List = []

        self._min_actions_for_pattern = self.config.get("min_actions", 3)
        self._max_session_duration = self.config.get("max_session_duration", 300)

        self._load_patterns()
        self._load_skills()

    def _load_patterns(self):
        patterns_file = self.skills_dir / "patterns.json"
        if patterns_file.exists():
            try:
                data = json.loads(patterns_file.read_text())
                for p in data.get("patterns", []):
                    pattern = LearnedPattern(
                        pattern_id=p["pattern_id"],
                        name=p["name"],
                        description=p["description"],
                        actions=[Action(**a) for a in p["actions"]],
                        trigger=p.get("trigger"),
                        created_at=p["created_at"],
                        use_count=p["use_count"],
                        last_used=p.get("last_used"),
                        tags=p.get("tags", []),
                    )
                    self._patterns[pattern.pattern_id] = pattern
                logger.info(f"Loaded {len(self._patterns)} patterns")
            except Exception as e:
                logger.error(f"Failed to load patterns: {e}")

    def _save_patterns(self):
        patterns_file = self.skills_dir / "patterns.json"
        try:
            data = {
                "patterns": [p.to_dict() for p in self._patterns.values()],
                "last_saved": time.time(),
            }
            patterns_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save patterns: {e}")

    def _load_skills(self):
        skills_file = self.skills_dir / "skills.json"
        if skills_file.exists():
            try:
                data = json.loads(skills_file.read_text())
                for s in data.get("skills", []):
                    skill = Skill(**s)
                    self._skills[skill.skill_id] = skill
                logger.info(f"Loaded {len(self._skills)} skills")
            except Exception as e:
                logger.error(f"Failed to load skills: {e}")

    def _save_skills(self):
        skills_file = self.skills_dir / "skills.json"
        try:
            data = {
                "skills": [s.to_dict() for s in self._skills.values()],
                "last_saved": time.time(),
            }
            skills_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save skills: {e}")

    def start_watching(self) -> bool:
        if self._watching:
            return False

        self._watching = True
        self._paused = False

        thread = threading.Thread(target=self._watch_loop, daemon=True)
        thread.start()

        logger.info("Watch mode started")
        return True

    def stop_watching(self):
        self._watching = False
        if self._recording:
            self.stop_recording()
        self._save_patterns()
        logger.info("Watch mode stopped")

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def start_recording(self, session_name: str = None) -> str:
        if self._recording:
            return None

        self._recording = True
        self._current_session = []
        self._session_start = time.time()

        session_id = hashlib.md5(f"{session_name}{time.time()}".encode()).hexdigest()[
            :8
        ]
        logger.info(f"Recording started: {session_id}")
        return session_id

    def stop_recording(self) -> List[Action]:
        self._recording = False
        session = self._current_session.copy()
        self._current_session = []
        self._session_start = None

        logger.info(f"Recording stopped: {len(session)} actions")
        return session

    def record_action(
        self, action_type: str, details: Dict[str, Any]
    ) -> Optional[Action]:
        if not self._recording:
            return None

        action_id = hashlib.md5(f"{action_type}{time.time()}".encode()).hexdigest()[:12]
        action = Action(
            action_id=action_id,
            action_type=action_type,
            timestamp=time.time(),
            details=details,
        )

        self._current_session.append(action)
        self._action_queue.put(action)

        for callback in self._action_callbacks:
            try:
                callback(action)
            except Exception as e:
                logger.error(f"Action callback error: {e}")

        return action

    def _watch_loop(self):
        while self._watching:
            if self._paused:
                time.sleep(0.5)
                continue

            try:
                action = self._action_queue.get(timeout=1.0)
                self._analyze_action(action)
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"Watch loop error: {e}")

            time.sleep(0.1)

    def _analyze_action(self, action: Action):
        for pattern in self._patterns.values():
            if self._action_matches_pattern_start(action, pattern):
                logger.debug(f"Potential pattern match: {pattern.name}")

    def _action_matches_pattern_start(
        self, action: Action, pattern: LearnedPattern
    ) -> bool:
        if not pattern.actions:
            return False

        first_action = pattern.actions[0]
        return action.action_type == first_action.action_type

    def process_recording(self, actions: List[Action]) -> Optional[LearnedPattern]:
        if len(actions) < self._min_actions_for_pattern:
            logger.warning(f"Not enough actions for pattern: {len(actions)}")
            return None

        pattern_id = hashlib.md5(f"pattern{time.time()}".encode()).hexdigest()[:12]

        action_types = [a.action_type for a in actions]
        name = self._generate_pattern_name(action_types)

        pattern = LearnedPattern(
            pattern_id=pattern_id,
            name=name,
            description=f"Learned from {len(actions)} actions",
            actions=actions,
            tags=self._extract_tags(actions),
        )

        self._patterns[pattern_id] = pattern
        self._save_patterns()

        for callback in self._pattern_callbacks:
            try:
                callback(pattern)
            except Exception as e:
                logger.error(f"Pattern callback error: {e}")

        logger.info(f"Created pattern: {name}")
        return pattern

    def _generate_pattern_name(self, action_types: List[str]) -> str:
        type_counts: Dict[str, int] = {}
        for t in action_types:
            type_counts[t] = type_counts.get(t, 0) + 1

        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        top_types = [t[0] for t in sorted_types[:3]]

        return " - ".join(top_types).replace("_", " ").title()

    def _extract_tags(self, actions: List[Action]) -> List[str]:
        tags = set()
        for action in actions:
            tags.add(action.action_type)
            if "app" in action.details:
                tags.add(action.details["app"])
            if "category" in action.details:
                tags.add(action.details["category"])
        return list(tags)

    def create_script_from_pattern(
        self, pattern: LearnedPattern, script_type: str = "python"
    ) -> Optional[Skill]:
        if script_type == "python":
            script_content = self._generate_python_script(pattern)
        elif script_type == "powershell":
            script_content = self._generate_powershell_script(pattern)
        elif script_type == "workflow":
            script_content = self._generate_workflow_json(pattern)
        else:
            logger.error(f"Unknown script type: {script_type}")
            return None

        skill_id = hashlib.md5(
            f"skill{pattern.pattern_id}{time.time()}".encode()
        ).hexdigest()[:12]

        skill = Skill(
            skill_id=skill_id,
            name=pattern.name,
            description=pattern.description,
            pattern_id=pattern.pattern_id,
            script_content=script_content,
            script_type=script_type,
        )

        self._skills[skill_id] = skill
        self._save_skills()

        logger.info(f"Created skill: {skill.name} ({script_type})")
        return skill

    def _generate_python_script(self, pattern: LearnedPattern) -> str:
        lines = [
            f'"""',
            f"{pattern.name}",
            f"{pattern.description}",
            f"Auto-generated by Alpha Omega Watch & Learn",
            f'"""',
            f"",
            f"import time",
            f"import pyautogui",
            f"",
            f"def run_automation():",
        ]

        for action in pattern.actions:
            lines.extend(self._action_to_python(action))

        lines.extend(
            [
                f"",
                f'if __name__ == "__main__":',
                f"    run_automation()",
            ]
        )

        return "\n".join(lines)

    def _action_to_python(self, action: Action) -> List[str]:
        code = []
        action_type = action.action_type
        details = action.details

        if action_type == "click":
            x, y = details.get("x", 0), details.get("y", 0)
            code.append(f"    pyautogui.click({x}, {y})")

        elif action_type == "type":
            text = details.get("text", "")
            code.append(f'    pyautogui.write("{text}")')

        elif action_type == "key_press":
            key = details.get("key", "")
            code.append(f'    pyautogui.press("{key}")')

        elif action_type == "hotkey":
            keys = details.get("keys", [])
            code.append(f"    pyautogui.hotkey({', '.join(map(repr, keys))})")

        elif action_type == "scroll":
            amount = details.get("amount", 0)
            code.append(f"    pyautogui.scroll({amount})")

        elif action_type == "wait":
            duration = details.get("duration", 1)
            code.append(f"    time.sleep({duration})")

        elif action_type == "open_app":
            app = details.get("app", "")
            code.append(f'    os.system("start {app}")')

        code.append(f"    time.sleep(0.1)")
        return code

    def _generate_powershell_script(self, pattern: LearnedPattern) -> str:
        lines = [
            f"# {pattern.name}",
            f"# {pattern.description}",
            f"# Auto-generated by Alpha Omega Watch & Learn",
            f"",
            f"Add-Type -AssemblyName System.Windows.Forms",
            f"",
        ]

        for action in pattern.actions:
            lines.extend(self._action_to_powershell(action))

        return "\n".join(lines)

    def _action_to_powershell(self, action: Action) -> List[str]:
        code = []
        details = action.details

        if action.action_type == "click":
            x, y = details.get("x", 0), details.get("y", 0)
            code.append(
                f"[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({x}, {y})"
            )
            code.append(
                f'$mouse = New-Object System.Windows.Forms.MouseEventArgs("Left", 1, {x}, {y}, 0)'
            )

        elif action.action_type == "type":
            text = details.get("text", "")
            code.append(f'SendKeys::SendWait("{text}")')

        elif action.action_type == "wait":
            duration = details.get("duration", 1)
            code.append(f"Start-Sleep -Seconds {duration}")

        return code

    def _generate_workflow_json(self, pattern: LearnedPattern) -> str:
        workflow = {
            "name": pattern.name,
            "description": pattern.description,
            "trigger": pattern.trigger or "manual",
            "steps": [],
        }

        for i, action in enumerate(pattern.actions):
            step = {
                "step_id": i + 1,
                "action_type": action.action_type,
                "params": action.details,
            }
            workflow["steps"].append(step)

        return json.dumps(workflow, indent=2)

    def save_to_skill_library(self, pattern: LearnedPattern) -> str:
        skill = self.create_script_from_pattern(pattern, "python")
        if skill:
            return skill.skill_id
        return None

    def get_learned_skills(self) -> List[Skill]:
        return list(self._skills.values())

    def get_patterns(self) -> List[LearnedPattern]:
        return list(self._patterns.values())

    def delete_skill(self, skill_id: str) -> bool:
        if skill_id in self._skills:
            del self._skills[skill_id]
            self._save_skills()
            return True
        return False

    def delete_pattern(self, pattern_id: str) -> bool:
        if pattern_id in self._patterns:
            del self._patterns[pattern_id]
            self._save_patterns()
            return True
        return False

    def register_action_callback(self, callback):
        self._action_callbacks.append(callback)

    def register_pattern_callback(self, callback):
        self._pattern_callbacks.append(callback)

    def get_status(self) -> dict:
        return {
            "watching": self._watching,
            "recording": self._recording,
            "paused": self._paused,
            "current_session_actions": len(self._current_session),
            "patterns_count": len(self._patterns),
            "skills_count": len(self._skills),
        }
