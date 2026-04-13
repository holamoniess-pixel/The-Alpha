"""
ALPHA OMEGA - Windows Credential Provider
Voice Authentication for Windows Login Bypass
Version: 2.0.0

SECURITY NOTE: This requires administrator privileges and modifies Windows security.
Self-signed certificate will show Windows Security warning - user must approve.
"""

import os
import sys
import json
import logging
import subprocess
import ctypes
import time
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("CredentialProvider")


@dataclass
class VoiceProfile:
    user_id: str
    voice_vector: list
    created_at: float
    last_used: float
    auth_count: int


class AlphaCredentialProvider:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self._is_windows = os.name == "nt"
        self._is_admin = self._check_admin()
        self._profiles_path = Path("C:/AlphaOmega/data/voice_profiles.json")
        self._profiles_path.parent.mkdir(parents=True, exist_ok=True)
        self._voice_auth = None
        self._provider_registered = False

    def _check_admin(self) -> bool:
        if not self._is_windows:
            return False
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def initialize(self) -> Tuple[bool, str]:
        if not self._is_windows:
            return False, "Credential provider only available on Windows"

        if not self._check_admin():
            return (
                False,
                "Administrator privileges required. Please run as administrator.",
            )

        try:
            from voice_auth import VoiceAuthenticator

            self._voice_auth = VoiceAuthenticator()
            return True, "Voice authenticator initialized"
        except ImportError:
            return False, "Voice authentication module not found"
        except Exception as e:
            return False, f"Failed to initialize: {e}"

    def request_admin_access(self) -> Tuple[bool, str]:
        if self._is_admin:
            return True, "Already running as administrator"

        if not self._is_windows:
            return False, "Only available on Windows"

        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            return True, "Administrator elevation requested - please approve UAC prompt"
        except Exception as e:
            return False, f"Failed to request admin access: {e}"

    def enroll_voice(self, user_id: str, audio_data: bytes = None) -> Tuple[bool, str]:
        if not self._voice_auth:
            initialized, msg = self.initialize()
            if not initialized:
                return False, msg

        try:
            if audio_data:
                success = self._voice_auth.enroll_user(user_id, audio_data)
            else:
                import tempfile
                import wave

                temp_path = tempfile.mktemp(suffix=".wav")

                success, msg = self._record_and_enroll(user_id, temp_path)
                if not success:
                    return False, msg

                if os.path.exists(temp_path):
                    os.unlink(temp_path)

            if success:
                profile = VoiceProfile(
                    user_id=user_id,
                    voice_vector=[],
                    created_at=time.time(),
                    last_used=time.time(),
                    auth_count=0,
                )
                self._save_profile(profile)
                return True, f"Voice profile created for {user_id}"

            return False, "Enrollment failed"

        except Exception as e:
            logger.error(f"Enrollment error: {e}")
            return False, str(e)

    def _record_and_enroll(self, user_id: str, output_path: str) -> Tuple[bool, str]:
        try:
            import pyaudio
            import wave

            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000
            RECORD_SECONDS = 5

            logger.info(f"Recording voice for {user_id}... Speak now!")

            p = pyaudio.PyAudio()
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
            )

            frames = []
            for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)

            stream.stop_stream()
            stream.close()
            p.terminate()

            wf = wave.open(output_path, "wb")
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b"".join(frames))
            wf.close()

            success = self._voice_auth.enroll_user(user_id, output_path)
            return success, "Recording complete" if success else "Enrollment failed"

        except ImportError:
            return False, "PyAudio not installed. Cannot record audio."
        except Exception as e:
            return False, f"Recording error: {e}"

    def verify_voice(
        self, audio_data: bytes = None, claimed_user: str = "default"
    ) -> Tuple[bool, float, str]:
        if not self._voice_auth:
            initialized, msg = self.initialize()
            if not initialized:
                return False, 0.0, msg

        try:
            if audio_data:
                verified, score = self._voice_auth.verify_user(audio_data, claimed_user)
            else:
                verified, score, msg = self._record_and_verify(claimed_user)
                if not verified and score == 0:
                    return False, 0.0, msg

            threshold = self.config.get("voice_auth_threshold", 0.65)

            if verified and score >= threshold:
                self._update_profile_usage(claimed_user)
                return True, score, f"Voice verified (score: {score:.2f})"
            else:
                return (
                    False,
                    score,
                    f"Voice verification failed (score: {score:.2f}, threshold: {threshold})",
                )

        except Exception as e:
            logger.error(f"Verification error: {e}")
            return False, 0.0, str(e)

    def _record_and_verify(self, claimed_user: str) -> Tuple[bool, float, str]:
        try:
            import pyaudio
            import wave
            import tempfile

            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000
            RECORD_SECONDS = 3

            logger.info("Recording for verification...")

            p = pyaudio.PyAudio()
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
            )

            frames = []
            for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)

            stream.stop_stream()
            stream.close()
            p.terminate()

            temp_path = tempfile.mktemp(suffix=".wav")
            wf = wave.open(temp_path, "wb")
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b"".join(frames))
            wf.close()

            verified, score = self._voice_auth.verify_user(temp_path, claimed_user)

            if os.path.exists(temp_path):
                os.unlink(temp_path)

            return verified, score, "Verification complete"

        except Exception as e:
            return False, 0.0, f"Recording error: {e}"

    def register_provider(self) -> Tuple[bool, str]:
        if not self._is_windows:
            return False, "Only available on Windows"

        if not self._check_admin():
            return False, "Administrator privileges required"

        try:
            provider_dir = Path("C:/AlphaOmega/credential_provider")
            provider_dir.mkdir(parents=True, exist_ok=True)

            self._create_provider_dll_stub(provider_dir)

            reg_commands = [
                'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Authentication\\Credential Providers\\{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}" /ve /d "AlphaOmegaVoiceProvider" /f',
                'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Authentication\\Credential Providers\\{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}" /v "Alias" /t REG_EXPAND_SZ /d "AlphaOmega" /f',
            ]

            for cmd in reg_commands:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(f"Registry command failed: {result.stderr}")

            self._provider_registered = True
            logger.info("Credential provider registered")

            return (
                True,
                "Credential provider registered. A system restart may be required.",
            )

        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return False, f"Failed to register: {e}"

    def _create_provider_dll_stub(self, directory: Path):
        dll_stub = directory / "AlphaOmegaCredentialProvider.dll.stub"

        stub_content = """
ALPHA OMEGA CREDENTIAL PROVIDER STUB
=====================================

This is a placeholder for the actual Windows Credential Provider DLL.

To fully implement Windows Login Bypass with voice authentication,
you need to:

1. Create a COM DLL that implements ICredentialProvider interface
2. Sign the DLL with a code signing certificate
3. Register the CLSID in Windows Registry

For BETA testing with self-signed certificate:
- Users will see a Windows Security warning
- They must click "More info" -> "Run anyway"

The Python implementation handles:
- Voice enrollment
- Voice verification
- Profile management

A native C++ DLL is required for actual Windows integration.
"""
        dll_stub.write_text(stub_content)

    def unregister_provider(self) -> Tuple[bool, str]:
        if not self._is_windows:
            return False, "Only available on Windows"

        if not self._check_admin():
            return False, "Administrator privileges required"

        try:
            reg_commands = [
                'reg delete "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Authentication\\Credential Providers\\{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}" /f',
            ]

            for cmd in reg_commands:
                subprocess.run(cmd, shell=True, capture_output=True)

            self._provider_registered = False
            return True, "Credential provider unregistered"

        except Exception as e:
            return False, f"Failed to unregister: {e}"

    def _save_profile(self, profile: VoiceProfile):
        profiles = self._load_profiles()
        profiles[profile.user_id] = {
            "user_id": profile.user_id,
            "created_at": profile.created_at,
            "last_used": profile.last_used,
            "auth_count": profile.auth_count,
        }
        self._profiles_path.write_text(json.dumps(profiles, indent=2))

    def _load_profiles(self) -> dict:
        if self._profiles_path.exists():
            return json.loads(self._profiles_path.read_text())
        return {}

    def _update_profile_usage(self, user_id: str):
        profiles = self._load_profiles()
        if user_id in profiles:
            profiles[user_id]["last_used"] = time.time()
            profiles[user_id]["auth_count"] = profiles[user_id].get("auth_count", 0) + 1
            self._profiles_path.write_text(json.dumps(profiles, indent=2))

    def get_profiles(self) -> list:
        return list(self._load_profiles().values())

    def delete_profile(self, user_id: str) -> bool:
        profiles = self._load_profiles()
        if user_id in profiles:
            del profiles[user_id]
            self._profiles_path.write_text(json.dumps(profiles, indent=2))

            if self._voice_auth:
                db_path = Path("users_voice_db.json")
                if db_path.exists():
                    db = json.loads(db_path.read_text())
                    if user_id in db:
                        del db[user_id]
                        db_path.write_text(json.dumps(db, indent=2))

            return True
        return False

    def is_registered(self) -> bool:
        return self._provider_registered

    def get_status(self) -> dict:
        return {
            "platform": "windows" if self._is_windows else "other",
            "is_admin": self._is_admin,
            "voice_auth_available": self._voice_auth is not None,
            "provider_registered": self._provider_registered,
            "profiles_count": len(self._load_profiles()),
        }
