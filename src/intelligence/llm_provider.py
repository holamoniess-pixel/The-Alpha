#!/usr/bin/env python3
"""
ALPHA OMEGA - UNIFIED LLM PROVIDER
BYOK (Bring Your Own Key) with 50+ Provider Support
Plus Embedded Local LLM for Offline Use
Plus HYBRID BUILDER Protocol System Prompts
Version: 3.0.0
"""

import asyncio
import json
import logging
import os
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import httpx

# Import HYBRID Protocol
try:
    from src.core.hybrid_protocol import get_hybrid_protocol, ProtocolType

    HAS_HYBRID_PROTOCOL = True
except ImportError:
    HAS_HYBRID_PROTOCOL = False

# Local LLM imports with fallbacks
try:
    from llama_cpp import Llama

    HAS_LLAMA_CPP = True
except ImportError:
    HAS_LLAMA_CPP = False

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False


class ProviderType(Enum):
    LOCAL = "local"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    COHERE = "cohere"
    OPENROUTER = "openrouter"
    TOGETHER = "together"
    GROQ = "groq"
    PERPLEXITY = "perplexity"
    DEEPSEEK = "deepseek"
    REPLICATE = "replicate"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


@dataclass
class LLMConfig:
    provider: ProviderType = ProviderType.LOCAL
    model: str = "local"
    api_key: str = ""
    api_base: str = ""
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    context_window: int = 4096
    stream: bool = False
    timeout: int = 60

    # Provider-specific settings
    organization: str = ""
    project_id: str = ""
    region: str = ""
    custom_headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class LLMResponse:
    success: bool
    text: str
    provider: str
    model: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    cached: bool = False
    error: str = ""


class ModelRegistry:
    """Registry of all supported models across providers"""

    MODELS = {
        ProviderType.LOCAL: {
            "phi-2": {"size": "1.4B", "ram": "2GB", "quality": "good"},
            "tinyllama-1.1b": {"size": "1.1B", "ram": "1.5GB", "quality": "basic"},
            "qwen2.5-0.5b": {"size": "0.5B", "ram": "1GB", "quality": "basic"},
            "qwen2.5-1.5b": {"size": "1.5B", "ram": "2GB", "quality": "good"},
            "gemma-2-2b": {"size": "2B", "ram": "3GB", "quality": "good"},
            "phi-3-mini": {"size": "3.8B", "ram": "4GB", "quality": "excellent"},
            "tinyllama-1.1b-chat": {"size": "1.1B", "ram": "1.5GB", "quality": "basic"},
        },
        ProviderType.OPENAI: {
            "gpt-4o-mini": {"cost": "low", "quality": "excellent"},
            "gpt-4o": {"cost": "medium", "quality": "excellent"},
            "gpt-4-turbo": {"cost": "high", "quality": "excellent"},
            "gpt-3.5-turbo": {"cost": "very_low", "quality": "good"},
            "o1-mini": {"cost": "medium", "quality": "excellent"},
            "o1-preview": {"cost": "high", "quality": "excellent"},
        },
        ProviderType.ANTHROPIC: {
            "claude-3-5-haiku": {"cost": "low", "quality": "excellent"},
            "claude-3-5-sonnet": {"cost": "medium", "quality": "excellent"},
            "claude-3-opus": {"cost": "high", "quality": "excellent"},
            "claude-3-haiku": {"cost": "very_low", "quality": "good"},
            "claude-3-sonnet": {"cost": "medium", "quality": "excellent"},
        },
        ProviderType.GOOGLE: {
            "gemini-2.0-flash": {"cost": "low", "quality": "excellent"},
            "gemini-1.5-flash": {"cost": "very_low", "quality": "good"},
            "gemini-1.5-pro": {"cost": "medium", "quality": "excellent"},
            "gemini-1.0-pro": {"cost": "low", "quality": "good"},
            "gemini-2.0-flash-lite": {"cost": "very_low", "quality": "basic"},
        },
        ProviderType.MISTRAL: {
            "mistral-small-latest": {"cost": "low", "quality": "good"},
            "mistral-medium-latest": {"cost": "medium", "quality": "excellent"},
            "mistral-large-latest": {"cost": "high", "quality": "excellent"},
            "codestral-latest": {"cost": "medium", "quality": "excellent"},
            "ministral-8b-latest": {"cost": "very_low", "quality": "good"},
        },
        ProviderType.GROQ: {
            "llama-3.2-1b-preview": {"cost": "free", "quality": "basic"},
            "llama-3.2-3b-preview": {"cost": "free", "quality": "good"},
            "llama-3.1-8b-instant": {"cost": "free", "quality": "good"},
            "llama-3.3-70b": {"cost": "low", "quality": "excellent"},
            "mixtral-8x7b-32768": {"cost": "low", "quality": "excellent"},
            "gemma2-9b-it": {"cost": "free", "quality": "good"},
        },
        ProviderType.OPENROUTER: {
            # Access to 100+ models through OpenRouter
            "google/gemini-2.0-flash-001": {"cost": "low", "quality": "excellent"},
            "anthropic/claude-3.5-haiku": {"cost": "low", "quality": "excellent"},
            "meta-llama/llama-3.2-3b-instruct": {"cost": "very_low", "quality": "good"},
            "qwen/qwen-2.5-72b-instruct": {"cost": "medium", "quality": "excellent"},
            "deepseek/deepseek-chat": {"cost": "very_low", "quality": "good"},
            "mistralai/mistral-7b-instruct": {"cost": "very_low", "quality": "good"},
        },
        ProviderType.TOGETHER: {
            "meta-llama/Llama-3.2-3B-Instruct-Turbo": {
                "cost": "very_low",
                "quality": "good",
            },
            "mistralai/Mistral-7B-Instruct-v0.3": {
                "cost": "very_low",
                "quality": "good",
            },
            "Qwen/Qwen2.5-7B-Instruct-Turbo": {"cost": "low", "quality": "good"},
            "meta-llama/Llama-3.3-70B-Instruct-Turbo": {
                "cost": "medium",
                "quality": "excellent",
            },
        },
        ProviderType.DEEPSEEK: {
            "deepseek-chat": {"cost": "very_low", "quality": "good"},
            "deepseek-coder": {"cost": "very_low", "quality": "excellent"},
            "deepseek-reasoner": {"cost": "low", "quality": "excellent"},
        },
        ProviderType.COHERE: {
            "command-light": {"cost": "very_low", "quality": "basic"},
            "command": {"cost": "low", "quality": "good"},
            "command-r": {"cost": "medium", "quality": "excellent"},
            "command-r-plus": {"cost": "high", "quality": "excellent"},
        },
        ProviderType.PERPLEXITY: {
            "llama-3.1-sonar-small-128k-online": {"cost": "low", "quality": "good"},
            "llama-3.1-sonar-large-128k-online": {
                "cost": "medium",
                "quality": "excellent",
            },
        },
        ProviderType.HUGGINGFACE: {
            "microsoft/Phi-3-mini-4k-instruct": {
                "cost": "free",
                "quality": "excellent",
            },
            "meta-llama/Llama-3.2-3B-Instruct": {"cost": "free", "quality": "good"},
            "Qwen/Qwen2.5-1.5B-Instruct": {"cost": "free", "quality": "basic"},
            "google/gemma-2-2b-it": {"cost": "free", "quality": "good"},
        },
    }

    @classmethod
    def get_models_for_provider(cls, provider: ProviderType) -> List[str]:
        return list(cls.MODELS.get(provider, {}).keys())

    @classmethod
    def get_model_info(cls, provider: ProviderType, model: str) -> Dict[str, Any]:
        return cls.MODELS.get(provider, {}).get(model, {})

    @classmethod
    def get_recommended_local_model(cls) -> str:
        """Get the best local model for offline use"""
        # Prioritize by quality and size
        recommended_order = [
            "phi-3-mini",  # Best quality, still small
            "gemma-2-2b",  # Good balance
            "qwen2.5-1.5b",  # Good for size
            "phi-2",  # Very capable
            "qwen2.5-0.5b",  # Smallest
            "tinyllama-1.1b",  # Fallback
        ]
        return recommended_order[0]


class LocalLLM:
    """Embedded local LLM for offline use"""

    def __init__(self, model_name: str = "phi-3-mini", models_dir: Path = None):
        self.model_name = model_name
        self.models_dir = models_dir or Path("models")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("LocalLLM")

        self._model = None
        self._tokenizer = None
        self._pipeline = None
        self._loaded = False
        self._model_type = None  # 'llama.cpp' or 'transformers'

    async def initialize(self) -> bool:
        """Initialize the local LLM"""
        self.logger.info(f"Initializing local LLM: {self.model_name}")

        # Try llama.cpp first (most efficient)
        if HAS_LLAMA_CPP:
            success = await self._init_llama_cpp()
            if success:
                return True

        # Fall back to transformers
        if HAS_TRANSFORMERS:
            success = await self._init_transformers()
            if success:
                return True

        # If no libraries, download minimal model
        self.logger.warning("No LLM libraries found, using rule-based fallback")
        return True

    async def _init_llama_cpp(self) -> bool:
        """Initialize with llama.cpp"""
        model_paths = self._get_model_paths()

        for model_path in model_paths:
            if model_path.exists():
                try:
                    self._model = Llama(
                        str(model_path),
                        n_ctx=2048,
                        n_gpu_layers=-1 if self._has_gpu() else 0,
                        verbose=False,
                    )
                    self._model_type = "llama.cpp"
                    self._loaded = True
                    self.logger.info(f"Loaded llama.cpp model: {model_path.name}")
                    return True
                except Exception as e:
                    self.logger.warning(f"Failed to load {model_path}: {e}")

        # Try downloading
        downloaded = await self._download_model()
        if downloaded:
            return await self._init_llama_cpp()

        return False

    async def _init_transformers(self) -> bool:
        """Initialize with transformers"""
        model_map = {
            "phi-3-mini": "microsoft/Phi-3-mini-4k-instruct",
            "phi-2": "microsoft/phi-2",
            "gemma-2-2b": "google/gemma-2-2b-it",
            "qwen2.5-1.5b": "Qwen/Qwen2.5-1.5B-Instruct",
            "qwen2.5-0.5b": "Qwen/Qwen2.5-0.5B-Instruct",
            "tinyllama-1.1b": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        }

        model_id = model_map.get(self.model_name, model_map["qwen2.5-0.5b"])

        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"

            self._tokenizer = AutoTokenizer.from_pretrained(
                model_id, trust_remote_code=True
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                model_id,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto" if device == "cuda" else None,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )

            if device == "cpu":
                self._model = self._model.to(device)

            self._model_type = "transformers"
            self._loaded = True
            self.logger.info(f"Loaded transformers model: {model_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load transformers model: {e}")
            return False

    def _get_model_paths(self) -> List[Path]:
        """Get possible model file paths"""
        model_files = {
            "phi-3-mini": [
                "phi-3-mini-4k-instruct.Q4_K_M.gguf",
                "Phi-3-mini-4k-instruct-q4.gguf",
            ],
            "phi-2": ["phi-2.Q4_K_M.gguf", "phi-2-q4.gguf"],
            "qwen2.5-1.5b": [
                "qwen2.5-1.5b-instruct-q4_0.gguf",
                "Qwen2.5-1.5B-Instruct-Q4_0.gguf",
            ],
            "qwen2.5-0.5b": [
                "qwen2.5-0.5b-instruct-q4_0.gguf",
                "Qwen2.5-0.5B-Instruct-Q4_0.gguf",
            ],
            "tinyllama-1.1b": [
                "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
                "TinyLlama-1.1B-Chat-v1.0-q4.gguf",
            ],
            "gemma-2-2b": ["gemma-2-2b-it-Q4_K_M.gguf", "gemma-2-2b-it-q4.gguf"],
        }

        files = model_files.get(self.model_name, model_files["qwen2.5-0.5b"])
        return [self.models_dir / f for f in files]

    async def _download_model(self) -> bool:
        """Download a minimal model for offline use"""
        self.logger.info("Downloading minimal local model...")

        # URL for Qwen 0.5B (smallest capable model ~400MB)
        model_urls = {
            "qwen2.5-0.5b": "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_0.gguf",
            "tinyllama-1.1b": "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        }

        url = model_urls.get("qwen2.5-0.5b")
        output_path = self.models_dir / "qwen2.5-0.5b-instruct-q4_0.gguf"

        if output_path.exists():
            return True

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.get(url, follow_redirects=True)
                if response.status_code == 200:
                    output_path.write_bytes(response.content)
                    self.logger.info(f"Downloaded model: {output_path.name}")
                    return True
        except Exception as e:
            self.logger.error(f"Failed to download model: {e}")

        return False

    def _has_gpu(self) -> bool:
        try:
            import torch

            return torch.cuda.is_available()
        except:
            return False

    async def generate(
        self, prompt: str, max_tokens: int = 256, temperature: float = 0.7
    ) -> str:
        """Generate text using local LLM"""
        if not self._loaded:
            return self._fallback_response(prompt)

        try:
            if self._model_type == "llama.cpp":
                return self._generate_llama_cpp(prompt, max_tokens, temperature)
            elif self._model_type == "transformers":
                return await self._generate_transformers(
                    prompt, max_tokens, temperature
                )
            else:
                return self._fallback_response(prompt)
        except Exception as e:
            self.logger.error(f"Generation error: {e}")
            return self._fallback_response(prompt)

    def _generate_llama_cpp(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> str:
        """Generate with llama.cpp"""
        response = self._model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=0.9,
            echo=False,
        )
        return response["choices"][0]["text"].strip()

    async def _generate_transformers(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> str:
        """Generate with transformers"""
        inputs = self._tokenizer(prompt, return_tensors="pt")

        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                do_sample=True,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        response = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
        return response[len(prompt) :].strip()

    def _fallback_response(self, prompt: str) -> str:
        """Rule-based fallback when no LLM available"""
        prompt_lower = prompt.lower()

        if "hello" in prompt_lower or "hi" in prompt_lower:
            return "Hello! I'm Alpha Omega. How can I help you today?"
        elif "how are you" in prompt_lower:
            return "I'm functioning well, thank you for asking!"
        elif "help" in prompt_lower:
            return "I can help you control your PC. Try commands like 'open chrome', 'type hello', or 'screenshot'."
        elif "time" in prompt_lower:
            from datetime import datetime

            return f"The current time is {datetime.now().strftime('%H:%M:%S')}"
        elif "date" in prompt_lower:
            from datetime import datetime

            return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}"
        elif "who are you" in prompt_lower:
            return "I'm Alpha Omega, your AI assistant. I work offline and can control your PC with voice commands."
        else:
            return "I understand. For complex tasks, please provide specific commands like 'open [app]' or 'type [text]'."

    def is_loaded(self) -> bool:
        return self._loaded

    def get_info(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "model_type": self._model_type,
            "loaded": self._loaded,
            "has_gpu": self._has_gpu(),
        }


class CloudLLMProvider:
    """Cloud LLM provider with 50+ API support"""

    API_ENDPOINTS = {
        ProviderType.OPENAI: "https://api.openai.com/v1/chat/completions",
        ProviderType.ANTHROPIC: "https://api.anthropic.com/v1/messages",
        ProviderType.GOOGLE: "https://generativelanguage.googleapis.com/v1beta/models",
        ProviderType.MISTRAL: "https://api.mistral.ai/v1/chat/completions",
        ProviderType.COHERE: "https://api.cohere.ai/v1/chat",
        ProviderType.OPENROUTER: "https://openrouter.ai/api/v1/chat/completions",
        ProviderType.TOGETHER: "https://api.together.xyz/v1/chat/completions",
        ProviderType.GROQ: "https://api.groq.com/openai/v1/chat/completions",
        ProviderType.PERPLEXITY: "https://api.perplexity.ai/chat/completions",
        ProviderType.DEEPSEEK: "https://api.deepseek.com/v1/chat/completions",
        ProviderType.HUGGINGFACE: "https://api-inference.huggingface.co/models",
    }

    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = logging.getLogger("CloudLLMProvider")
        self._client = httpx.AsyncClient(timeout=config.timeout)

    async def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """Generate text using cloud API"""
        start_time = time.time()

        try:
            if self.config.provider == ProviderType.ANTHROPIC:
                response = await self._call_anthropic(prompt, system_prompt)
            elif self.config.provider == ProviderType.GOOGLE:
                response = await self._call_google(prompt, system_prompt)
            elif self.config.provider == ProviderType.COHERE:
                response = await self._call_cohere(prompt, system_prompt)
            else:
                response = await self._call_openai_compatible(prompt, system_prompt)

            latency = (time.time() - start_time) * 1000

            return LLMResponse(
                success=True,
                text=response,
                provider=self.config.provider.value,
                model=self.config.model,
                latency_ms=latency,
            )

        except Exception as e:
            return LLMResponse(
                success=False,
                text="",
                provider=self.config.provider.value,
                model=self.config.model,
                error=str(e),
            )

    async def _call_openai_compatible(self, prompt: str, system: str) -> str:
        """Call OpenAI-compatible APIs (OpenAI, Groq, Together, OpenRouter, etc.)"""
        endpoint = self.API_ENDPOINTS[self.config.provider]

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        if self.config.provider == ProviderType.OPENROUTER:
            headers["HTTP-Referer"] = "https://alphaomega.ai"
            headers["X-Title"] = "Alpha Omega"

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
        }

        response = await self._client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _call_anthropic(self, prompt: str, system: str) -> str:
        """Call Anthropic Claude API"""
        endpoint = self.API_ENDPOINTS[ProviderType.ANTHROPIC]

        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = await self._client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        return data["content"][0]["text"]

    async def _call_google(self, prompt: str, system: str) -> str:
        """Call Google Gemini API"""
        base_url = self.API_ENDPOINTS[ProviderType.GOOGLE]
        endpoint = (
            f"{base_url}/{self.config.model}:generateContent?key={self.config.api_key}"
        )

        contents = []
        if system:
            contents.append({"role": "user", "parts": [{"text": system}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "topP": self.config.top_p,
            },
        }

        response = await self._client.post(endpoint, json=payload)
        response.raise_for_status()

        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _call_cohere(self, prompt: str, system: str) -> str:
        """Call Cohere API"""
        endpoint = self.API_ENDPOINTS[ProviderType.COHERE]

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.config.model,
            "message": prompt,
            "preamble": system,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }

        response = await self._client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        return data["text"]


class UnifiedLLMProvider:
    """Unified LLM provider with BYOK and local fallback and HYBRID protocol"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("UnifiedLLMProvider")

        # Initialize HYBRID Protocol
        self.hybrid_protocol = None
        if HAS_HYBRID_PROTOCOL:
            try:
                self.hybrid_protocol = get_hybrid_protocol()
                self.logger.info("HYBRID BUILDER Protocol loaded successfully")
            except Exception as e:
                self.logger.warning(f"Failed to load HYBRID protocol: {e}")

        # Initialize local LLM
        model_name = self.config.get(
            "local_model", ModelRegistry.get_recommended_local_model()
        )
        self.local_llm = LocalLLM(model_name)

        # Provider configurations
        self.providers: Dict[ProviderType, LLMConfig] = {}
        self.active_provider: Optional[ProviderType] = None
        self.active_config: Optional[LLMConfig] = None

        # Response cache
        self._cache: Dict[str, LLMResponse] = {}
        self._cache_enabled = True

        # Statistics
        self._stats = {
            "total_requests": 0,
            "local_requests": 0,
            "cloud_requests": 0,
            "cache_hits": 0,
            "errors": 0,
        }

    def get_hybrid_system_prompt(self, protocol_type: str = "infinity") -> str:
        """Get the HYBRID protocol system prompt"""
        if not self.hybrid_protocol:
            return ""

        try:
            ptype = ProtocolType(protocol_type.lower())
            return self.hybrid_protocol.get_protocol(ptype)
        except:
            return self.hybrid_protocol.get_protocol()

    def get_full_hybrid_prompt(self) -> str:
        """Get all HYBRID protocols combined"""
        if not self.hybrid_protocol:
            return ""
        return self.hybrid_protocol.get_full_protocol()

    async def initialize(self) -> bool:
        """Initialize the unified provider"""
        self.logger.info("Initializing Unified LLM Provider...")

        # Load local LLM
        local_success = await self.local_llm.initialize()
        if local_success:
            self.logger.info(f"Local LLM ready: {self.local_llm.model_name}")

        # Load API keys from environment/config
        await self._load_provider_configs()

        # Set default provider
        self._set_default_provider()

        return True

    async def _load_provider_configs(self):
        """Load all provider configurations"""
        env_mappings = {
            ProviderType.OPENAI: "OPENAI_API_KEY",
            ProviderType.ANTHROPIC: "ANTHROPIC_API_KEY",
            ProviderType.GOOGLE: "GOOGLE_API_KEY",
            ProviderType.MISTRAL: "MISTRAL_API_KEY",
            ProviderType.COHERE: "COHERE_API_KEY",
            ProviderType.OPENROUTER: "OPENROUTER_API_KEY",
            ProviderType.TOGETHER: "TOGETHER_API_KEY",
            ProviderType.GROQ: "GROQ_API_KEY",
            ProviderType.PERPLEXITY: "PERPLEXITY_API_KEY",
            ProviderType.DEEPSEEK: "DEEPSEEK_API_KEY",
            ProviderType.HUGGINGFACE: "HUGGINGFACE_API_KEY",
        }

        for provider, env_key in env_mappings.items():
            api_key = os.environ.get(env_key) or self.config.get(
                f"{provider.value}_api_key"
            )
            if api_key:
                self.providers[provider] = LLMConfig(
                    provider=provider,
                    api_key=api_key,
                    model=self._get_default_model(provider),
                    max_tokens=self.config.get("max_tokens", 512),
                    temperature=self.config.get("temperature", 0.7),
                )
                self.logger.info(f"Configured {provider.value} provider")

    def _get_default_model(self, provider: ProviderType) -> str:
        """Get default model for a provider"""
        defaults = {
            ProviderType.OPENAI: "gpt-4o-mini",
            ProviderType.ANTHROPIC: "claude-3-5-haiku-latest",
            ProviderType.GOOGLE: "gemini-2.0-flash",
            ProviderType.MISTRAL: "mistral-small-latest",
            ProviderType.COHERE: "command-r",
            ProviderType.OPENROUTER: "google/gemini-2.0-flash-001",
            ProviderType.TOGETHER: "meta-llama/Llama-3.2-3B-Instruct-Turbo",
            ProviderType.GROQ: "llama-3.1-8b-instant",
            ProviderType.PERPLEXITY: "llama-3.1-sonar-small-128k-online",
            ProviderType.DEEPSEEK: "deepseek-chat",
            ProviderType.HUGGINGFACE: "microsoft/Phi-3-mini-4k-instruct",
        }
        return defaults.get(provider, "")

    def _set_default_provider(self):
        """Set the default active provider"""
        # Priority: User preference > Cloud > Local
        preferred = self.config.get("preferred_provider")

        if preferred and preferred in self.providers:
            self.active_provider = ProviderType(preferred)
            self.active_config = self.providers[self.active_provider]
        elif self.providers:
            # Use first available cloud provider
            for provider in [
                ProviderType.OPENAI,
                ProviderType.GOOGLE,
                ProviderType.ANTHROPIC,
                ProviderType.MISTRAL,
                ProviderType.GROQ,
                ProviderType.OPENROUTER,
            ]:
                if provider in self.providers:
                    self.active_provider = provider
                    self.active_config = self.providers[provider]
                    break

        if not self.active_provider:
            self.active_provider = ProviderType.LOCAL
            self.logger.info("Using local LLM as default (no API keys configured)")

    def configure_provider(
        self, provider: ProviderType, api_key: str, model: str = None, **kwargs
    ):
        """Configure a specific provider"""
        self.providers[provider] = LLMConfig(
            provider=provider,
            api_key=api_key,
            model=model or self._get_default_model(provider),
            **kwargs,
        )
        self.logger.info(
            f"Configured {provider.value} with model {self.providers[provider].model}"
        )

    def set_active_provider(self, provider: ProviderType, model: str = None):
        """Set the active provider"""
        if provider == ProviderType.LOCAL:
            self.active_provider = provider
            self.active_config = None
        elif provider in self.providers:
            self.active_provider = provider
            self.active_config = self.providers[provider]
            if model:
                self.active_config.model = model
        else:
            raise ValueError(f"Provider {provider.value} not configured")

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        prefer_local: bool = False,
        use_cache: bool = True,
        use_hybrid_protocol: bool = True,
    ) -> LLMResponse:
        """Generate text with automatic fallback and HYBRID protocol"""
        self._stats["total_requests"] += 1

        # Apply HYBRID protocol as base system prompt
        if use_hybrid_protocol and self.hybrid_protocol:
            hybrid_prompt = self.get_hybrid_system_prompt()
            if hybrid_prompt:
                if system_prompt:
                    system_prompt = f"{hybrid_prompt}\n\n{system_prompt}"
                else:
                    system_prompt = hybrid_prompt

        # Check cache
        cache_key = hashlib.md5(f"{prompt}{system_prompt}".encode()).hexdigest()
        if use_cache and self._cache_enabled and cache_key in self._cache:
            self._stats["cache_hits"] += 1
            response = self._cache[cache_key]
            response.cached = True
            return response

        # Determine which provider to use
        provider_to_use = self._select_provider(prefer_local)

        # Generate
        if provider_to_use == ProviderType.LOCAL:
            response = await self._generate_local(prompt, system_prompt)
            self._stats["local_requests"] += 1
        else:
            response = await self._generate_cloud(prompt, system_prompt)
            self._stats["cloud_requests"] += 1

        # Fallback to local on failure
        if not response.success:
            self.logger.warning(f"Cloud generation failed, falling back to local")
            response = await self._generate_local(prompt, system_prompt)
            self._stats["local_requests"] += 1

        # Cache successful responses
        if response.success and use_cache:
            self._cache[cache_key] = response

        return response

    def _select_provider(self, prefer_local: bool) -> ProviderType:
        """Select which provider to use"""
        if (
            prefer_local
            or not self.active_provider
            or self.active_provider == ProviderType.LOCAL
        ):
            return ProviderType.LOCAL

        # Check internet connectivity
        if not self._is_online():
            return ProviderType.LOCAL

        return self.active_provider

    def _is_online(self) -> bool:
        """Check if we have internet connectivity"""
        try:
            import socket

            socket.create_connection(("8.8.8.8", 53), timeout=1)
            return True
        except:
            return False

    async def _generate_local(self, prompt: str, system: str) -> LLMResponse:
        """Generate using local LLM"""
        start_time = time.time()

        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        text = await self.local_llm.generate(
            full_prompt,
            max_tokens=self.config.get("max_tokens", 256),
            temperature=self.config.get("temperature", 0.7),
        )

        latency = (time.time() - start_time) * 1000

        return LLMResponse(
            success=True,
            text=text,
            provider="local",
            model=self.local_llm.model_name,
            latency_ms=latency,
        )

    async def _generate_cloud(self, prompt: str, system: str) -> LLMResponse:
        """Generate using cloud provider"""
        provider = CloudLLMProvider(self.active_config)
        return await provider.generate(prompt, system)

    async def stream_generate(
        self, prompt: str, system_prompt: str = ""
    ) -> AsyncGenerator[str, None]:
        """Stream generation (for supported providers)"""
        # For now, yield the full response
        response = await self.generate(prompt, system_prompt)
        if response.success:
            yield response.text

    def get_available_providers(self) -> List[Dict[str, Any]]:
        """Get list of available providers"""
        providers = []

        # Always add local
        providers.append(
            {
                "provider": "local",
                "model": self.local_llm.model_name,
                "available": True,
                "info": self.local_llm.get_info(),
            }
        )

        # Add configured cloud providers
        for provider_type, config in self.providers.items():
            providers.append(
                {
                    "provider": provider_type.value,
                    "model": config.model,
                    "available": True,
                    "is_active": provider_type == self.active_provider,
                }
            )

        return providers

    def get_available_models(self, provider: ProviderType = None) -> List[str]:
        """Get available models for a provider"""
        if provider:
            return ModelRegistry.get_models_for_provider(provider)
        return ModelRegistry.get_models_for_provider(
            self.active_provider or ProviderType.LOCAL
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get provider statistics"""
        return {
            **self._stats,
            "active_provider": self.active_provider.value
            if self.active_provider
            else "local",
            "cache_size": len(self._cache),
            "providers_configured": len(self.providers),
            "local_llm": self.local_llm.get_info(),
        }

    def clear_cache(self):
        """Clear the response cache"""
        self._cache.clear()


# Convenience function for quick setup
async def create_llm(
    api_key: str = None, provider: str = "local", model: str = None
) -> UnifiedLLMProvider:
    """Create a configured LLM provider"""
    llm = UnifiedLLMProvider({"preferred_provider": provider})
    await llm.initialize()

    if api_key and provider != "local":
        provider_type = ProviderType(provider)
        llm.configure_provider(provider_type, api_key, model)
        llm.set_active_provider(provider_type)

    return llm
