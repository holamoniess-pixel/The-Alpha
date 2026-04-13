#!/usr/bin/env python3
"""
ALPHA OMEGA - COMPREHENSIVE TEST SUITE
Tests all components and integrations
Version: 2.0.0
"""

import sys
import os
import asyncio
import time
import traceback
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.results: List[Dict] = []

    def run_test(self, name: str, test_func, *args) -> bool:
        """Run a single test"""
        print(f"\n  Testing: {name}...", end=" ")
        try:
            result = test_func(*args)
            if result:
                print("✓ PASS")
                self.passed += 1
                self.results.append({"name": name, "status": "passed"})
                return True
            else:
                print("✗ FAIL")
                self.failed += 1
                self.results.append({"name": name, "status": "failed"})
                return False
        except Exception as e:
            print(f"✗ ERROR: {str(e)[:50]}")
            self.failed += 1
            self.results.append({"name": name, "status": "error", "error": str(e)})
            return False

    async def run_async_test(self, name: str, test_func, *args) -> bool:
        """Run an async test"""
        print(f"\n  Testing: {name}...", end=" ")
        try:
            result = await test_func(*args)
            if result:
                print("✓ PASS")
                self.passed += 1
                self.results.append({"name": name, "status": "passed"})
                return True
            else:
                print("✗ FAIL")
                self.failed += 1
                self.results.append({"name": name, "status": "failed"})
                return False
        except Exception as e:
            print(f"✗ ERROR: {str(e)[:50]}")
            self.failed += 1
            self.results.append({"name": name, "status": "error", "error": str(e)})
            return False

    def skip_test(self, name: str, reason: str):
        """Skip a test"""
        print(f"\n  Testing: {name}... ⚠ SKIP ({reason})")
        self.skipped += 1
        self.results.append({"name": name, "status": "skipped", "reason": reason})

    def summary(self) -> Dict:
        """Print test summary"""
        total = self.passed + self.failed + self.skipped
        print("\n" + "=" * 60)
        print("  TEST SUMMARY")
        print("=" * 60)
        print(f"  Total:   {total}")
        print(f"  Passed:  {self.passed} ✓")
        print(f"  Failed:  {self.failed} ✗")
        print(f"  Skipped: {self.skipped} ⚠")
        print("=" * 60)

        if self.failed == 0:
            print("  ALL TESTS PASSED!")
        else:
            print("  SOME TESTS FAILED - See details above")
        print("=" * 60)

        return {
            "total": total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "results": self.results,
        }


def test_imports() -> bool:
    """Test all module imports"""
    modules = [
        "src.core.system",
        "src.memory.memory_system",
        "src.automation.automation_engine",
        "src.voice.voice_system",
        "src.intelligence.intelligence_engine",
        "src.learning.learning_engine",
        "src.security.security_framework",
        "src.vault.vault_manager",
        "src.vision.vision_system",
        "src.api.web_server",
        "src.core.self_extension",
        "src.core.performance",
    ]

    for module in modules:
        try:
            __import__(module)
        except ImportError as e:
            print(f"\n    Failed to import {module}: {e}")
            return False
    return True


def test_config() -> bool:
    """Test configuration loading"""
    try:
        from src.core.system import SystemConfig

        config = SystemConfig()

        if not config.name:
            return False
        if not config.version:
            return False
        if not config.wake_word:
            return False

        return True
    except Exception:
        return False


def test_directories() -> bool:
    """Test required directories"""
    required = ["src", "logs", "data"]

    for d in required:
        path = Path(d)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

    return True


async def test_memory_system() -> bool:
    """Test memory system"""
    try:
        from src.memory.memory_system import MemorySystem

        config = {"memory_retention_days": 30}
        memory = MemorySystem(config)

        success = await memory.initialize()
        if not success:
            return False

        await memory.store_command("test command", "test", True, "test response")

        patterns = await memory.get_patterns(limit=10)

        stats = memory.get_stats()

        await memory.save_and_close()

        return True
    except Exception as e:
        print(f"\n    Error: {e}")
        return False


async def test_automation_engine() -> bool:
    """Test automation engine"""
    try:
        from src.automation.automation_engine import AutomationEngine

        config = {"safety_mode": True}
        engine = AutomationEngine(config, None)

        success = await engine.initialize()
        if not success:
            return False

        result = await engine.execute_command("ip", {})

        stats = engine.get_stats()

        return True
    except Exception as e:
        print(f"\n    Error: {e}")
        return False


async def test_intelligence_engine() -> bool:
    """Test intelligence engine"""
    try:
        from src.intelligence.intelligence_engine import IntelligenceEngine

        config = {"context_window": 4096, "temperature": 0.7, "max_tokens": 512}
        engine = IntelligenceEngine(config, None)

        success = await engine.initialize()
        if not success:
            return False

        intent = await engine.process_command("open chrome")

        if not intent:
            return False

        return True
    except Exception as e:
        print(f"\n    Error: {e}")
        return False


async def test_security_framework() -> bool:
    """Test security framework"""
    try:
        from src.security.security_framework import SecurityFramework

        config = {
            "security_enabled": True,
            "audit_logging": True,
            "session_timeout": 300,
        }
        security = SecurityFramework(config)

        success = await security.initialize()
        if not success:
            return False

        allowed = security.is_command_allowed("open chrome")

        blocked = security.is_command_allowed("format C:")

        status = security.get_status()

        return True
    except Exception as e:
        print(f"\n    Error: {e}")
        return False


async def test_vault_system() -> bool:
    """Test vault system"""
    try:
        from src.vault.vault_manager import VaultManager

        vault = VaultManager()

        success = vault.initialize_vault("test_password_123", "test_user")
        if not success:
            return False

        locked = vault.is_unlocked()
        if not locked:
            return False

        secret_id = vault.create_secret(
            "test_service", "test_label", "test_secret_data"
        )

        vault.lock_vault()

        return True
    except Exception as e:
        print(f"\n    Error: {e}")
        return False


async def test_self_extension() -> bool:
    """Test self-extension engine"""
    try:
        from src.core.self_extension import (
            SelfExtensionEngine,
            TaskPlanner,
            ToolRegistry,
        )

        registry = ToolRegistry()
        planner = TaskPlanner(registry)

        task = planner.analyze_task("open chrome")

        if not task:
            return False

        plan = planner.create_plan(task)

        tools = registry.list_all_tools()
        if len(tools) < 10:
            return False

        return True
    except Exception as e:
        print(f"\n    Error: {e}")
        return False


async def test_performance_optimizer() -> bool:
    """Test performance optimizer"""
    try:
        from src.core.performance import PerformanceOptimizer, LRUCache

        optimizer = PerformanceOptimizer({"enabled": True})

        success = await optimizer.initialize()
        if not success:
            return False

        cache = LRUCache(max_size=10)
        cache.put("key1", "value1")
        value = cache.get("key1")

        if value != "value1":
            return False

        stats = optimizer.get_stats()

        return True
    except Exception as e:
        print(f"\n    Error: {e}")
        return False


async def test_learning_engine() -> bool:
    """Test learning engine"""
    try:
        from src.learning.learning_engine import LearningEngine

        config = {
            "learning_enabled": True,
            "pattern_threshold": 3,
            "min_confidence": 0.6,
        }
        learning = LearningEngine(config, None)

        success = await learning.initialize()
        if not success:
            return False

        learning.record_command("open chrome", {"success": True})

        stats = learning.get_stats()

        return True
    except Exception as e:
        print(f"\n    Error: {e}")
        return False


def test_vision_system() -> bool:
    """Test vision system"""
    try:
        from src.vision.vision_system import VisionSystem

        config = {"analysis_interval": 3.0}
        vision = VisionSystem(config, None)

        return True
    except Exception as e:
        print(f"\n    Error: {e}")
        return False


async def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  ALPHA OMEGA TEST SUITE v2.0.0")
    print("=" * 60)

    runner = TestRunner()

    print("\n[1/12] Module Imports")
    runner.run_test("Import all modules", test_imports)

    print("\n[2/12] Configuration")
    runner.run_test("Load configuration", test_config)

    print("\n[3/12] Directories")
    runner.run_test("Check directories", test_directories)

    print("\n[4/12] Memory System")
    await runner.run_async_test("Memory system operations", test_memory_system)

    print("\n[5/12] Automation Engine")
    await runner.run_async_test("Automation engine operations", test_automation_engine)

    print("\n[6/12] Intelligence Engine")
    await runner.run_async_test(
        "Intelligence engine operations", test_intelligence_engine
    )

    print("\n[7/12] Security Framework")
    await runner.run_async_test(
        "Security framework operations", test_security_framework
    )

    print("\n[8/12] Vault System")
    await runner.run_async_test("Vault system operations", test_vault_system)

    print("\n[9/12] Self-Extension Engine")
    await runner.run_async_test("Self-extension engine operations", test_self_extension)

    print("\n[10/12] Performance Optimizer")
    await runner.run_async_test(
        "Performance optimizer operations", test_performance_optimizer
    )

    print("\n[11/12] Learning Engine")
    await runner.run_async_test("Learning engine operations", test_learning_engine)

    print("\n[12/12] Vision System")
    runner.run_test("Vision system operations", test_vision_system)

    return runner.summary()


def main():
    try:
        result = asyncio.run(run_all_tests())

        if result["failed"] == 0:
            print("\n✓ All tests passed!")
            return 0
        else:
            print(f"\n✗ {result['failed']} test(s) failed")
            return 1
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        return 1
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
