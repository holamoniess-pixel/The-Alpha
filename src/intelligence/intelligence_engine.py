#!/usr/bin/env python3
"""
ALPHA OMEGA - HIGH-PERFORMANCE INTELLIGENCE ENGINE
NLP, Intent Classification, and LLM Integration
Version: 2.0.0
"""

import asyncio
import json
import logging
import re
import time
import hashlib
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
import threading

from .llm_provider import (
    UnifiedLLMProvider,
    LLMResponse,
    ProviderType,
    ModelRegistry,
)


class IntentType(Enum):
    AUTOMATION = auto()
    QUERY = auto()
    SYSTEM = auto()
    LEARNING = auto()
    CONVERSATION = auto()
    UNKNOWN = auto()


class ActionCategory(Enum):
    APPLICATION = "application"
    FILE = "file"
    SYSTEM = "system"
    WEB = "web"
    CLIPBOARD = "clipboard"
    WINDOW = "window"
    AUDIO = "audio"
    NETWORK = "network"
    UNKNOWN = "unknown"


@dataclass
class ProcessedIntent:
    intent_type: IntentType
    confidence: float
    command: str
    action: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    entities: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.intent_type.name,
            "confidence": self.confidence,
            "command": self.command,
            "action": self.action,
            "parameters": self.parameters,
            "entities": self.entities,
            "context": self.context,
            "raw_text": self.raw_text,
        }


@dataclass
class Entity:
    entity_type: str
    value: str
    confidence: float
    position: Tuple[int, int] = (0, 0)


class EntityExtractor:
    def __init__(self):
        self.patterns = {
            "app_name": [
                r"\b(chrome|firefox|edge|safari|browser)\b",
                r"\b(notepad|word|excel|powerpoint|outlook)\b",
                r"\b(vscode|visual studio|sublime|atom)\b",
                r"\b(steam|discord|spotify|vlc)\b",
                r"\b(calculator|paint|cmd|terminal|powershell)\b",
                r"\b(settings|control panel|task manager)\b",
            ],
            "file_path": [
                r'([A-Za-z]:\\[^\s"\'<>|]+\.\w+)',
                r'(\./[^\s"\'<>|]+\.\w+)',
                r'(\.\./[^\s"\'<>|]+\.\w+)',
                r'(\~/[^\s"\'<>|]+\.\w+)',
            ],
            "url": [
                r'(https?://[^\s"\'<>]+)',
                r'(www\.[^\s"\'<>]+\.\w+)',
            ],
            "number": [
                r"\b(\d+(?:\.\d+)?)\b",
            ],
            "coordinates": [
                r"\b(\d{1,4})\s*[,x]\s*(\d{1,4})\b",
            ],
            "email": [
                r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            ],
            "ip_address": [
                r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b",
            ],
            "time": [
                r"\b(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[ap]m)?)\b",
                r"\b(\d{1,2}\s*(?:hours?|minutes?|seconds?))\b",
            ],
            "percentage": [
                r"\b(\d+(?:\.\d+)?)\s*%\b",
            ],
        }

        self._compiled = {}
        for entity_type, patterns in self.patterns.items():
            self._compiled[entity_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    def extract(self, text: str) -> List[Entity]:
        entities = []

        for entity_type, patterns in self._compiled.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    entities.append(
                        Entity(
                            entity_type=entity_type,
                            value=match.group(1) if match.lastindex else match.group(0),
                            confidence=0.9,
                            position=(match.start(), match.end()),
                        )
                    )

        return entities


class IntentClassifier:
    def __init__(self):
        self.intent_patterns = {
            IntentType.AUTOMATION: {
                "keywords": [
                    "open",
                    "start",
                    "launch",
                    "run",
                    "close",
                    "kill",
                    "stop",
                    "click",
                    "type",
                    "press",
                    "scroll",
                    "move",
                    "drag",
                    "minimize",
                    "maximize",
                    "resize",
                    "window",
                    "copy",
                    "paste",
                    "cut",
                    "delete",
                    "create",
                    "move file",
                    "shutdown",
                    "restart",
                    "sleep",
                    "lock",
                    "volume",
                    "mute",
                    "screenshot",
                    "download",
                    "search",
                ],
                "weight": 1.0,
            },
            IntentType.QUERY: {
                "keywords": [
                    "what",
                    "how",
                    "when",
                    "where",
                    "why",
                    "who",
                    "which",
                    "is",
                    "are",
                    "can",
                    "could",
                    "would",
                    "should",
                    "tell me",
                    "explain",
                    "describe",
                    "show",
                    "list",
                    "status",
                    "info",
                    "information",
                    "weather",
                    "time",
                    "date",
                ],
                "weight": 0.8,
            },
            IntentType.SYSTEM: {
                "keywords": [
                    "status",
                    "help",
                    "pause",
                    "resume",
                    "stop",
                    "cancel",
                    "settings",
                    "config",
                    "version",
                    "update",
                    "restart system",
                    "shutdown system",
                    "lock system",
                ],
                "weight": 0.9,
            },
            IntentType.LEARNING: {
                "keywords": [
                    "learn",
                    "remember",
                    "forget",
                    "teach",
                    "train",
                    "pattern",
                    "habit",
                    "workflow",
                    "automate",
                    "schedule",
                    "repeat",
                    "macro",
                    "custom command",
                ],
                "weight": 0.7,
            },
            IntentType.CONVERSATION: {
                "keywords": [
                    "hello",
                    "hi",
                    "hey",
                    "good morning",
                    "good evening",
                    "thank",
                    "please",
                    "sorry",
                    "goodbye",
                    "bye",
                    "how are you",
                    "what are you",
                    "who are you",
                ],
                "weight": 0.5,
            },
        }

        self.action_patterns = {
            ActionCategory.APPLICATION: [
                "open",
                "start",
                "launch",
                "run",
                "close",
                "kill",
                "app",
                "application",
            ],
            ActionCategory.FILE: [
                "file",
                "folder",
                "directory",
                "create",
                "delete",
                "copy",
                "move",
                "read",
                "write",
            ],
            ActionCategory.SYSTEM: [
                "shutdown",
                "restart",
                "sleep",
                "lock",
                "status",
                "volume",
                "mute",
                "brightness",
            ],
            ActionCategory.WEB: [
                "url",
                "website",
                "search",
                "browser",
                "download",
                "open link",
            ],
            ActionCategory.CLIPBOARD: ["copy", "paste", "cut", "clipboard"],
            ActionCategory.WINDOW: [
                "window",
                "minimize",
                "maximize",
                "resize",
                "move window",
                "focus",
            ],
            ActionCategory.AUDIO: ["volume", "mute", "unmute", "sound", "audio"],
            ActionCategory.NETWORK: [
                "ping",
                "ip",
                "network",
                "connect",
                "disconnect",
                "wifi",
            ],
        }

    def classify(self, text: str) -> Tuple[IntentType, float, ActionCategory]:
        text_lower = text.lower()
        scores = defaultdict(float)

        for intent_type, pattern_data in self.intent_patterns.items():
            for keyword in pattern_data["keywords"]:
                if keyword in text_lower:
                    scores[intent_type] += pattern_data["weight"]

        if not scores:
            return IntentType.UNKNOWN, 0.0, ActionCategory.UNKNOWN

        best_intent = max(scores, key=scores.get)
        confidence = min(scores[best_intent] / 3.0, 1.0)

        action_scores = defaultdict(float)
        for action_cat, keywords in self.action_patterns.items():
            for keyword in keywords:
                if keyword in text_lower:
                    action_scores[action_cat] += 1.0

        best_action = (
            max(action_scores, key=action_scores.get)
            if action_scores
            else ActionCategory.UNKNOWN
        )

        return best_intent, confidence, best_action


class ParameterExtractor:
    def __init__(self):
        self.param_patterns = {
            "x": r"[xX]\s*[=: ]?\s*(\d+)",
            "y": r"[yY]\s*[=: ]?\s*(\d+)",
            "text": r'["\']([^"\']+)["\']|type\s+(.+?)(?:\s+at|\s+in|$)',
            "path": r'(?:file|path|folder|directory)\s+[=: ]?\s*["\']?([^\s"\'<>|]+)',
            "url": r'(https?://[^\s"\'<>]+)',
            "app": r"(?:open|start|launch|close)\s+([a-zA-Z\s]+?)(?:\s+with|\s+using|\s*$)",
            "query": r'(?:search|find|look for)\s+["\']?([^"\'\n]+)["\']?',
            "amount": r"(\d+(?:\.\d+)?)\s*(?:percent|%)?",
            "duration": r"(\d+)\s*(?:seconds?|minutes?|hours?)",
        }

        self._compiled = {
            k: re.compile(v, re.IGNORECASE) for k, v in self.param_patterns.items()
        }

    def extract(self, text: str, entities: List[Entity]) -> Dict[str, Any]:
        params = {}

        for param_name, pattern in self._compiled.items():
            match = pattern.search(text)
            if match:
                if match.lastindex:
                    params[param_name] = match.group(1) or match.group(2)
                else:
                    params[param_name] = match.group(0)

        for entity in entities:
            if entity.entity_type not in params:
                params[entity.entity_type] = entity.value

        coords_match = re.search(r"(\d{1,4})\s*[,x]\s*(\d{1,4})", text)
        if coords_match:
            params["x"] = int(coords_match.group(1))
            params["y"] = int(coords_match.group(2))

        return params


class KnowledgeBase:
    def __init__(self):
        self.facts = {
            "system": {
                "name": "AlphaOmega",
                "version": "2.0.0",
                "type": "AI Assistant",
            },
            "capabilities": [
                "voice control",
                "automation",
                "file management",
                "application control",
                "web browsing",
                "system control",
                "learning patterns",
                "voice authentication",
                "screen vision",
            ],
            "greetings": [
                "Hello! I'm AlphaOmega, ready to assist you.",
                "Hi there! How can I help you today?",
                "Greetings! AlphaOmega at your service.",
            ],
            "status_responses": {
                "working": "I'm functioning normally. All systems operational.",
                "ready": "Ready to assist. What would you like me to do?",
            },
        }

        self.command_help = {
            "open": 'Open an application. Usage: "open [app name]"',
            "close": 'Close an application. Usage: "close [app name]"',
            "type": 'Type text. Usage: "type [text]"',
            "click": 'Click at position. Usage: "click [x] [y]"',
            "screenshot": 'Take a screenshot. Usage: "screenshot"',
            "volume": 'Set volume. Usage: "volume [0-100]"',
            "search": 'Search the web. Usage: "search [query]"',
            "status": 'Get system status. Usage: "status"',
            "help": 'Show help. Usage: "help"',
        }

    def get_response(self, category: str, key: str = None) -> Optional[str]:
        if category in self.facts:
            if key:
                return self.facts[category].get(key)
            return self.facts[category]
        return None

    def get_help(self, command: str = None) -> str:
        if command and command in self.command_help:
            return self.command_help[command]
        return "\n".join(f"{k}: {v}" for k, v in self.command_help.items())


class LLMClient:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("LLMClient")

        self.api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get(
            "OPENAI_API_KEY"
        )
        self.api_url = config.get(
            "api_url", "https://openrouter.ai/api/v1/chat/completions"
        )
        self.model = config.get("model", "google/gemini-2.0-flash-001")

        self._local_model = None
        self._local_tokenizer = None
        self._use_local = config.get("use_local", False)
        self._context_history = []
        self._max_context = config.get("context_window", 4096)

    async def initialize(self) -> bool:
        if self._use_local and HAS_TRANSFORMERS:
            try:
                model_name = self.config.get("local_model", "microsoft/DialoGPT-medium")
                self.logger.info(f"Loading local model: {model_name}")

                self._local_tokenizer = AutoTokenizer.from_pretrained(model_name)
                self._local_model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype=torch.float16
                    if torch.cuda.is_available()
                    else torch.float32,
                )

                if torch.cuda.is_available():
                    self._local_model = self._local_model.to("cuda")

                self.logger.info("Local model loaded successfully")
                return True
            except Exception as e:
                self.logger.warning(f"Failed to load local model: {e}")

        if self.api_key:
            self.logger.info("Using API-based LLM")
            return True

        self.logger.warning("No LLM available - using rule-based responses")
        return True

    async def generate(self, prompt: str, context: Dict[str, Any] = None) -> str:
        if self._use_local and self._local_model:
            return await self._generate_local(prompt, context)
        elif self.api_key and HAS_REQUESTS:
            return await self._generate_api(prompt, context)
        else:
            return self._generate_rule_based(prompt, context)

    async def _generate_local(self, prompt: str, context: Dict[str, Any] = None) -> str:
        try:
            inputs = self._local_tokenizer.encode(prompt, return_tensors="pt")

            if torch.cuda.is_available():
                inputs = inputs.to("cuda")

            with torch.no_grad():
                outputs = self._local_model.generate(
                    inputs,
                    max_length=inputs.shape[1] + self.config.get("max_tokens", 256),
                    temperature=self.config.get("temperature", 0.7),
                    do_sample=True,
                    pad_token_id=self._local_tokenizer.eos_token_id,
                )

            response = self._local_tokenizer.decode(
                outputs[0][inputs.shape[1] :], skip_special_tokens=True
            )
            return response.strip()
        except Exception as e:
            self.logger.error(f"Local generation error: {e}")
            return ""

    async def _generate_api(self, prompt: str, context: Dict[str, Any] = None) -> str:
        try:
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt},
            ]

            if context:
                messages.insert(
                    1, {"role": "system", "content": f"Context: {json.dumps(context)}"}
                )

            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": self.config.get("max_tokens", 512),
                    "temperature": self.config.get("temperature", 0.7),
                },
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                self.logger.error(f"API error: {response.status_code}")
                return ""
        except Exception as e:
            self.logger.error(f"API generation error: {e}")
            return ""

    def _generate_rule_based(self, prompt: str, context: Dict[str, Any] = None) -> str:
        prompt_lower = prompt.lower()

        if "time" in prompt_lower:
            import datetime

            return f"The current time is {datetime.datetime.now().strftime('%H:%M:%S')}"
        elif "date" in prompt_lower:
            import datetime

            return f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}"
        elif "who are you" in prompt_lower:
            return "I am AlphaOmega, your AI assistant for PC control and automation."
        elif "help" in prompt_lower:
            return "I can help you control your PC with voice commands. Try saying 'open chrome', 'type hello', or 'what time is it'."
        else:
            return "I understand. How can I assist you further?"

    def _get_system_prompt(self) -> str:
        return """You are AlphaOmega, a sophisticated AI assistant that controls a PC through voice commands.
You are helpful, concise, and professional. Address the user respectfully.
You can execute system commands, manage files, control applications, and provide information.
When the user gives a command, acknowledge it briefly and execute it.
Keep responses short and actionable."""


class IntelligenceEngine:
    def __init__(self, config: Dict[str, Any], memory_system=None):
        self.config = config
        self.memory = memory_system
        self.logger = logging.getLogger("IntelligenceEngine")

        self.entity_extractor = EntityExtractor()
        self.intent_classifier = IntentClassifier()
        self.param_extractor = ParameterExtractor()
        self.knowledge_base = KnowledgeBase()

        self.llm_client = None
        self.unified_llm = None
        self._use_unified_llm = False

        self._context_window = []
        self._max_context = config.get("context_window", 4096)

        self._stats = {
            "commands_processed": 0,
            "intents_classified": 0,
            "entities_extracted": 0,
            "llm_calls": 0,
            "avg_processing_ms": 0,
        }

    async def initialize(self) -> bool:
        self.logger.info("Initializing Intelligence Engine...")

        llm_config = self.config.get("intelligence", {})

        self.unified_llm = UnifiedLLMProvider(llm_config)
        init_success = await self.unified_llm.initialize()

        if init_success:
            self._use_unified_llm = True
            self.logger.info(
                f"Unified LLM Provider initialized. Active: {self.unified_llm.active_provider}"
            )
        else:
            self.llm_client = LLMClient(self.config)
            await self.llm_client.initialize()
            self.logger.info("Fallback LLM Client initialized")

        self.logger.info("Intelligence Engine initialized")
        return True

    async def process_command(
        self, command: str, context: Dict[str, Any] = None
    ) -> ProcessedIntent:
        start_time = time.time()
        self._stats["commands_processed"] += 1

        self._add_to_context({"role": "user", "content": command})

        entities = self.entity_extractor.extract(command)
        self._stats["entities_extracted"] += len(entities)

        intent_type, confidence, action_category = self.intent_classifier.classify(
            command
        )
        self._stats["intents_classified"] += 1

        parameters = self.param_extractor.extract(command, entities)

        action = self._extract_action(command, intent_type)

        processed = ProcessedIntent(
            intent_type=intent_type,
            confidence=confidence,
            command=self._normalize_command(command),
            action=action,
            parameters=parameters,
            entities={e.entity_type: e.value for e in entities},
            context=context or {},
            raw_text=command,
        )

        if self.memory:
            await self.memory.store_command(
                command=command,
                intent=intent_type.name,
                success=True,
                response="",
                context={"processed": processed.to_dict()},
            )

        processing_time = (time.time() - start_time) * 1000
        self._stats["avg_processing_ms"] = (
            self._stats["avg_processing_ms"] * (self._stats["commands_processed"] - 1)
            + processing_time
        ) / self._stats["commands_processed"]

        return processed

    def _extract_action(self, text: str, intent_type: IntentType) -> str:
        text_lower = text.lower().strip()

        action_keywords = {
            "open": "open",
            "start": "open",
            "launch": "open",
            "run": "open",
            "close": "close",
            "kill": "close",
            "stop": "close",
            "type": "type",
            "click": "click",
            "press": "press",
            "scroll": "scroll",
            "move": "move",
            "drag": "drag",
            "copy": "clipboard_copy",
            "paste": "clipboard_paste",
            "cut": "clipboard_copy",
            "delete": "file_delete",
            "create": "file_create",
            "read": "file_read",
            "list": "dir_list",
            "search": "search",
            "find": "search",
            "shutdown": "shutdown",
            "restart": "restart",
            "sleep": "sleep",
            "lock": "lock",
            "volume": "volume",
            "mute": "mute",
            "screenshot": "screenshot",
            "status": "system_info",
            "help": "help",
            "ping": "ping",
            "ip": "ip",
        }

        words = text_lower.split()
        for word in words:
            if word in action_keywords:
                return action_keywords[word]

        if intent_type == IntentType.QUERY:
            return "query"
        elif intent_type == IntentType.SYSTEM:
            return "system"
        elif intent_type == IntentType.CONVERSATION:
            return "conversation"

        return "unknown"

    def _normalize_command(self, text: str) -> str:
        text = text.lower().strip()

        wake_words = ["hey alpha", "alpha", "okay alpha", "ok alpha"]
        for wake in wake_words:
            text = text.replace(wake, "")

        text = " ".join(text.split())

        return text

    async def answer_query(self, intent: ProcessedIntent) -> Dict[str, Any]:
        query = intent.parameters.get("query", intent.raw_text)

        kb_response = self._check_knowledge_base(query)
        if kb_response:
            return {"success": True, "message": kb_response}

        self._stats["llm_calls"] += 1

        if self._use_unified_llm and self.unified_llm:
            response = await self.unified_llm.generate(
                query, system_prompt=self._get_system_prompt()
            )
            return {"success": response.success, "message": response.text}
        else:
            response = await self.llm_client.generate(query, intent.context)
            return {"success": True, "message": response}

    def _check_knowledge_base(self, query: str) -> Optional[str]:
        query_lower = query.lower()

        if "who are you" in query_lower or "what are you" in query_lower:
            return (
                self.knowledge_base.get_response("system", "name")
                + " - "
                + self.knowledge_base.get_response("system", "type")
            )

        if "version" in query_lower:
            return (
                f"I am version {self.knowledge_base.get_response('system', 'version')}"
            )

        if "what can you do" in query_lower or "capabilities" in query_lower:
            caps = self.knowledge_base.get_response("capabilities")
            return "I can: " + ", ".join(caps)

        if "time" in query_lower:
            import datetime

            return datetime.datetime.now().strftime("%H:%M:%S")

        if "date" in query_lower:
            import datetime

            return datetime.datetime.now().strftime("%A, %B %d, %Y")

        return None

    async def generate_response(
        self, command: str, intent: ProcessedIntent
    ) -> Dict[str, Any]:
        self._stats["llm_calls"] += 1

        context = {
            "intent": intent.to_dict(),
            "memory_context": self._get_context_summary(),
        }

        if self._use_unified_llm and self.unified_llm:
            response = await self.unified_llm.generate(
                command, system_prompt=self._get_system_prompt()
            )
            text = response.text
        else:
            response = await self.llm_client.generate(command, context)
            text = response

        self._add_to_context({"role": "assistant", "content": text})

        return {"success": True, "message": text}

    def _get_system_prompt(self) -> str:
        return """You are AlphaOmega, a sophisticated AI assistant that controls a PC through voice commands.
You are helpful, concise, and professional. Address the user respectfully.
You can execute system commands, manage files, control applications, and provide information.
When the user gives a command, acknowledge it briefly and execute it.
Keep responses short and actionable."""

    def get_llm_stats(self) -> Dict[str, Any]:
        if self._use_unified_llm and self.unified_llm:
            return self.unified_llm.get_stats()
        return {}

    def get_available_providers(self) -> List[Dict[str, Any]]:
        if self._use_unified_llm and self.unified_llm:
            return self.unified_llm.get_available_providers()
        return []

    async def set_llm_provider(self, provider: str, model: str = None):
        if self._use_unified_llm and self.unified_llm:
            try:
                provider_type = ProviderType(provider)
                self.unified_llm.set_active_provider(provider_type, model)
                return {"success": True, "message": f"Switched to {provider}"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Unified LLM not initialized"}

    def _add_to_context(self, message: Dict[str, str]):
        self._context_window.append({"message": message, "timestamp": time.time()})

        total_length = sum(
            len(m["message"].get("content", "")) for m in self._context_window
        )
        while total_length > self._max_context and len(self._context_window) > 2:
            removed = self._context_window.pop(0)
            total_length -= len(removed["message"].get("content", ""))

    def _get_context_summary(self) -> str:
        recent = self._context_window[-5:]
        return " ".join(m["message"].get("content", "") for m in recent)

    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, "context_size": len(self._context_window)}

    def set_memory_system(self, memory_system):
        self.memory = memory_system
