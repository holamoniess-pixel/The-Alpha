"""
ALPHA OMEGA - Config Manager
Centralized Configuration Management with Validation & Encryption
Version: 2.0.0
"""

import os
import json
import yaml
import logging
import hashlib
import base64
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import time

logger = logging.getLogger("ConfigManager")


class ConfigCategory(Enum):
    VOICE = "voice"
    INTELLIGENCE = "intelligence"
    SECURITY = "security"
    AUTOMATION = "automation"
    VISION = "vision"
    LEARNING = "learning"
    GAMING = "gaming"
    APPEARANCE = "appearance"
    INTEGRATIONS = "integrations"
    PERFORMANCE = "performance"


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"valid": self.valid, "errors": self.errors, "warnings": self.warnings}


@dataclass
class SettingDefinition:
    key: str
    name: str
    description: str
    type: str
    default: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    options: Optional[List[str]] = None
    category: str = "general"
    subcategory: str = "general"
    sensitive: bool = False
    requires_restart: bool = False


SETTINGS_SCHEMA = {
    ConfigCategory.VOICE.value: [
        SettingDefinition(
            "wake_word",
            "Wake Word",
            "Phrase to activate the assistant",
            "text",
            "hey alpha",
        ),
        SettingDefinition(
            "wake_sensitivity",
            "Wake Sensitivity",
            "How sensitive to wake word (0-100)",
            "slider",
            80,
            min_value=0,
            max_value=100,
        ),
        SettingDefinition(
            "voice_engine",
            "Voice Engine",
            "TTS/STT engine",
            "dropdown",
            "whisper-base",
            options=["whisper-tiny", "whisper-base", "whisper-small", "vosk"],
        ),
        SettingDefinition(
            "language",
            "Language",
            "Recognition language",
            "dropdown",
            "en-US",
            options=[
                "en-US",
                "en-GB",
                "es-ES",
                "fr-FR",
                "de-DE",
                "it-IT",
                "pt-BR",
                "ja-JP",
                "ko-KR",
                "zh-CN",
            ],
        ),
        SettingDefinition(
            "voice_speed",
            "Voice Speed",
            "TTS speaking rate",
            "slider",
            1.0,
            min_value=0.5,
            max_value=2.0,
        ),
        SettingDefinition(
            "voice_pitch",
            "Voice Pitch",
            "TTS voice pitch (0-100)",
            "slider",
            50,
            min_value=0,
            max_value=100,
        ),
        SettingDefinition(
            "noise_reduction",
            "Noise Reduction",
            "Background noise filtering",
            "toggle",
            True,
        ),
        SettingDefinition(
            "voice_auth_enabled",
            "Voice Authentication",
            "Enable speaker verification",
            "toggle",
            False,
        ),
        SettingDefinition(
            "sample_rate",
            "Sample Rate",
            "Audio sample rate",
            "dropdown",
            "16000",
            options=["8000", "16000", "22050", "44100"],
        ),
        SettingDefinition(
            "command_timeout",
            "Command Timeout",
            "Seconds to listen after wake",
            "slider",
            10,
            min_value=1,
            max_value=30,
        ),
        SettingDefinition(
            "barge_in", "Barge-In", "Interrupt TTS with voice", "toggle", True
        ),
        SettingDefinition(
            "offline_voice", "Offline Voice", "Use local models only", "toggle", True
        ),
    ],
    ConfigCategory.INTELLIGENCE.value: [
        SettingDefinition(
            "llm_provider",
            "LLM Provider",
            "Primary AI provider",
            "dropdown",
            "local",
            options=["local", "openai", "anthropic", "google", "groq", "openrouter"],
        ),
        SettingDefinition(
            "primary_model",
            "Primary Model",
            "Main LLM model",
            "dropdown",
            "phi-3-mini",
            options=[
                "phi-3-mini",
                "llama-3.1-8b",
                "mistral-7b",
                "gpt-4o-mini",
                "claude-3-haiku",
                "gemini-2.0-flash",
            ],
        ),
        SettingDefinition(
            "fallback_model",
            "Fallback Model",
            "Backup model",
            "dropdown",
            "tinyllama",
            options=["tinyllama", "phi-3-mini", "gpt-3.5-turbo"],
        ),
        SettingDefinition(
            "temperature",
            "Temperature",
            "Creativity level (0-2)",
            "slider",
            0.7,
            min_value=0,
            max_value=2,
        ),
        SettingDefinition(
            "max_tokens",
            "Max Tokens",
            "Response length limit",
            "slider",
            512,
            min_value=50,
            max_value=4096,
        ),
        SettingDefinition(
            "context_window",
            "Context Window",
            "Conversation memory size",
            "slider",
            4096,
            min_value=1024,
            max_value=32768,
        ),
        SettingDefinition(
            "top_p",
            "Top P",
            "Nucleus sampling",
            "slider",
            0.9,
            min_value=0,
            max_value=1,
        ),
        SettingDefinition(
            "reasoning_enabled", "Reasoning", "Enable chain-of-thought", "toggle", False
        ),
        SettingDefinition(
            "multi_step", "Multi-Step Reasoning", "Break complex tasks", "toggle", True
        ),
        SettingDefinition(
            "confidence_threshold",
            "Confidence Threshold",
            "Minimum confidence %",
            "slider",
            70,
            min_value=0,
            max_value=100,
        ),
        SettingDefinition(
            "long_term_memory",
            "Long-Term Memory",
            "Persist conversations",
            "toggle",
            True,
        ),
        SettingDefinition(
            "memory_retention_days",
            "Memory Retention",
            "Days to keep memories",
            "slider",
            30,
            min_value=1,
            max_value=365,
        ),
        SettingDefinition(
            "openai_api_key",
            "OpenAI API Key",
            "GPT API key",
            "password",
            "",
            sensitive=True,
        ),
        SettingDefinition(
            "anthropic_api_key",
            "Anthropic API Key",
            "Claude API key",
            "password",
            "",
            sensitive=True,
        ),
        SettingDefinition(
            "google_api_key",
            "Google API Key",
            "Gemini API key",
            "password",
            "",
            sensitive=True,
        ),
        SettingDefinition(
            "groq_api_key",
            "Groq API Key",
            "Groq API key",
            "password",
            "",
            sensitive=True,
        ),
        SettingDefinition(
            "openrouter_api_key",
            "OpenRouter API Key",
            "OpenRouter API key",
            "password",
            "",
            sensitive=True,
        ),
    ],
    ConfigCategory.SECURITY.value: [
        SettingDefinition(
            "voice_auth_enabled",
            "Voice Authentication",
            "Voice-based login",
            "toggle",
            False,
        ),
        SettingDefinition(
            "windows_login_bypass",
            "Windows Login Bypass",
            "Replace Windows login",
            "toggle",
            False,
            requires_restart=True,
        ),
        SettingDefinition(
            "auth_threshold",
            "Auth Threshold",
            "Similarity threshold %",
            "slider",
            65,
            min_value=50,
            max_value=99,
        ),
        SettingDefinition(
            "max_auth_attempts",
            "Max Auth Attempts",
            "Before lockout",
            "slider",
            3,
            min_value=1,
            max_value=10,
        ),
        SettingDefinition(
            "malware_scanning", "Malware Scanning", "Auto-scan files", "toggle", True
        ),
        SettingDefinition(
            "scan_on_download",
            "Scan on Download",
            "Check downloaded files",
            "toggle",
            True,
        ),
        SettingDefinition(
            "scan_on_execute", "Scan on Execute", "Pre-execution scan", "toggle", True
        ),
        SettingDefinition(
            "quarantine_threats",
            "Quarantine Threats",
            "Move threats to隔离",
            "toggle",
            True,
        ),
        SettingDefinition(
            "defender_integration",
            "Windows Defender",
            "Use Defender engine",
            "toggle",
            True,
        ),
        SettingDefinition(
            "command_whitelist",
            "Command Whitelist",
            "Only allow safe commands",
            "toggle",
            True,
        ),
        SettingDefinition(
            "require_approval",
            "Require Approval",
            "Ask before dangerous actions",
            "toggle",
            True,
        ),
        SettingDefinition(
            "vault_encryption",
            "Vault Encryption",
            "AES-256-GCM for secrets",
            "toggle",
            True,
        ),
        SettingDefinition(
            "activity_logging", "Activity Logging", "Log all actions", "toggle", True
        ),
        SettingDefinition(
            "tamper_proof_logs",
            "Tamper-Proof Logs",
            "Blockchain-style logs",
            "toggle",
            True,
        ),
        SettingDefinition(
            "log_retention_days",
            "Log Retention",
            "Days to keep logs",
            "slider",
            7,
            min_value=1,
            max_value=365,
        ),
    ],
    ConfigCategory.AUTOMATION.value: [
        SettingDefinition(
            "gui_automation",
            "GUI Automation",
            "Allow mouse/keyboard control",
            "toggle",
            True,
        ),
        SettingDefinition(
            "allow_shutdown", "Allow Shutdown", "Can shut down PC", "toggle", False
        ),
        SettingDefinition(
            "allow_restart", "Allow Restart", "Can restart PC", "toggle", True
        ),
        SettingDefinition("allow_sleep", "Allow Sleep", "Can sleep PC", "toggle", True),
        SettingDefinition(
            "allow_lock", "Allow Lock", "Can lock workstation", "toggle", True
        ),
        SettingDefinition(
            "file_create", "Allow Create", "Create new files", "toggle", True
        ),
        SettingDefinition(
            "file_modify", "Allow Modify", "Modify existing files", "toggle", True
        ),
        SettingDefinition(
            "file_delete", "Allow Delete", "Delete files", "toggle", False
        ),
        SettingDefinition(
            "auto_backup", "Auto Backup", "Backup before changes", "toggle", True
        ),
        SettingDefinition(
            "browser_control", "Browser Control", "Control web browser", "toggle", True
        ),
        SettingDefinition(
            "screenshot_capture",
            "Screenshot Capture",
            "Take screenshots",
            "toggle",
            True,
        ),
        SettingDefinition(
            "max_concurrent_tasks",
            "Max Concurrent Tasks",
            "Parallel workflows",
            "slider",
            5,
            min_value=1,
            max_value=10,
        ),
    ],
    ConfigCategory.VISION.value: [
        SettingDefinition(
            "enable_vision", "Enable Vision", "Screen reading", "toggle", True
        ),
        SettingDefinition(
            "ocr_engine",
            "OCR Engine",
            "Text recognition",
            "dropdown",
            "tesseract",
            options=["tesseract", "easyocr"],
        ),
        SettingDefinition(
            "screenshot_interval",
            "Screenshot Interval",
            "Auto-capture rate (sec, 0=off)",
            "slider",
            0,
            min_value=0,
            max_value=60,
        ),
        SettingDefinition(
            "active_window_only",
            "Active Window Only",
            "Only read active window",
            "toggle",
            True,
        ),
        SettingDefinition(
            "object_detection", "Object Detection", "Recognize objects", "toggle", False
        ),
        SettingDefinition(
            "face_detection", "Face Detection", "Detect faces", "toggle", False
        ),
        SettingDefinition(
            "gesture_recognition",
            "Gesture Recognition",
            "Hand gestures",
            "toggle",
            False,
        ),
        SettingDefinition(
            "blur_sensitive", "Blur Sensitive", "Blur passwords/keys", "toggle", True
        ),
    ],
    ConfigCategory.LEARNING.value: [
        SettingDefinition(
            "enable_learning", "Enable Learning", "Learn from user", "toggle", True
        ),
        SettingDefinition(
            "learn_commands", "Learn Commands", "Remember patterns", "toggle", True
        ),
        SettingDefinition(
            "learn_workflows", "Learn Workflows", "Create from habits", "toggle", True
        ),
        SettingDefinition(
            "prediction_enabled", "Prediction", "Predict next action", "toggle", True
        ),
        SettingDefinition(
            "watch_mode", "Watch Mode", "Observe user actions", "toggle", False
        ),
        SettingDefinition(
            "learn_from_tutorials",
            "Learn from Tutorials",
            "Process video tutorials",
            "toggle",
            False,
        ),
        SettingDefinition(
            "screen_recording",
            "Screen Recording",
            "Record for learning",
            "toggle",
            False,
        ),
        SettingDefinition(
            "auto_recreate",
            "Auto-Recreate",
            "Create scripts from actions",
            "toggle",
            False,
        ),
        SettingDefinition(
            "tutorial_source",
            "Tutorial Source",
            "Where to learn from",
            "dropdown",
            "youtube",
            options=["youtube", "local", "all"],
        ),
        SettingDefinition(
            "learning_depth",
            "Learning Depth",
            "How much to learn",
            "slider",
            5,
            min_value=1,
            max_value=10,
        ),
        SettingDefinition(
            "time_patterns", "Time Patterns", "Learn time-based habits", "toggle", True
        ),
        SettingDefinition(
            "app_usage_tracking",
            "App Usage",
            "Track app usage patterns",
            "toggle",
            True,
        ),
    ],
    ConfigCategory.GAMING.value: [
        SettingDefinition(
            "game_detection", "Game Detection", "Auto-detect games", "toggle", True
        ),
        SettingDefinition(
            "performance_mode", "Performance Mode", "Boost when gaming", "toggle", True
        ),
        SettingDefinition(
            "in_game_voice", "In-Game Voice", "Voice commands in game", "toggle", True
        ),
        SettingDefinition(
            "enable_macros", "Enable Macros", "Allow game macros", "toggle", False
        ),
        SettingDefinition(
            "anti_cheat_safe", "Anti-Cheat Safe", "Only safe macros", "toggle", True
        ),
        SettingDefinition("fps_overlay", "FPS Overlay", "Show FPS", "toggle", False),
        SettingDefinition(
            "temp_monitor", "Temperature Monitor", "Track GPU temp", "toggle", True
        ),
    ],
    ConfigCategory.APPEARANCE.value: [
        SettingDefinition(
            "theme",
            "Theme",
            "UI theme preset",
            "dropdown",
            "cyberpunk",
            options=["cyberpunk", "dark", "light", "midnight", "neon", "forest"],
        ),
        SettingDefinition("dark_mode", "Dark Mode", "Dark/light mode", "toggle", True),
        SettingDefinition(
            "accent_color", "Accent Color", "Primary color", "color", "#00e5ff"
        ),
        SettingDefinition(
            "enable_animations", "Animations", "UI animations", "toggle", True
        ),
        SettingDefinition(
            "particle_effects",
            "Particle Effects",
            "Background particles",
            "toggle",
            True,
        ),
        SettingDefinition(
            "parallax_effect", "Parallax", "Mouse parallax", "toggle", True
        ),
        SettingDefinition(
            "animation_speed",
            "Animation Speed",
            "Speed multiplier",
            "slider",
            1.0,
            min_value=0.5,
            max_value=2.0,
        ),
        SettingDefinition(
            "always_on_top", "Always On Top", "Window stays on top", "toggle", False
        ),
        SettingDefinition(
            "transparency",
            "Transparency",
            "Window opacity %",
            "slider",
            80,
            min_value=0,
            max_value=100,
        ),
        SettingDefinition(
            "font_size",
            "Font Size",
            "Text size",
            "slider",
            14,
            min_value=8,
            max_value=24,
        ),
        SettingDefinition(
            "sound_effects", "Sound Effects", "UI sounds", "toggle", True
        ),
        SettingDefinition(
            "desktop_notifications",
            "Desktop Notifications",
            "System notifications",
            "toggle",
            True,
        ),
    ],
    ConfigCategory.INTEGRATIONS.value: [
        SettingDefinition(
            "discord_integration", "Discord", "Discord controls", "toggle", False
        ),
        SettingDefinition(
            "spotify_integration", "Spotify", "Music control", "toggle", True
        ),
        SettingDefinition(
            "obs_integration", "OBS", "Streaming control", "toggle", False
        ),
        SettingDefinition("steam_integration", "Steam", "Game library", "toggle", True),
        SettingDefinition(
            "vscode_integration", "VS Code", "Code editor", "toggle", True
        ),
        SettingDefinition(
            "chrome_integration", "Chrome", "Browser control", "toggle", True
        ),
        SettingDefinition(
            "home_assistant", "Home Assistant", "Smart home", "toggle", False
        ),
        SettingDefinition("ha_url", "HA URL", "Home Assistant URL", "text", ""),
        SettingDefinition(
            "ha_token", "HA Token", "Access token", "password", "", sensitive=True
        ),
        SettingDefinition(
            "google_calendar", "Google Calendar", "Calendar access", "toggle", False
        ),
    ],
    ConfigCategory.PERFORMANCE.value: [
        SettingDefinition(
            "cpu_limit",
            "CPU Limit",
            "Max CPU usage %",
            "slider",
            80,
            min_value=10,
            max_value=100,
        ),
        SettingDefinition(
            "memory_limit",
            "Memory Limit",
            "Max RAM (MB)",
            "slider",
            2048,
            min_value=512,
            max_value=8192,
        ),
        SettingDefinition(
            "gpu_acceleration", "GPU Acceleration", "Use GPU for AI", "toggle", False
        ),
        SettingDefinition(
            "background_tasks", "Background Tasks", "Run when minimized", "toggle", True
        ),
        SettingDefinition(
            "work_in_sleep", "Work in Sleep", "Continue in sleep mode", "toggle", False
        ),
        SettingDefinition(
            "wake_for_tasks",
            "Wake for Tasks",
            "Wake PC for scheduled tasks",
            "toggle",
            False,
        ),
        SettingDefinition(
            "network_in_sleep",
            "Network in Sleep",
            "Keep network active",
            "toggle",
            False,
        ),
        SettingDefinition(
            "enable_caching", "Enable Caching", "Cache responses", "toggle", True
        ),
        SettingDefinition(
            "cache_size",
            "Cache Size",
            "MB for cache",
            "slider",
            512,
            min_value=100,
            max_value=2000,
        ),
        SettingDefinition(
            "auto_optimize", "Auto Optimize", "Auto-tune settings", "toggle", True
        ),
        SettingDefinition(
            "low_power_mode", "Low Power Mode", "Reduce power usage", "toggle", False
        ),
    ],
}


class ConfigManager:
    def __init__(self, config_path: str = None, vault_manager=None):
        self.config_path = Path(config_path or "C:/AlphaOmega/config.yaml")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._vault = vault_manager
        self._config: Dict[str, Any] = {}
        self._defaults = self._build_defaults()
        self._encrypted_keys: Dict[str, str] = {}
        self._load_config()

    def _build_defaults(self) -> Dict[str, Any]:
        defaults = {}
        for category, settings in SETTINGS_SCHEMA.items():
            defaults[category] = {}
            for setting in settings:
                defaults[category][setting.key] = setting.default
        return defaults

    def _load_config(self):
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info(f"Loaded config from {self.config_path}")
            else:
                self._config = {}
                logger.info("No config file found, using defaults")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self._config = {}

    def _save_config(self) -> bool:
        try:
            config_to_save = self._config.copy()

            for key_path, vault_key in self._encrypted_keys.items():
                parts = key_path.split(".")
                current = config_to_save
                for part in parts[:-1]:
                    if part not in current:
                        break
                    current = current[part]
                else:
                    current[parts[-1]] = f"<vault:{vault_key}>"

            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    config_to_save, f, default_flow_style=False, allow_unicode=True
                )

            logger.info(f"Saved config to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        parts = key.split(".")
        if len(parts) == 1:
            category = parts[0]
            if category in self._config:
                return {
                    **self._defaults.get(category, {}),
                    **self._config.get(category, {}),
                }
            return self._defaults.get(category, default)

        category = parts[0]
        setting_key = ".".join(parts[1:])

        if category in self._config and setting_key in self._config[category]:
            value = self._config[category][setting_key]
            if isinstance(value, str) and value.startswith("<vault:"):
                return self._decrypt_from_vault(value)
            return value

        if category in self._defaults and setting_key in self._defaults[category]:
            return self._defaults[category][setting_key]

        return default

    def set(self, key: str, value: Any, sensitive: bool = False) -> bool:
        parts = key.split(".")
        if len(parts) < 2:
            logger.error(f"Invalid key format: {key}")
            return False

        category = parts[0]
        setting_key = ".".join(parts[1:])

        if category not in self._config:
            self._config[category] = {}

        if sensitive and self._vault and isinstance(value, str) and value:
            vault_key = self._encrypt_to_vault(key, value)
            value = f"<vault:{vault_key}>"
            self._encrypted_keys[key] = vault_key

        self._config[category][setting_key] = value
        return True

    def _encrypt_to_vault(self, key: str, value: str) -> str:
        if not self._vault:
            return value

        vault_key = f"api_key_{hashlib.md5(key.encode()).hexdigest()[:16]}"

        try:
            if hasattr(self._vault, "store_secret"):
                self._vault.store_secret(
                    vault_key, value, metadata={"source": "config", "key": key}
                )
            return vault_key
        except Exception as e:
            logger.error(f"Failed to encrypt to vault: {e}")
            return value

    def _decrypt_from_vault(self, value: str) -> str:
        if not self._vault or not value.startswith("<vault:"):
            return value

        vault_key = value[7:-1]

        try:
            if hasattr(self._vault, "get_secret"):
                return self._vault.get_secret(vault_key)
            return value
        except Exception as e:
            logger.error(f"Failed to decrypt from vault: {e}")
            return ""

    def get_category(self, category: str) -> Dict[str, Any]:
        defaults = self._defaults.get(category, {})
        overrides = self._config.get(category, {})

        result = {}
        for key, value in defaults.items():
            if key in overrides:
                override_value = overrides[key]
                if isinstance(override_value, str) and override_value.startswith(
                    "<vault:"
                ):
                    result[key] = self._decrypt_from_vault(override_value)
                else:
                    result[key] = override_value
            else:
                result[key] = value

        return result

    def set_category(self, category: str, settings: Dict[str, Any]) -> bool:
        if category not in SETTINGS_SCHEMA:
            logger.error(f"Unknown category: {category}")
            return False

        schema_settings = {s.key: s for s in SETTINGS_SCHEMA[category]}

        for key, value in settings.items():
            if key in schema_settings:
                setting_def = schema_settings[key]
                validated, error = self._validate_value(key, value, setting_def)
                if not validated:
                    logger.error(f"Validation failed for {key}: {error}")
                    return False

                self.set(f"{category}.{key}", value, sensitive=setting_def.sensitive)

        return self._save_config()

    def _validate_value(
        self, key: str, value: Any, setting_def: SettingDefinition
    ) -> Tuple[bool, str]:
        if setting_def.type == "toggle":
            if not isinstance(value, bool):
                return False, f"{key} must be a boolean"

        elif setting_def.type == "slider":
            if not isinstance(value, (int, float)):
                return False, f"{key} must be a number"
            if setting_def.min_value is not None and value < setting_def.min_value:
                return False, f"{key} must be >= {setting_def.min_value}"
            if setting_def.max_value is not None and value > setting_def.max_value:
                return False, f"{key} must be <= {setting_def.max_value}"

        elif setting_def.type == "dropdown":
            if setting_def.options and value not in setting_def.options:
                return False, f"{key} must be one of {setting_def.options}"

        elif setting_def.type == "password":
            if not isinstance(value, str):
                return False, f"{key} must be a string"

        elif setting_def.type == "text":
            if not isinstance(value, str):
                return False, f"{key} must be a string"

        elif setting_def.type == "color":
            if not isinstance(value, str) or not value.startswith("#"):
                return False, f"{key} must be a hex color (e.g., #00e5ff)"

        return True, ""

    def validate_config(self, config: Dict[str, Any] = None) -> ValidationResult:
        result = ValidationResult(valid=True)
        config_to_validate = config or self._config

        for category, settings in config_to_validate.items():
            if category not in SETTINGS_SCHEMA:
                result.warnings.append(f"Unknown category: {category}")
                continue

            schema_settings = {s.key: s for s in SETTINGS_SCHEMA[category]}

            for key, value in settings.items():
                if key in schema_settings:
                    valid, error = self._validate_value(
                        key, value, schema_settings[key]
                    )
                    if not valid:
                        result.errors.append(f"{category}.{key}: {error}")
                        result.valid = False

        return result

    def get_category_schema(self, category: str) -> List[Dict[str, Any]]:
        if category not in SETTINGS_SCHEMA:
            return []

        return [
            {
                "key": s.key,
                "name": s.name,
                "description": s.description,
                "type": s.type,
                "default": s.default,
                "min_value": s.min_value,
                "max_value": s.max_value,
                "options": s.options,
                "subcategory": s.subcategory,
                "sensitive": s.sensitive,
                "requires_restart": s.requires_restart,
            }
            for s in SETTINGS_SCHEMA[category]
        ]

    def get_all_schemas(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            category: self.get_category_schema(category) for category in SETTINGS_SCHEMA
        }

    def reset_category(self, category: str) -> bool:
        if category not in self._defaults:
            return False

        self._config[category] = self._defaults[category].copy()
        return self._save_config()

    def reset_all(self) -> bool:
        self._config = self._defaults.copy()
        return self._save_config()

    def export_config(self) -> str:
        return json.dumps(self._config, indent=2, default=str)

    def import_config(self, config_json: str, merge: bool = True) -> bool:
        try:
            imported = json.loads(config_json)

            if merge:
                for category, settings in imported.items():
                    if category not in self._config:
                        self._config[category] = {}
                    self._config[category].update(settings)
            else:
                self._config = imported

            result = self.validate_config()
            if not result.valid:
                logger.error(f"Import validation failed: {result.errors}")
                return False

            return self._save_config()
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return False
