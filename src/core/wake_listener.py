"""
ALPHA OMEGA - Wake Listener
Always-On Voice Wake Detection for Sleep Mode
Version: 2.0.0
"""

import os
import sys
import time
import logging
import threading
import queue
from pathlib import Path
from typing import Optional, Callable, List, Tuple
from dataclasses import dataclass
import json

logger = logging.getLogger("WakeListener")


@dataclass
class WakeEvent:
    wake_word: str
    confidence: float
    timestamp: float
    audio_data: Optional[bytes] = None

    def to_dict(self) -> dict:
        return {
            "wake_word": self.wake_word,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


class WakeListener:
    _is_windows = os.name == "nt"

    def __init__(self, config: dict = None):
        self.config = config or {}
        self._listening = False
        self._paused = False
        self._audio_queue = queue.Queue()
        self._wake_callbacks: List[Callable] = []
        self._error_callbacks: List[Callable] = []
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self._wake_word = self.config.get("wake_word", "hey alpha")
        self._sensitivity = self.config.get("wake_sensitivity", 0.8)
        self._sample_rate = int(self.config.get("sample_rate", "16000"))
        self._channels = 1
        self._chunk_size = 1024

        self._pyaudio = None
        self._audio_stream = None
        self._recognizer = None
        self._model = None

        self._low_power_mode = self.config.get("low_power_mode", True)
        self._buffer_seconds = self.config.get("buffer_seconds", 5)
        self._poll_interval = 0.1 if not self._low_power_mode else 0.5

    def start_listening(self) -> bool:
        if self._listening:
            logger.warning("Already listening")
            return False

        try:
            self._init_audio()
            self._init_recognizer()

            self._listening = True
            self._paused = False

            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()

            logger.info(f"Wake listener started - listening for '{self._wake_word}'")
            return True

        except Exception as e:
            logger.error(f"Failed to start listening: {e}")
            self._cleanup()
            return False

    def stop_listening(self) -> bool:
        self._listening = False

        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

        self._cleanup()
        logger.info("Wake listener stopped")
        return True

    def pause(self):
        self._paused = True
        logger.info("Wake listener paused")

    def resume(self):
        self._paused = False
        logger.info("Wake listener resumed")

    def is_active(self) -> bool:
        return self._listening and not self._paused

    def register_wake_callback(self, callback: Callable):
        self._wake_callbacks.append(callback)

    def register_error_callback(self, callback: Callable):
        self._error_callbacks.append(callback)

    def _init_audio(self):
        try:
            import pyaudio

            self._pyaudio = pyaudio.PyAudio()

            self._audio_stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=self._channels,
                rate=self._sample_rate,
                input=True,
                frames_per_buffer=self._chunk_size,
                input_device_index=self._get_device_index(),
            )

            logger.info(f"Audio initialized: {self._sample_rate}Hz")

        except ImportError:
            logger.error("PyAudio not installed. Run: pip install pyaudio")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize audio: {e}")
            raise

    def _get_device_index(self) -> Optional[int]:
        device_name = self.config.get("input_device")

        if not device_name or not self._pyaudio:
            return None

        for i in range(self._pyaudio.get_device_count()):
            info = self._pyaudio.get_device_info_by_index(i)
            if device_name.lower() in info["name"].lower():
                logger.info(f"Using device: {info['name']}")
                return i

        return None

    def _init_recognizer(self):
        engine = self.config.get("voice_engine", "whisper")

        if engine.startswith("whisper") or engine == "vosk":
            try:
                import speech_recognition as sr

                self._recognizer = sr.Recognizer()
                self._recognizer.energy_threshold = self._sensitivity * 300
                self._recognizer.dynamic_energy_threshold = True
                self._recognizer.pause_threshold = 0.5

                logger.info(f"Speech recognizer initialized: {engine}")

            except ImportError:
                logger.error("SpeechRecognition not installed")
                raise

    def _listen_loop(self):
        buffer = []
        buffer_duration = 0
        max_buffer_duration = self._buffer_seconds

        while self._listening:
            if self._paused:
                time.sleep(0.1)
                continue

            try:
                data = self._audio_stream.read(
                    self._chunk_size, exception_on_overflow=False
                )
                buffer.append(data)
                buffer_duration += self._chunk_size / self._sample_rate

                if buffer_duration >= max_buffer_duration:
                    self._process_buffer(b"".join(buffer))
                    buffer = []
                    buffer_duration = 0

            except OSError as e:
                if "Input overflowed" in str(e):
                    continue
                self._notify_error(e)
            except Exception as e:
                self._notify_error(e)

            time.sleep(self._poll_interval)

    def _process_buffer(self, audio_data: bytes):
        try:
            import speech_recognition as sr
            import io
            import wave

            audio_io = io.BytesIO()

            with wave.open(audio_io, "wb") as wf:
                wf.setnchannels(self._channels)
                wf.setsampwidth(self._pyaudio.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self._sample_rate)
                wf.writeframes(audio_data)

            audio_io.seek(0)
            audio_source = sr.AudioFile(audio_io)

            with audio_source as source:
                audio = self._recognizer.record(source)

            try:
                text = self._recognizer.recognize_google(audio).lower()
                logger.debug(f"Heard: {text}")

                if self._check_wake_word(text):
                    confidence = self._calculate_confidence(text)
                    event = WakeEvent(
                        wake_word=self._wake_word,
                        confidence=confidence,
                        timestamp=time.time(),
                        audio_data=audio_data,
                    )
                    self._notify_wake(event)

            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                logger.debug(f"Recognition service error: {e}")

        except Exception as e:
            logger.debug(f"Buffer processing error: {e}")

    def _check_wake_word(self, text: str) -> bool:
        wake_variants = [
            self._wake_word.lower(),
            self._wake_word.lower().replace(" ", ""),
            self._wake_word.lower().replace(" ", "-"),
        ]

        phonetic_variants = {
            "hey alpha": ["alpha", "hallo", "hello", "helo"],
            "raver": ["river", "rover", "waver"],
        }

        all_variants = wake_variants + phonetic_variants.get(
            self._wake_word.lower(), []
        )

        return any(v in text for v in all_variants)

    def _calculate_confidence(self, text: str) -> float:
        if self._wake_word.lower() in text:
            return 0.95
        elif self._wake_word.lower().replace(" ", "") in text.replace(" ", ""):
            return 0.85
        else:
            return 0.7

    def _notify_wake(self, event: WakeEvent):
        logger.info(f"Wake word detected: {event.wake_word} ({event.confidence:.2f})")

        for callback in self._wake_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Wake callback error: {e}")

    def _notify_error(self, error: Exception):
        logger.error(f"Listener error: {error}")

        for callback in self._error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"Error callback error: {e}")

    def _cleanup(self):
        if self._audio_stream:
            try:
                self._audio_stream.stop_stream()
                self._audio_stream.close()
            except Exception:
                pass
            self._audio_stream = None

        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except Exception:
                pass
            self._pyaudio = None

    def get_status(self) -> dict:
        return {
            "listening": self._listening,
            "paused": self._paused,
            "wake_word": self._wake_word,
            "sensitivity": self._sensitivity,
            "sample_rate": self._sample_rate,
            "low_power_mode": self._low_power_mode,
            "active": self.is_active(),
        }


class WakeListenerLite:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self._listening = False
        self._callbacks: List[Callable] = []

    def start_listening(self) -> bool:
        self._listening = True
        return True

    def stop_listening(self) -> bool:
        self._listening = False
        return True

    def register_wake_callback(self, callback: Callable):
        self._callbacks.append(callback)

    def is_active(self) -> bool:
        return self._listening

    def simulate_wake(self):
        if self._listening:
            event = WakeEvent(
                wake_word="simulated", confidence=1.0, timestamp=time.time()
            )
            for callback in self._callbacks:
                callback(event)
