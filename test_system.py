#!/usr/bin/env python3
"""
ALPHA OMEGA - SYSTEM TEST
Verify all components are working
Version: 2.0.0
"""

import sys
import os
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test all module imports"""
    print("\n[1/5] Testing imports...")

    modules = [
        ("src.core.system", "Core System"),
        ("src.memory.memory_system", "Memory System"),
        ("src.automation.automation_engine", "Automation Engine"),
        ("src.voice.voice_system", "Voice System"),
        ("src.intelligence.intelligence_engine", "Intelligence Engine"),
        ("src.learning.learning_engine", "Learning Engine"),
        ("src.security.security_framework", "Security Framework"),
        ("src.vault.vault_manager", "Vault Manager"),
        ("src.vision.vision_system", "Vision System"),
        ("src.api.web_server", "Web API"),
    ]

    success = 0
    for module, name in modules:
        try:
            __import__(module)
            print(f"  ✓ {name}")
            success += 1
        except Exception as e:
            print(f"  ✗ {name}: {e}")

    print(f"\n  Imported {success}/{len(modules)} modules")
    return success == len(modules)


def test_directories():
    """Test required directories exist"""
    print("\n[2/5] Testing directories...")

    dirs = ["logs", "data", "src"]
    for d in dirs:
        path = Path(d)
        if path.exists():
            print(f"  ✓ {d}/")
        else:
            print(f"  ✗ {d}/ (creating...)")
            path.mkdir(parents=True, exist_ok=True)

    return True


def test_config():
    """Test configuration file"""
    print("\n[3/5] Testing configuration...")

    config_path = Path("config.yaml")
    if config_path.exists():
        print("  ✓ config.yaml found")
        return True
    else:
        print("  ⚠ config.yaml not found (will use defaults)")
        return True


def test_dependencies():
    """Test optional dependencies"""
    print("\n[4/5] Testing dependencies...")

    optional = {
        "cv2": "OpenCV (vision)",
        "pyaudio": "PyAudio (voice)",
        "speech_recognition": "SpeechRecognition",
        "pyttsx3": "TTS Engine",
        "requests": "HTTP Requests",
        "cryptography": "Encryption",
        "fastapi": "Web API",
    }

    for module, name in optional.items():
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ⚠ {name} (optional)")

    return True


async def test_components():
    """Test component initialization"""
    print("\n[5/5] Testing components...")

    try:
        from src.core.system import SystemConfig

        config = SystemConfig()
        print(f"  ✓ SystemConfig: {config.name} v{config.version}")

        return True
    except Exception as e:
        print(f"  ✗ Component test failed: {e}")
        return False


def main():
    print("=" * 60)
    print("  ALPHA OMEGA SYSTEM TEST")
    print("  Version: 2.0.0")
    print("=" * 60)

    results = []

    results.append(test_imports())
    results.append(test_directories())
    results.append(test_config())
    results.append(test_dependencies())
    results.append(asyncio.run(test_components()))

    passed = sum(results)
    total = len(results)

    print("\n" + "=" * 60)
    print(f"  RESULTS: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("\n  ✓ All tests passed! System ready.")
        print("\n  To start:")
        print("    python run_alpha.py")
        print("    OR")
        print("    start_alpha.bat")
        print("\n  API: http://localhost:8000")
        print("  WebSocket: ws://localhost:8000/ws")
    else:
        print("\n  ⚠ Some tests failed. Check errors above.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
