#!/usr/bin/env python3
import os
import sys
import asyncio
import threading
import logging
import webbrowser
import time
from pathlib import Path

# --- AUTO-PATH FIX ---
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(1, str(BASE_DIR / "src"))
os.environ["PYTHONPATH"] = f"{BASE_DIR};{BASE_DIR / 'src'};{os.environ.get('PYTHONPATH', '')}"

from src.core.system import AlphaOmegaCore, SystemConfig, get_system
from src.api.web_server import run_server

# --- LOGGING SETUP ---
if not os.path.exists("logs"): os.makedirs("logs")
logging.basicConfig(level=logging.ERROR) # Quiet logging for cleaner terminal

async def terminal_loop(system):
    print("\n" + "="*60)
    print("🤖 ALPHA OMEGA INTERACTIVE TERMINAL")
    print("Type your commands below. Say 'exit' to quit.")
    print("="*60 + "\n")
    
    while True:
        try:
            command = input("Alpha >> ").strip()
            if not command: continue
            if command.lower() in ["exit", "quit", "bye"]: break
            
            result = await system.process_command(command)
            print(f"Response: {result.get('message', 'No response')}")
            
        except KeyboardInterrupt: break
        except Exception as e: print(f"Error: {e}")

async def main_engine():
    config = SystemConfig.from_yaml("config.yaml")
    system = get_system(config)
    
    print("🚀 Initializing Alpha Omega Engine...")
    success = await system.initialize()
    if not success:
        print("❌ System initialization failed.")
        return

    # Start API in background thread
    threading.Thread(target=lambda: run_server(port=8000), daemon=True).start()
    
    # Give server a moment to start
    time.sleep(2)
    
    # Launch Web UI
    print("🌐 Launching Admin Dashboard: http://localhost:8000/ui")
    webbrowser.open("http://localhost:8000/ui")
    
    # Start System Logic
    asyncio.create_task(system.start())
    
    # Enter Terminal Loop
    await terminal_loop(system)
    
    await system.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main_engine())
    except KeyboardInterrupt:
        print("\n👋 System stopped.")