#!/usr/bin/env python3
"""
ALPHA OMEGA - HIGH-PERFORMANCE VOICE SYSTEM
Low-latency wake word detection and speech recognition
Version: 2.0.0
"""

import asyncio
import audioop
import json
import logging
import math
import os
import queue
import struct
import threading
import time
import wave
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import deque
import base64
import io

try:
    import pyaudio

    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False
    logging.warning("PyAudio not available")

try:
    import speech_recognition as sr

    HAS_SR = True
except ImportError:
    HAS_SR = False
    logging.warning("SpeechRecognition not available")

try:
    import pyttsx3

    HAS_TTS = True
except ImportError:
    HAS_TTS = False
    logging.warning("pyttsx3 not available")

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logging.warning("NumPy not available")

try:
    from vosk import Model, SpkModel, KaldiRecognizer

    HAS_VOSK = True
except ImportError:
    HAS_VOSK = False
    logging.warning("Vosk not available - offline recognition disabled")


class VoiceState:
    IDLE = "idle"
    LISTENING_WAKE = "listening_wake"
    LISTENING_COMMAND = "listening_command"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class AudioChunk:
    data: bytes
    timestamp: float = field(default_factory=time.time)
    energy: float = 0.0
    is_speech: bool = False


@dataclass
class VoiceCommand:
    text: str
    confidence: float
    timestamp: float
    is_wake_word: bool = False
    speaker_id: Optional[str] = None


class AudioBuffer:
    def __init__(self, max_seconds: float = 30.0, sample_rate: int = 16000):
        self.max_seconds = max_seconds
        self.sample_rate = sample_rate
        self.max_chunks = int(max_seconds * sample_rate / 1024)
        self._buffer = deque(maxlen=self.max_chunks)
        self._lock = threading.Lock()

    def append(self, chunk: AudioChunk):
        with self._lock:
            self._buffer.append(chunk)

    def get_recent(self, seconds: float) -> List[AudioChunk]:
        with self._lock:
            cutoff = time.time() - seconds
            return [c for c in self._buffer if c.timestamp >= cutoff]

    def get_all(self) -> bytes:
        with self._lock:
            return b"".join(c.data for c in self._buffer)

    def clear(self):
        with self._lock:
            self._buffer.clear()


class VoiceActivityDetector:
    def __init__(self, sample_rate: int = 16000, frame_size: int = 1024):
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self.energy_threshold = 500
        self.silence_threshold = 3
        self.speech_threshold = 5
        self._energy_history = deque(maxlen=100)
        self._speech_frames = 0
        self._silence_frames = 0
        self._is_speech = False
        self._adaptive_threshold = True
        self._ambient_energy = 100

    def update_threshold(self):
        if self._energy_history:
            avg_energy = sum(self._energy_history) / len(self._energy_history)
            self.energy_threshold = max(300, min(avg_energy * 3, 3000))
            self._ambient_energy = avg_energy

    def is_speech(self, audio_data: bytes) -> bool:
        if HAS_NUMPY:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            energy = np.sqrt(np.mean(audio_array.astype(np.float64) ** 2))
        else:
            energy = abs(audioop.rms(audio_data, 2))

        self._energy_history.append(energy)

        if self._adaptive_threshold and len(self._energy_history) % 20 == 0:
            self.update_threshold()

        if energy > self.energy_threshold:
            self._speech_frames += 1
            self._silence_frames = 0
        else:
            self._silence_frames += 1
            self._speech_frames = max(0, self._speech_frames - 1)

        if self._speech_frames > self.speech_threshold:
            self._is_speech = True
        elif self._silence_frames > self.silence_threshold:
            self._is_speech = False

        return self._is_speech

    def get_energy(self, audio_data: bytes) -> float:
        if HAS_NUMPY:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            return float(np.sqrt(np.mean(audio_array.astype(np.float64) ** 2)))
        return float(abs(audioop.rms(audio_data, 2)))


class WakeWordDetector:
    def __init__(self, wake_word: str, sample_rate: int = 16000):
        self.wake_word = wake_word.lower()
        self.sample_rate = sample_rate
        self.wake_word_variants = self._generate_variants(wake_word)
        self._recent_transcripts = deque(maxlen=10)
        self._detection_count = 0
        self._last_detection = 0
        self._cooldown = 2.0

    def _generate_variants(self, phrase: str) -> List[str]:
        variants = [phrase.lower()]
        words = phrase.lower().split()
        variants.append("".join(words))
        variants.append(" ".join(w[0] for w in words))
        for word in words:
            variants.append(word)
        return variants

    def detect(self, text: str) -> bool:
        now = time.time()
        if now - self._last_detection < self._cooldown:
            return False

        text_lower = text.lower().strip()
        self._recent_transcripts.append(text_lower)

        for variant in self.wake_word_variants:
            if variant in text_lower:
                self._detection_count += 1
                self._last_detection = now
                return True

        combined = " ".join(self._recent_transcripts)
        for variant in self.wake_word_variants:
            if variant in combined and len(combined) < len(variant) + 50:
                self._detection_count += 1
                self._last_detection = now
                return True

        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "detections": self._detection_count,
            "last_detection": self._last_detection,
            "wake_word": self.wake_word,
        }


class SpeechRecognizer:
    def __init__(self, config: Dict[str, Any], offline: bool = True):
        self.config = config
        self.offline = offline
        self.sample_rate = config.get("sample_rate", 16000)
        self.language = config.get("language", "en-US")
        self.timeout = config.get("timeout", 5)
        self.logger = logging.getLogger("SpeechRecognizer")

        self._online_recognizer = None
        self._offline_model = None
        self._offline_recognizer = None

        self._stats = {
            "recognitions": 0,
            "successful": 0,
            "failed": 0,
            "avg_time_ms": 0,
        }

    async def initialize(self) -> bool:
        self.logger.info("Initializing Speech Recognizer...")

        if HAS_SR:
            self._online_recognizer = sr.Recognizer()
            self._online_recognizer.energy_threshold = 300
            self._online_recognizer.dynamic_energy_threshold = True
            self._online_recognizer.pause_threshold = 0.8
            self.logger.info("Online recognizer initialized (Google Speech)")

        if HAS_VOSK and self.offline:
            model_path = "model-small"
            spk_path = "model-spk"

            if os.path.exists(spk_path):
                self._offline_model = SpkModel(spk_path)
                self._offline_recognizer = KaldiRecognizer(
                    Model(model_path) if os.path.exists(model_path) else None,
                    self.sample_rate,
                    self._offline_model,
                )
                self.logger.info(
                    "Offline Vosk recognizer initialized (with speaker model)"
                )
            elif os.path.exists(model_path):
                self._offline_model = Model(model_path)
                self._offline_recognizer = KaldiRecognizer(
                    self._offline_model, self.sample_rate
                )
                self.logger.info("Offline Vosk recognizer initialized")
            else:
                self.logger.warning(
                    "Vosk models not found - offline recognition disabled"
                )

        return True

    async def recognize(self, audio_data: bytes) -> Dict[str, Any]:
        start_time = time.time()
        self._stats["recognitions"] += 1

        if self._offline_recognizer:
            result = await self._recognize_offline(audio_data)
        elif self._online_recognizer:
            result = await self._recognize_online(audio_data)
        else:
            self._stats["failed"] += 1
            return {
                "text": "",
                "confidence": 0.0,
                "success": False,
                "error": "No speech recognizer available",
            }

        processing_time = (time.time() - start_time) * 1000
        if result.get("success"):
            self._stats["successful"] += 1
        else:
            self._stats["failed"] += 1

        self._stats["avg_time_ms"] = (
            self._stats["avg_time_ms"] * (self._stats["recognitions"] - 1)
            + processing_time
        ) / self._stats["recognitions"]

        result["processing_time_ms"] = processing_time
        return result

    async def _recognize_offline(self, audio_data: bytes) -> Dict[str, Any]:
        try:
            self._offline_recognizer.AcceptWaveform(audio_data)
            result = json.loads(self._offline_recognizer.FinalResult())

            text = result.get("text", "")
            confidence = 1.0

            if "result" in result and result["result"]:
                confidences = [w.get("conf", 0) for w in result["result"]]
                confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return {
                "text": text,
                "confidence": confidence,
                "success": bool(text),
                "speaker_vector": result.get("spk"),
                "offline": True,
            }
        except Exception as e:
            self.logger.error(f"Offline recognition error: {e}")
            return {"text": "", "confidence": 0.0, "success": False, "error": str(e)}

    async def _recognize_online(self, audio_data: bytes) -> Dict[str, Any]:
        if not HAS_SR:
            return {
                "text": "",
                "confidence": 0.0,
                "success": False,
                "error": "SpeechRecognition not available",
            }

        try:
            audio = sr.AudioData(audio_data, self.sample_rate, 2)
            text = self._online_recognizer.recognize_google(
                audio, language=self.language
            )
            return {"text": text, "confidence": 0.9, "success": True, "offline": False}
        except sr.UnknownValueError:
            return {
                "text": "",
                "confidence": 0.0,
                "success": False,
                "error": "Could not understand",
            }
        except sr.RequestError as e:
            return {"text": "", "confidence": 0.0, "success": False, "error": str(e)}
        except Exception as e:
            self.logger.error(f"Online recognition error: {e}")
            return {"text": "", "confidence": 0.0, "success": False, "error": str(e)}


class VoiceAuthenticator:
    def __init__(self, threshold: float = 0.65):
        self.threshold = threshold
        self.users_db_path = Path("data/voice_users.json")
        self.users_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.users: Dict[str, Dict] = {}
        self._load_db()
        self.logger = logging.getLogger("VoiceAuthenticator")

    def _load_db(self):
        if self.users_db_path.exists():
            try:
                with open(self.users_db_path, "r") as f:
                    self.users = json.load(f)
            except Exception:
                self.users = {}

    def _save_db(self):
        with open(self.users_db_path, "w") as f:
            json.dump(self.users, f, indent=2)

    def enroll(self, user_id: str, speaker_vector: List[float]) -> bool:
        vector_hash = hashlib.sha256(json.dumps(speaker_vector).encode()).hexdigest()
        self.users[user_id] = {
            "vector": speaker_vector,
            "hash": vector_hash,
            "enrolled_at": time.time(),
            "samples": 1,
        }
        self._save_db()
        return True

    def verify(
        self, speaker_vector: List[float], claimed_user: str = "admin"
    ) -> Dict[str, Any]:
        if claimed_user not in self.users:
            return {"verified": False, "score": 0.0, "reason": "User not enrolled"}

        enrolled_vector = self.users[claimed_user]["vector"]

        if HAS_NUMPY:
            v1 = np.array(speaker_vector)
            v2 = np.array(enrolled_vector)
            score = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
        else:
            score = sum(a * b for a, b in zip(speaker_vector, enrolled_vector))
            norm1 = math.sqrt(sum(a * a for a in speaker_vector))
            norm2 = math.sqrt(sum(b * b for b in enrolled_vector))
            score = score / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0

        verified = score > self.threshold

        return {
            "verified": verified,
            "score": score,
            "threshold": self.threshold,
            "user": claimed_user if verified else None,
        }

    def get_users(self) -> List[str]:
        return list(self.users.keys())


class TextToSpeech:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rate = config.get("rate", 180)
        self.volume = config.get("volume", 0.9)
        self.voice_id = config.get("voice_id", None)
        self.engine = None
        self._lock = threading.Lock()
        self._speaking = False
        self.logger = logging.getLogger("TextToSpeech")

    async def initialize(self) -> bool:
        if HAS_TTS:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", self.rate)
            self.engine.setProperty("volume", self.volume)
            voices = self.engine.getProperty("voices")
            if voices and self.voice_id is not None:
                self.engine.setProperty("voice", voices[self.voice_id].id)
            self.logger.info("TTS engine initialized")
            return True
        else:
            self.logger.warning("TTS not available - pyttsx3 not installed")
            return False

    async def speak(self, text: str, blocking: bool = False) -> bool:
        if not self.engine or not text:
            return False

        with self._lock:
            self._speaking = True

            def _speak():
                self.engine.say(text)
                self.engine.runAndWait()

            if blocking:
                _speak()
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, _speak)

            self._speaking = False
            return True

    def stop(self):
        if self.engine:
            self.engine.stop()
            self._speaking = False

    def is_speaking(self) -> bool:
        return self._speaking


class VoiceSystem:
    def __init__(self, config: Dict[str, Any], wake_word: str = "hey alpha"):
        self.config = config
        self.wake_word = wake_word
        self.logger = logging.getLogger("VoiceSystem")

        self.sample_rate = config.get("sample_rate", 16000)
        self.chunk_size = config.get("chunk_size", 1024)
        self.channels = 1

        self.state = VoiceState.IDLE

        self.audio_buffer = AudioBuffer(max_seconds=30.0, sample_rate=self.sample_rate)
        self.vad = VoiceActivityDetector(
            sample_rate=self.sample_rate, frame_size=self.chunk_size
        )
        self.wake_detector = WakeWordDetector(wake_word, self.sample_rate)
        self.recognizer = SpeechRecognizer(config, offline=config.get("offline", True))
        self.authenticator = VoiceAuthenticator(
            threshold=config.get("voice_auth_threshold", 0.65)
        )
        self.tts = TextToSpeech(config)

        self._audio = None
        self._audio_stream = None
        self._audio_queue = queue.Queue()
        self._command_queue = queue.Queue()

        self._command_handler: Optional[Callable] = None
        self._running = False
        self._listening = False

        self._stats = {
            "total_chunks": 0,
            "speech_chunks": 0,
            "commands_detected": 0,
            "wake_words_detected": 0,
            "uptime": 0,
        }

        self._start_time = 0

    async def initialize(self) -> bool:
        self.logger.info("Initializing Voice System...")

        if not HAS_PYAUDIO:
            self.logger.error("PyAudio not available - voice system cannot function")
            return False

        await self.recognizer.initialize()
        await self.tts.initialize()

        try:
            self._audio = pyaudio.PyAudio()

            device_count = self._audio.get_device_count()
            input_device = None

            for i in range(device_count):
                info = self._audio.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    input_device = i
                    break

            if input_device is None:
                self.logger.error("No input audio device found")
                return False

            self._input_device = input_device
            self.logger.info(
                f"Using audio device: {self._audio.get_device_info_by_index(input_device)['name']}"
            )

            return True

        except Exception as e:
            self.logger.error(f"Audio initialization failed: {e}")
            return False

    def set_command_handler(self, handler: Callable):
        self._command_handler = handler

    async def start_listening(self):
        self.logger.info("Starting voice listening loop...")
        self._running = True
        self._start_time = time.time()

        try:
            self._audio_stream = self._audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self._input_device,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback,
            )

            self._audio_stream.start_stream()
            self.state = VoiceState.LISTENING_WAKE

            while self._running:
                try:
                    if not self._audio_queue.empty():
                        audio_chunk = self._audio_queue.get()
                        await self._process_audio_chunk(audio_chunk)

                    if not self._command_queue.empty():
                        command = self._command_queue.get()
                        if self._command_handler:
                            response = await self._command_handler(command.text)
                            if response:
                                await self.tts.speak(response)

                    await asyncio.sleep(0.01)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Listening loop error: {e}")
                    await asyncio.sleep(0.1)

        except Exception as e:
            self.logger.error(f"Audio stream error: {e}")
        finally:
            await self.stop()

    def _audio_callback(self, in_data, frame_count, time_info, status):
        chunk = AudioChunk(data=in_data)
        chunk.energy = self.vad.get_energy(in_data)
        chunk.is_speech = self.vad.is_speech(in_data)

        self.audio_buffer.append(chunk)
        self._audio_queue.put(chunk)

        self._stats["total_chunks"] += 1
        if chunk.is_speech:
            self._stats["speech_chunks"] += 1

        return (None, pyaudio.paContinue)

    async def _process_audio_chunk(self, chunk: AudioChunk):
        if self.state == VoiceState.LISTENING_WAKE:
            if chunk.is_speech:
                recent = self.audio_buffer.get_recent(2.0)
                audio_data = b"".join(c.data for c in recent)

                result = await self.recognizer.recognize(audio_data)

                if result.get("success") and result.get("text"):
                    text = result["text"]

                    if self.wake_detector.detect(text):
                        self.logger.info(f"Wake word detected!")
                        self._stats["wake_words_detected"] += 1
                        self.state = VoiceState.LISTENING_COMMAND

                        if self.config.get("play_chime", True):
                            self._play_chime()

                        await self._listen_for_command()

        elif self.state == VoiceState.PROCESSING:
            pass

    async def _listen_for_command(self):
        self.logger.info("Listening for command...")

        command_audio = []
        silence_count = 0
        max_silence = int(
            self.config.get("command_timeout", 10) * self.sample_rate / self.chunk_size
        )

        start_time = time.time()
        timeout = self.config.get("command_timeout", 10)

        while time.time() - start_time < timeout:
            if not self._audio_queue.empty():
                chunk = self._audio_queue.get()
                command_audio.append(chunk.data)

                if not chunk.is_speech:
                    silence_count += 1
                    if silence_count > max_silence / 4:
                        break
                else:
                    silence_count = 0

            await asyncio.sleep(0.01)

        audio_data = b"".join(command_audio)

        if len(audio_data) > self.chunk_size * 3:
            self.state = VoiceState.PROCESSING

            result = await self.recognizer.recognize(audio_data)

            if result.get("success") and result.get("text"):
                command_text = result["text"]
                self.logger.info(f"Command recognized: {command_text}")
                self._stats["commands_detected"] += 1

                command = VoiceCommand(
                    text=command_text,
                    confidence=result.get("confidence", 1.0),
                    timestamp=time.time(),
                    is_wake_word=False,
                    speaker_id=result.get("speaker_vector"),
                )

                self._command_queue.put(command)
            else:
                self.logger.warning(
                    f"Command not understood: {result.get('error', 'unknown')}"
                )

        self.state = VoiceState.LISTENING_WAKE

    def _play_chime(self):
        try:
            import winsound

            winsound.Beep(1000, 100)
        except:
            print("\a", end="")

    async def speak(self, text: str):
        await self.tts.speak(text)

    def is_listening(self) -> bool:
        return self._running and self.state in [
            VoiceState.LISTENING_WAKE,
            VoiceState.LISTENING_COMMAND,
        ]

    def get_state(self) -> str:
        return self.state

    def get_stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time else 0
        return {
            **self._stats,
            "uptime": uptime,
            "state": self.state,
            "wake_detector": self.wake_detector.get_stats(),
            "recognizer": self.recognizer._stats,
        }

    async def stop(self):
        self.logger.info("Stopping voice system...")
        self._running = False
        self._listening = False

        if self._audio_stream:
            self._audio_stream.stop_stream()
            self._audio_stream.close()

        if self._audio:
            self._audio.terminate()

        self.tts.stop()
        self.state = VoiceState.IDLE
        self.logger.info("Voice system stopped")
