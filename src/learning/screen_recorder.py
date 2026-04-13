"""
ALPHA OMEGA - Screen Recorder
Privacy-First Recording for Watch & Learn
Version: 2.0.0
"""

import os
import sys
import time
import logging
import threading
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import queue
import base64

logger = logging.getLogger("ScreenRecorder")


@dataclass
class Recording:
    recording_id: str
    start_time: float
    end_time: Optional[float] = None
    frames: List[bytes] = field(default_factory=list)
    frame_times: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    blurs_applied: int = 0

    def to_dict(self) -> dict:
        return {
            "recording_id": self.recording_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "frame_count": len(self.frames),
            "duration": (self.end_time or time.time()) - self.start_time,
            "metadata": self.metadata,
            "blurs_applied": self.blurs_applied,
        }


@dataclass
class PrivacySettings:
    blur_passwords: bool = True
    blur_inputs: bool = True
    excluded_apps: List[str] = field(
        default_factory=lambda: ["Password Manager", "Banking"]
    )
    excluded_regions: List[Tuple[int, int, int, int]] = field(default_factory=list)
    auto_detect_sensitive: bool = True
    prompt_before_recording: bool = True
    delete_after_processing: bool = True
    max_retention_hours: int = 24


class ScreenRecorder:
    _is_windows = os.name == "nt"

    def __init__(self, config: dict = None, recordings_dir: str = None):
        self.config = config or {}
        self.recordings_dir = Path(recordings_dir or "C:/AlphaOmega/recordings")
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

        self._recording = False
        self._paused = False
        self._current_recording: Optional[Recording] = None
        self._frame_queue: queue.Queue = queue.Queue()
        self._thread: Optional[threading.Thread] = None

        self._privacy = PrivacySettings(
            **{
                k: v
                for k, v in self.config.get("privacy", {}).items()
                if k in PrivacySettings.__dataclass_fields__
            }
        )

        self._fps = self.config.get("fps", 5)
        self._frame_interval = 1.0 / self._fps
        self._max_frames = self.config.get("max_frames", 3000)

        self._mss = None
        self._ocr = None

        self._consent_given = False
        self._consent_dialog_active = False

    def get_privacy_settings(self) -> PrivacySettings:
        return self._privacy

    def set_privacy_settings(self, settings: Dict[str, Any]):
        for key, value in settings.items():
            if hasattr(self._privacy, key):
                setattr(self._privacy, key, value)

    def request_permission(self) -> Tuple[bool, str]:
        if self._consent_dialog_active:
            return False, "Permission dialog already active"

        if self._privacy.prompt_before_recording and not self._consent_given:
            self._consent_dialog_active = True
            return False, "WAITING_FOR_CONSENT"

        return True, "Permission granted"

    def grant_permission(self):
        self._consent_given = True
        self._consent_dialog_active = False

    def deny_permission(self):
        self._consent_given = False
        self._consent_dialog_active = False

    def start_recording(self, metadata: Dict[str, Any] = None) -> Optional[str]:
        if self._recording:
            logger.warning("Already recording")
            return None

        if self._privacy.prompt_before_recording:
            permitted, msg = self.request_permission()
            if not permitted:
                if msg == "WAITING_FOR_CONSENT":
                    return "WAITING_FOR_CONSENT"
                return None

        try:
            import mss

            self._mss = mss.mss()
        except ImportError:
            logger.error("mss not installed. Run: pip install mss")
            return None

        recording_id = f"rec_{int(time.time() * 1000)}"
        self._current_recording = Recording(
            recording_id=recording_id,
            start_time=time.time(),
            metadata=metadata or {},
        )

        self._recording = True
        self._paused = False

        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

        logger.info(f"Recording started: {recording_id}")
        return recording_id

    def stop_recording(self) -> Optional[Recording]:
        if not self._recording:
            return None

        self._recording = False
        self._paused = False

        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

        if self._current_recording:
            self._current_recording.end_time = time.time()
            self._save_recording(self._current_recording)

        recording = self._current_recording
        self._current_recording = None

        self._consent_given = False
        logger.info(
            f"Recording stopped: {recording.recording_id if recording else 'none'}"
        )

        return recording

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def is_recording(self) -> bool:
        return self._recording

    def _record_loop(self):
        while self._recording:
            if self._paused:
                time.sleep(0.1)
                continue

            try:
                frame = self._capture_frame()

                if frame and self._current_recording:
                    if self._privacy.auto_detect_sensitive:
                        frame, blurred = self._apply_privacy_filters(frame)
                        if blurred:
                            self._current_recording.blurs_applied += 1

                    self._current_recording.frames.append(frame)
                    self._current_recording.frame_times.append(time.time())

                    if len(self._current_recording.frames) >= self._max_frames:
                        logger.info("Max frames reached, stopping recording")
                        break

            except Exception as e:
                logger.error(f"Capture error: {e}")

            time.sleep(self._frame_interval)

    def _capture_frame(self) -> Optional[bytes]:
        if not self._mss:
            return None

        try:
            monitor = self._mss.monitors[1]
            screenshot = self._mss.grab(monitor)

            import io
            from PIL import Image

            img = Image.frombytes(
                "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
            )

            buffer = io.BytesIO()
            img.save(buffer, format="PNG", optimize=True)
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Frame capture failed: {e}")
            return None

    def _apply_privacy_filters(self, frame_data: bytes) -> Tuple[bytes, bool]:
        blurred = False

        if not self._privacy.blur_passwords and not self._privacy.blur_inputs:
            return frame_data, blurred

        try:
            from PIL import Image, ImageFilter
            import io

            img = Image.open(io.BytesIO(frame_data))

            if self._privacy.excluded_regions:
                for region in self._privacy.excluded_regions:
                    x, y, w, h = region
                    box = img.crop((x, y, x + w, y + h))
                    box = box.filter(ImageFilter.GaussianBlur(20))
                    img.paste(box, (x, y))
                    blurred = True

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue(), blurred

        except Exception as e:
            logger.debug(f"Privacy filter error: {e}")
            return frame_data, blurred

    def _save_recording(self, recording: Recording):
        try:
            recording_dir = self.recordings_dir / recording.recording_id
            recording_dir.mkdir(exist_ok=True)

            metadata = {
                **recording.metadata,
                "recording_id": recording.recording_id,
                "start_time": recording.start_time,
                "end_time": recording.end_time,
                "frame_count": len(recording.frames),
                "blurs_applied": recording.blurs_applied,
            }

            (recording_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

            for i, (frame_data, frame_time) in enumerate(
                zip(recording.frames, recording.frame_times)
            ):
                frame_path = recording_dir / f"frame_{i:05d}.png"
                frame_path.write_bytes(frame_data)

            logger.info(f"Recording saved: {recording.recording_id}")

        except Exception as e:
            logger.error(f"Failed to save recording: {e}")

    def load_recording(self, recording_id: str) -> Optional[Recording]:
        recording_dir = self.recordings_dir / recording_id

        if not recording_dir.exists():
            return None

        try:
            metadata = json.loads((recording_dir / "metadata.json").read_text())

            frames = []
            frame_times = []

            for frame_path in sorted(recording_dir.glob("frame_*.png")):
                frames.append(frame_path.read_bytes())

            recording = Recording(
                recording_id=recording_id,
                start_time=metadata["start_time"],
                end_time=metadata.get("end_time"),
                frames=frames,
                frame_times=frame_times,
                metadata=metadata,
                blurs_applied=metadata.get("blurs_applied", 0),
            )

            return recording

        except Exception as e:
            logger.error(f"Failed to load recording: {e}")
            return None

    def delete_recording(self, recording_id: str) -> bool:
        recording_dir = self.recordings_dir / recording_id

        if not recording_dir.exists():
            return False

        try:
            import shutil

            shutil.rmtree(recording_dir)
            logger.info(f"Recording deleted: {recording_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete recording: {e}")
            return False

    def list_recordings(self) -> List[dict]:
        recordings = []

        for rec_dir in self.recordings_dir.iterdir():
            if rec_dir.is_dir():
                meta_path = rec_dir / "metadata.json"
                if meta_path.exists():
                    try:
                        meta = json.loads(meta_path.read_text())
                        recordings.append(meta)
                    except Exception:
                        pass

        return sorted(recordings, key=lambda x: x["start_time"], reverse=True)

    def cleanup_old_recordings(self, max_age_hours: int = None):
        max_age = max_age_hours or self._privacy.max_retention_hours
        cutoff = time.time() - (max_age * 3600)

        for rec_dir in self.recordings_dir.iterdir():
            if rec_dir.is_dir():
                meta_path = rec_dir / "metadata.json"
                if meta_path.exists():
                    try:
                        meta = json.loads(meta_path.read_text())
                        if meta.get("start_time", 0) < cutoff:
                            self.delete_recording(rec_dir.name)
                    except Exception:
                        pass

    def get_status(self) -> dict:
        return {
            "recording": self._recording,
            "paused": self._paused,
            "current_frames": len(self._current_recording.frames)
            if self._current_recording
            else 0,
            "fps": self._fps,
            "privacy_enabled": self._privacy.auto_detect_sensitive,
            "consent_given": self._consent_given,
        }
