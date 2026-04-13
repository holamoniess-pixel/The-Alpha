#!/usr/bin/env python3
"""
ALPHA OMEGA - OLLAMA INTEGRATION
Native Ollama Support for Local LLM
Version: 2.0.0
"""

import asyncio
import json
import logging
import os
import time
import hashlib
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass, field
from pathlib import Path
import httpx


@dataclass
class OllamaModel:
    name: str
    size: str
    digest: str
    modified_at: str
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def model_id(self) -> str:
        return self.name.split(":")[0] if ":" in self.name else self.name

    @property
    def tag(self) -> str:
        return self.name.split(":")[1] if ":" in self.name else "latest"

    @property
    def size_gb(self) -> float:
        try:
            size_bytes = int(self.size)
            return round(size_bytes / (1024**3), 2)
        except:
            return 0.0


@dataclass
class OllamaResponse:
    success: bool
    text: str
    model: str
    tokens_generated: int = 0
    tokens_prompt: int = 0
    latency_ms: float = 0.0
    context: List[int] = field(default_factory=list)
    error: str = ""


class OllamaClient:
    """Native Ollama API Client"""

    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 11434

    POPULAR_MODELS = {
        "llama3.2:1b": {
            "size": "1.3GB",
            "ram": "2GB",
            "quality": "good",
            "speed": "fast",
        },
        "llama3.2:3b": {
            "size": "2GB",
            "ram": "4GB",
            "quality": "excellent",
            "speed": "fast",
        },
        "llama3.1:8b": {
            "size": "4.7GB",
            "ram": "8GB",
            "quality": "excellent",
            "speed": "medium",
        },
        "llama3.3:70b": {
            "size": "42GB",
            "ram": "48GB",
            "quality": "excellent",
            "speed": "slow",
        },
        "mistral:7b": {
            "size": "4.1GB",
            "ram": "8GB",
            "quality": "excellent",
            "speed": "medium",
        },
        "codellama:7b": {
            "size": "3.8GB",
            "ram": "8GB",
            "quality": "excellent",
            "speed": "medium",
        },
        "deepseek-coder:6.7b": {
            "size": "3.8GB",
            "ram": "8GB",
            "quality": "excellent",
            "speed": "medium",
        },
        "phi3:mini": {
            "size": "2.2GB",
            "ram": "4GB",
            "quality": "excellent",
            "speed": "fast",
        },
        "gemma2:2b": {
            "size": "1.6GB",
            "ram": "4GB",
            "quality": "good",
            "speed": "fast",
        },
        "qwen2.5:0.5b": {
            "size": "0.4GB",
            "ram": "1GB",
            "quality": "basic",
            "speed": "ultra",
        },
        "qwen2.5:1.5b": {
            "size": "1GB",
            "ram": "2GB",
            "quality": "good",
            "speed": "fast",
        },
        "qwen2.5:7b": {
            "size": "4.7GB",
            "ram": "8GB",
            "quality": "excellent",
            "speed": "medium",
        },
        "llava:7b": {
            "size": "4.7GB",
            "ram": "8GB",
            "quality": "excellent",
            "speed": "medium",
            "multimodal": True,
        },
        "nomic-embed-text": {
            "size": "274MB",
            "ram": "1GB",
            "quality": "N/A",
            "speed": "ultra",
            "type": "embedding",
        },
    }

    def __init__(self, host: str = None, port: int = None):
        self.host = host or os.environ.get("OLLAMA_HOST", self.DEFAULT_HOST)
        self.port = port or int(os.environ.get("OLLAMA_PORT", self.DEFAULT_PORT))
        self.base_url = f"http://{self.host}:{self.port}"
        self.logger = logging.getLogger("OllamaClient")

        self._client = httpx.AsyncClient(timeout=300.0)
        self._models_cache: Dict[str, OllamaModel] = {}
        self._last_model_list: float = 0
        self._cache_ttl: int = 60

        self._stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_latency_ms": 0,
            "errors": 0,
        }

    async def is_running(self) -> bool:
        """Check if Ollama server is running"""
        try:
            response = await self._client.get(
                f"{self.base_url}/api/version", timeout=2.0
            )
            if response.status_code == 200:
                data = response.json()
                self.logger.info(
                    f"Ollama server running: {data.get('version', 'unknown')}"
                )
                return True
        except Exception as e:
            self.logger.debug(f"Ollama not running: {e}")
        return False

    async def get_version(self) -> Dict[str, Any]:
        """Get Ollama server version info"""
        try:
            response = await self._client.get(f"{self.base_url}/api/version")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.logger.error(f"Failed to get version: {e}")
        return {}

    async def list_models(self, force_refresh: bool = False) -> List[OllamaModel]:
        """List all installed models"""
        now = time.time()

        if (
            not force_refresh
            and self._models_cache
            and (now - self._last_model_list) < self._cache_ttl
        ):
            return list(self._models_cache.values())

        try:
            response = await self._client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = []
                self._models_cache.clear()

                for model_data in data.get("models", []):
                    model = OllamaModel(
                        name=model_data.get("name", "unknown"),
                        size=model_data.get("size", "0"),
                        digest=model_data.get("digest", ""),
                        modified_at=model_data.get("modified_at", ""),
                        details=model_data.get("details", {}),
                    )
                    models.append(model)
                    self._models_cache[model.name] = model

                self._last_model_list = now
                self.logger.info(f"Found {len(models)} installed models")
                return models
        except Exception as e:
            self.logger.error(f"Failed to list models: {e}")

        return []

    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get detailed info about a model"""
        try:
            response = await self._client.post(
                f"{self.base_url}/api/show", json={"name": model_name}
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.logger.error(f"Failed to get model info: {e}")
        return {}

    async def pull_model(self, model_name: str, stream: bool = False) -> bool:
        """Download/pull a model from Ollama registry"""
        self.logger.info(f"Pulling model: {model_name}")

        try:
            if stream:
                async with self._client.stream(
                    "POST",
                    f"{self.base_url}/api/pull",
                    json={"name": model_name, "stream": True},
                    timeout=600.0,
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            data = json.loads(line)
                            status = data.get("status", "")
                            if "completed" in status or "success" in status:
                                self.logger.info(
                                    f"Model {model_name} downloaded successfully"
                                )
                                return True
                            elif "error" in data:
                                self.logger.error(f"Pull error: {data['error']}")
                                return False
            else:
                response = await self._client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model_name, "stream": False},
                    timeout=600.0,
                )
                if response.status_code == 200:
                    self.logger.info(f"Model {model_name} downloaded successfully")
                    return True
        except Exception as e:
            self.logger.error(f"Failed to pull model: {e}")

        return False

    async def delete_model(self, model_name: str) -> bool:
        """Delete a model from local storage"""
        try:
            response = await self._client.delete(
                f"{self.base_url}/api/delete", json={"name": model_name}
            )
            if response.status_code == 200:
                self.logger.info(f"Model {model_name} deleted")
                if model_name in self._models_cache:
                    del self._models_cache[model_name]
                return True
        except Exception as e:
            self.logger.error(f"Failed to delete model: {e}")
        return False

    async def generate(
        self,
        prompt: str,
        model: str = "llama3.2:3b",
        system: str = "",
        context: List[int] = None,
        stream: bool = False,
        raw: bool = False,
        options: Dict[str, Any] = None,
    ) -> OllamaResponse:
        """Generate text using Ollama"""
        start_time = time.time()
        self._stats["total_requests"] += 1

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "raw": raw,
        }

        if system:
            payload["system"] = system
        if context:
            payload["context"] = context
        if options:
            payload["options"] = options

        default_options = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "num_predict": 512,
            "stop": ["</s>", "\n\n\n"],
        }

        if "options" not in payload:
            payload["options"] = default_options
        else:
            payload["options"] = {**default_options, **payload["options"]}

        try:
            response = await self._client.post(
                f"{self.base_url}/api/generate", json=payload, timeout=120.0
            )

            if response.status_code == 200:
                data = response.json()
                latency = (time.time() - start_time) * 1000

                self._stats["total_tokens"] += data.get("eval_count", 0)
                self._stats["total_latency_ms"] += latency

                return OllamaResponse(
                    success=True,
                    text=data.get("response", ""),
                    model=model,
                    tokens_generated=data.get("eval_count", 0),
                    tokens_prompt=data.get("prompt_eval_count", 0),
                    latency_ms=latency,
                    context=data.get("context", []),
                )
            else:
                self._stats["errors"] += 1
                return OllamaResponse(
                    success=False,
                    text="",
                    model=model,
                    error=f"HTTP {response.status_code}: {response.text}",
                )

        except Exception as e:
            self._stats["errors"] += 1
            return OllamaResponse(success=False, text="", model=model, error=str(e))

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "llama3.2:3b",
        stream: bool = False,
        options: Dict[str, Any] = None,
    ) -> OllamaResponse:
        """Chat with Ollama using message format"""
        start_time = time.time()
        self._stats["total_requests"] += 1

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }

        if options:
            payload["options"] = options

        try:
            response = await self._client.post(
                f"{self.base_url}/api/chat", json=payload, timeout=120.0
            )

            if response.status_code == 200:
                data = response.json()
                latency = (time.time() - start_time) * 1000

                message = data.get("message", {})

                self._stats["total_tokens"] += data.get("eval_count", 0)
                self._stats["total_latency_ms"] += latency

                return OllamaResponse(
                    success=True,
                    text=message.get("content", ""),
                    model=model,
                    tokens_generated=data.get("eval_count", 0),
                    tokens_prompt=data.get("prompt_eval_count", 0),
                    latency_ms=latency,
                )
            else:
                self._stats["errors"] += 1
                return OllamaResponse(
                    success=False,
                    text="",
                    model=model,
                    error=f"HTTP {response.status_code}",
                )

        except Exception as e:
            self._stats["errors"] += 1
            return OllamaResponse(success=False, text="", model=model, error=str(e))

    async def embed(
        self,
        input: str,
        model: str = "nomic-embed-text",
    ) -> List[float]:
        """Generate embeddings using Ollama"""
        try:
            response = await self._client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": model, "prompt": input},
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("embedding", [])
        except Exception as e:
            self.logger.error(f"Embedding error: {e}")

        return []

    async def embed_batch(
        self,
        inputs: List[str],
        model: str = "nomic-embed-text",
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        embeddings = []
        for text in inputs:
            emb = await self.embed(text, model)
            embeddings.append(emb)
        return embeddings

    async def stream_generate(
        self,
        prompt: str,
        model: str = "llama3.2:3b",
        system: str = "",
        options: Dict[str, Any] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream generation token by token"""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
        }

        if system:
            payload["system"] = system
        if options:
            payload["options"] = options

        try:
            async with self._client.stream(
                "POST", f"{self.base_url}/api/generate", json=payload, timeout=120.0
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                        if data.get("done", False):
                            break
        except Exception as e:
            self.logger.error(f"Stream error: {e}")

    def get_popular_models(self) -> Dict[str, Dict[str, Any]]:
        """Get list of popular/recommended models"""
        return self.POPULAR_MODELS

    async def recommend_model(
        self,
        task: str = "general",
        max_ram_gb: float = None,
        prefer_speed: bool = False,
    ) -> str:
        """Recommend best model based on requirements"""
        models = await self.list_models()
        installed = {m.model_id for m in models}

        if task == "code":
            candidates = ["deepseek-coder:6.7b", "codellama:7b", "llama3.1:8b"]
        elif task == "chat":
            candidates = ["llama3.2:3b", "mistral:7b", "llama3.1:8b"]
        elif task == "fast":
            candidates = ["llama3.2:1b", "qwen2.5:0.5b", "phi3:mini"]
        elif task == "vision":
            candidates = ["llava:7b"]
        else:
            candidates = ["llama3.2:3b", "llama3.2:1b", "phi3:mini", "mistral:7b"]

        for model in candidates:
            model_base = model.split(":")[0]
            if model_base in installed:
                return model

        if max_ram_gb:
            for model, info in self.POPULAR_MODELS.items():
                ram = float(info["ram"].replace("GB", ""))
                if ram <= max_ram_gb:
                    if prefer_speed and info.get("speed") in ["ultra", "fast"]:
                        return model
                    elif not prefer_speed:
                        return model

        return "llama3.2:3b"

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        avg_latency = (
            self._stats["total_latency_ms"] / self._stats["total_requests"]
            if self._stats["total_requests"] > 0
            else 0
        )
        return {
            **self._stats,
            "avg_latency_ms": round(avg_latency, 2),
            "cached_models": len(self._models_cache),
        }

    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()


class OllamaIntegration:
    """High-level Ollama integration for Alpha Omega"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.client = OllamaClient(
            host=self.config.get("ollama_host"),
            port=self.config.get("ollama_port"),
        )
        self.logger = logging.getLogger("OllamaIntegration")

        self._default_model = self.config.get("ollama_model", "llama3.2:3b")
        self._initialized = False
        self._available = False

    async def initialize(self) -> bool:
        """Initialize Ollama integration"""
        self.logger.info("Initializing Ollama integration...")

        self._available = await self.client.is_running()

        if self._available:
            version = await self.client.get_version()
            models = await self.client.list_models()

            self.logger.info(
                f"Ollama connected. Version: {version.get('version', 'unknown')}"
            )
            self.logger.info(f"Available models: {len(models)}")

            if not models:
                self.logger.warning("No models installed. Consider pulling one.")
                recommended = await self.client.recommend_model()
                self.logger.info(f"Recommended: ollama pull {recommended}")
        else:
            self.logger.warning(
                "Ollama server not running. Install from: https://ollama.ai"
            )

        self._initialized = True
        return self._available

    def is_available(self) -> bool:
        """Check if Ollama is available"""
        return self._available

    async def generate(
        self, prompt: str, model: str = None, system_prompt: str = "", **options
    ) -> OllamaResponse:
        """Generate text using Ollama"""
        if not self._available:
            return OllamaResponse(
                success=False,
                text="",
                model=model or self._default_model,
                error="Ollama not available",
            )

        model = model or self._default_model

        return await self.client.generate(
            prompt=prompt, model=model, system=system_prompt, options=options
        )

    async def chat(
        self, messages: List[Dict[str, str]], model: str = None, **options
    ) -> OllamaResponse:
        """Chat with Ollama"""
        if not self._available:
            return OllamaResponse(
                success=False,
                text="",
                model=model or self._default_model,
                error="Ollama not available",
            )

        model = model or self._default_model
        return await self.client.chat(messages=messages, model=model, options=options)

    async def stream(self, prompt: str, model: str = None) -> AsyncGenerator[str, None]:
        """Stream generation"""
        model = model or self._default_model
        async for token in self.client.stream_generate(prompt, model):
            yield token

    async def get_models(self) -> List[OllamaModel]:
        """Get list of installed models"""
        return await self.client.list_models()

    async def pull_model(self, model_name: str) -> bool:
        """Download a model"""
        return await self.client.pull_model(model_name)

    async def get_embeddings(self, text: str) -> List[float]:
        """Get text embeddings"""
        return await self.client.embed(text)

    async def quick_chat(self, message: str, model: str = None) -> str:
        """Quick one-off chat"""
        response = await self.chat(
            messages=[{"role": "user", "content": message}], model=model
        )
        return response.text if response.success else ""

    def get_info(self) -> Dict[str, Any]:
        """Get integration info"""
        return {
            "available": self._available,
            "default_model": self._default_model,
            "base_url": self.client.base_url,
            "stats": self.client.get_stats(),
        }
