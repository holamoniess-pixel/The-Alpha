"""
ALPHA OMEGA - Tutorial Processor
Process Video Tutorials for Learning
Version: 2.0.0
"""

import os
import sys
import re
import time
import logging
import json
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

logger = logging.getLogger("TutorialProcessor")


@dataclass
class TutorialStep:
    step_id: str
    step_number: int
    timestamp: float
    description: str
    actions: List[Dict[str, Any]] = field(default_factory=list)
    text_content: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "step_number": self.step_number,
            "timestamp": self.timestamp,
            "description": self.description,
            "actions": self.actions,
            "text_content": self.text_content,
            "confidence": self.confidence,
        }


@dataclass
class TutorialSteps:
    tutorial_id: str
    source: str
    title: str
    steps: List[TutorialStep]
    created_at: float = field(default_factory=time.time)
    summary: str = ""
    total_duration: float = 0.0

    def to_dict(self) -> dict:
        return {
            "tutorial_id": self.tutorial_id,
            "source": self.source,
            "title": self.title,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
            "summary": self.summary,
            "total_duration": self.total_duration,
        }


class TutorialProcessor:
    def __init__(self, config: dict = None, cache_dir: str = None):
        self.config = config or {}
        self.cache_dir = Path(cache_dir or "C:/AlphaOmega/tutorial_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._min_step_duration = self.config.get("min_step_duration", 2.0)
        self._max_steps = self.config.get("max_steps", 50)
        self._ocr_enabled = self.config.get("ocr_enabled", True)

        self._yt_dlp_path = self._find_yt_dlp()
        self._ffmpeg_path = self._find_ffmpeg()

    def _find_yt_dlp(self) -> Optional[str]:
        for cmd in ["yt-dlp", "youtube-dl"]:
            try:
                result = subprocess.run([cmd, "--version"], capture_output=True)
                if result.returncode == 0:
                    return cmd
            except FileNotFoundError:
                pass
        return None

    def _find_ffmpeg(self) -> Optional[str]:
        for cmd in ["ffmpeg", "ffmpeg.exe"]:
            try:
                result = subprocess.run([cmd, "-version"], capture_output=True)
                if result.returncode == 0:
                    return cmd
            except FileNotFoundError:
                pass
        return None

    def process_youtube(self, url: str) -> Optional[TutorialSteps]:
        if not self._yt_dlp_path:
            logger.error("yt-dlp not installed. Run: pip install yt-dlp")
            return None

        try:
            logger.info(f"Processing YouTube video: {url}")

            info_cmd = [self._yt_dlp_path, "--dump-json", "--no-download", url]
            info_result = subprocess.run(info_cmd, capture_output=True, text=True)

            if info_result.returncode != 0:
                logger.error(f"Failed to get video info: {info_result.stderr}")
                return None

            video_info = json.loads(info_result.stdout)
            title = video_info.get("title", "Unknown")
            duration = video_info.get("duration", 0)

            video_path = self.cache_dir / f"{video_info.get('id', 'video')}.mp4"

            if not video_path.exists():
                download_cmd = [
                    self._yt_dlp_path,
                    "-f",
                    "best[height<=720]",
                    "-o",
                    str(video_path),
                    url,
                ]
                download_result = subprocess.run(
                    download_cmd, capture_output=True, text=True
                )

                if download_result.returncode != 0:
                    logger.error(f"Download failed: {download_result.stderr}")
                    return None

            return self._process_video_file(video_path, title, url)

        except Exception as e:
            logger.error(f"YouTube processing failed: {e}")
            return None

    def process_local_video(self, path: str) -> Optional[TutorialSteps]:
        video_path = Path(path)
        if not video_path.exists():
            logger.error(f"Video not found: {path}")
            return None

        return self._process_video_file(video_path, video_path.stem, f"local:{path}")

    def _process_video_file(
        self, video_path: Path, title: str, source: str
    ) -> Optional[TutorialSteps]:
        if not self._ffmpeg_path:
            logger.error("ffmpeg not found")
            return None

        try:
            frames_dir = self.cache_dir / f"frames_{int(time.time())}"
            frames_dir.mkdir(exist_ok=True)

            extract_cmd = [
                self._ffmpeg_path,
                "-i",
                str(video_path),
                "-vf",
                f"fps=1",
                str(frames_dir / "frame_%04d.png"),
            ]

            subprocess.run(extract_cmd, capture_output=True)

            frames = sorted(frames_dir.glob("frame_*.png"))

            steps = self._extract_steps_from_frames(frames)

            summary = self._generate_summary(steps)

            tutorial_id = hashlib.md5(f"{source}{time.time()}".encode()).hexdigest()[
                :12
            ]

            tutorial = TutorialSteps(
                tutorial_id=tutorial_id,
                source=source,
                title=title,
                steps=steps,
                summary=summary,
                total_duration=len(frames),
            )

            self._save_tutorial(tutorial)

            for frame in frames:
                frame.unlink()
            frames_dir.rmdir()

            logger.info(f"Processed tutorial: {title} ({len(steps)} steps)")
            return tutorial

        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            return None

    def _extract_steps_from_frames(self, frames: List[Path]) -> List[TutorialStep]:
        steps = []
        prev_text = ""
        step_count = 0

        for i, frame in enumerate(frames):
            if step_count >= self._max_steps:
                break

            text_content = self._extract_text_from_frame(frame)

            if text_content and text_content != prev_text:
                step_count += 1
                step_id = hashlib.md5(f"step{i}{text_content}".encode()).hexdigest()[:8]

                step = TutorialStep(
                    step_id=step_id,
                    step_number=step_count,
                    timestamp=i,
                    description=self._generate_step_description(text_content),
                    text_content=text_content,
                    confidence=self._calculate_confidence(text_content),
                )

                actions = self._infer_actions(text_content)
                if actions:
                    step.actions = actions

                steps.append(step)
                prev_text = text_content

        return steps

    def _extract_text_from_frame(self, frame_path: Path) -> str:
        if not self._ocr_enabled:
            return ""

        try:
            import pytesseract
            from PIL import Image

            img = Image.open(frame_path)
            text = pytesseract.image_to_string(img)
            return text.strip()

        except ImportError:
            logger.debug("pytesseract not installed")
            return ""
        except Exception as e:
            logger.debug(f"OCR failed: {e}")
            return ""

    def _generate_step_description(self, text: str) -> str:
        text = " ".join(text.split())

        if len(text) > 100:
            sentences = re.split(r"[.!?]", text)
            if sentences:
                return sentences[0].strip()[:100]

        return text[:100]

    def _calculate_confidence(self, text: str) -> float:
        if not text:
            return 0.0

        confidence = 0.5

        action_keywords = [
            "click",
            "press",
            "type",
            "select",
            "open",
            "close",
            "drag",
            "scroll",
        ]
        for keyword in action_keywords:
            if keyword in text.lower():
                confidence += 0.1

        if len(text) > 20:
            confidence += 0.1

        return min(confidence, 1.0)

    def _infer_actions(self, text: str) -> List[Dict[str, Any]]:
        actions = []
        text_lower = text.lower()

        click_patterns = [
            (r"click (?:on )?(?:the )?['\"]?(\w+)['\"]?", "click"),
            (r"click (?:on )?(?:the )?(\w+) button", "click_button"),
        ]

        for pattern, action_type in click_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                actions.append(
                    {
                        "type": action_type,
                        "target": match,
                        "source": "inferred",
                    }
                )

        type_patterns = [
            (r"type ['\"]([^'\"]+)['\"]", "type"),
            (r"enter ['\"]([^'\"]+)['\"]", "type"),
        ]

        for pattern, action_type in type_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                actions.append(
                    {
                        "type": action_type,
                        "text": match,
                        "source": "inferred",
                    }
                )

        key_patterns = [
            (r"press (\w+)", "key_press"),
            (r"hit (\w+)", "key_press"),
        ]

        for pattern, action_type in key_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if len(match) <= 15:
                    actions.append(
                        {
                            "type": action_type,
                            "key": match.upper(),
                            "source": "inferred",
                        }
                    )

        return actions[:5]

    def _generate_summary(self, steps: List[TutorialStep]) -> str:
        if not steps:
            return ""

        summaries = [f"{i + 1}. {s.description}" for i, s in enumerate(steps[:10])]

        if len(steps) > 10:
            summaries.append(f"... and {len(steps) - 10} more steps")

        return "\n".join(summaries)

    def _save_tutorial(self, tutorial: TutorialSteps):
        tutorial_file = self.cache_dir / f"{tutorial.tutorial_id}.json"
        tutorial_file.write_text(json.dumps(tutorial.to_dict(), indent=2))

    def load_tutorial(self, tutorial_id: str) -> Optional[TutorialSteps]:
        tutorial_file = self.cache_dir / f"{tutorial_id}.json"

        if not tutorial_file.exists():
            return None

        try:
            data = json.loads(tutorial_file.read_text())
            return TutorialSteps(
                tutorial_id=data["tutorial_id"],
                source=data["source"],
                title=data["title"],
                steps=[TutorialStep(**s) for s in data["steps"]],
                created_at=data["created_at"],
                summary=data["summary"],
                total_duration=data["total_duration"],
            )
        except Exception as e:
            logger.error(f"Failed to load tutorial: {e}")
            return None

    def create_automation_from_tutorial(
        self, tutorial: TutorialSteps
    ) -> Dict[str, Any]:
        workflow = {
            "name": tutorial.title,
            "description": f"Learned from: {tutorial.source}",
            "tutorial_id": tutorial.tutorial_id,
            "created_at": time.time(),
            "steps": [],
        }

        for step in tutorial.steps:
            if step.actions:
                workflow_step = {
                    "step_number": step.step_number,
                    "description": step.description,
                    "actions": step.actions,
                    "confidence": step.confidence,
                }
                workflow["steps"].append(workflow_step)

        return workflow

    def list_tutorials(self) -> List[Dict[str, Any]]:
        tutorials = []

        for tutorial_file in self.cache_dir.glob("*.json"):
            try:
                data = json.loads(tutorial_file.read_text())
                tutorials.append(
                    {
                        "tutorial_id": data["tutorial_id"],
                        "title": data["title"],
                        "source": data["source"],
                        "step_count": len(data["steps"]),
                        "created_at": data["created_at"],
                    }
                )
            except Exception:
                pass

        return sorted(tutorials, key=lambda x: x["created_at"], reverse=True)

    def delete_tutorial(self, tutorial_id: str) -> bool:
        tutorial_file = self.cache_dir / f"{tutorial_id}.json"

        if tutorial_file.exists():
            tutorial_file.unlink()
            return True

        return False

    def get_status(self) -> dict:
        return {
            "yt_dlp_available": self._yt_dlp_path is not None,
            "ffmpeg_available": self._ffmpeg_path is not None,
            "ocr_enabled": self._ocr_enabled,
            "cache_dir": str(self.cache_dir),
            "cached_tutorials": len(list(self.cache_dir.glob("*.json"))),
        }
