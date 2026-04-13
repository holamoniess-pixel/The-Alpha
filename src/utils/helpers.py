#!/usr/bin/env python3
"""Alpha Omega Utilities Module"""

import os
import sys
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional


def ensure_directories():
    """Create required directories"""
    dirs = ["logs", "data", "models"]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """Setup logging with file and console handlers"""
    ensure_directories()

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(level)
        console.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(console)

        log_file = Path("logs") / f"{name}_{time.strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(file_handler)

    return logger


def get_config_value(config: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Get nested config value by dot-separated path"""
    keys = path.split(".")
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value


def timing_decorator(func):
    """Decorator to measure function execution time"""

    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = (time.time() - start) * 1000
        if hasattr(result, "__dict__"):
            result._timing_ms = elapsed
        return result

    return wrapper


async def async_timing_decorator(func):
    """Async decorator to measure function execution time"""

    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        elapsed = (time.time() - start) * 1000
        if hasattr(result, "__dict__"):
            result._timing_ms = elapsed
        return result

    return wrapper


class Singleton(type):
    """Singleton metaclass"""

    _instances = {}
    _lock = None

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            if cls._lock is None:
                import threading

                cls._lock = threading.Lock()
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
