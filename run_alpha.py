#!/usr/bin/env python3
"""
ALPHA OMEGA - MAIN ENTRY POINT
Production-Ready AI Assistant System
Version: 2.0.0
"""

import asyncio
import sys
import os
import signal
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.system import AlphaOmegaCore, SystemConfig
from src.api.web_server import run_server
import threading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/alpha_omega.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger("Main")


def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}")
    sys.exit(0)


async def run_system():
    config = SystemConfig.from_yaml("config.yaml")

    system = AlphaOmegaCore(config)

    try:
        success = await system.initialize()

        if not success:
            logger.error("System initialization failed")
            return 1

        await system.start()

        logger.info("=" * 60)
        logger.info("ALPHA OMEGA SYSTEM RUNNING")
        logger.info(f"Wake Word: '{config.wake_word}'")
        logger.info(f"API Server: http://localhost:8000")
        logger.info("=" * 60)

        while system._running:
            await asyncio.sleep(1)

        return 0

    except KeyboardInterrupt:
        logger.info("Shutdown requested...")
        await system.shutdown()
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await system.shutdown()
        return 1


def run_api_server():
    run_server(host="0.0.0.0", port=8000)


async def main():
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()

    exit_code = await run_system()

    return exit_code


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
