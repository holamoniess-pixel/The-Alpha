#!/usr/bin/env python3
import os
import sys
import asyncio
from pathlib import Path

# --- AUTO-PATH FIX ---
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(1, str(BASE_DIR / "src"))
os.environ["PYTHONPATH"] = f"{BASE_DIR};{BASE_DIR / 'src'};{os.environ.get('PYTHONPATH', '')}"

from src.core.system import AlphaOmegaCore, SystemConfig
from src.api.web_server import run_server
import threading
import logging

if not os.path.exists("logs"): os.makedirs("logs")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

async def start_alpha():
    print("🚀 Initializing Alpha Omega...")
    try:
        config = SystemConfig.from_yaml("config.yaml")
        system = AlphaOmegaCore(config)
        success = await system.initialize()
        if not success:
            print("❌ System initialization failed. Try running 'fix_alpha.ps1'.")
            return
        print(f"✅ Wake Word Active: '{config.wake_word}'")
        await system.start()
        while True: await asyncio.sleep(1)
    except Exception as e:
        print(f"💥 Fatal error: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: run_server(port=8000), daemon=True).start()
    try: asyncio.run(start_alpha())
    except KeyboardInterrupt: print("\n👋 System stopped.")