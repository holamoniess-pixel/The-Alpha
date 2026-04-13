"""
ALPHA OMEGA - Power Manager
Power State Management & Wake-on-Voice Support
Version: 2.0.0
"""

import os
import sys
import ctypes
import logging
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum
import threading
import json

logger = logging.getLogger("PowerManager")


class PowerState(Enum):
    ACTIVE = "active"
    IDLE = "idle"
    SLEEP = "sleep"
    HIBERNATE = "hibernate"
    SHUTDOWN = "shutdown"
    UNKNOWN = "unknown"


class PowerProfile(Enum):
    BALANCED = "balanced"
    PERFORMANCE = "performance"
    POWER_SAVER = "power_saver"
    HIGH_PERFORMANCE = "high_performance"


@dataclass
class BatteryInfo:
    percent: int
    power_plugged: bool
    time_remaining: Optional[int] = None
    charging: bool = False
    discharging: bool = False

    def to_dict(self) -> dict:
        return {
            "percent": self.percent,
            "power_plugged": self.power_plugged,
            "time_remaining": self.time_remaining,
            "charging": self.charging,
            "discharging": self.discharging,
        }


@dataclass
class PowerStateInfo:
    state: PowerState
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    battery: Optional[BatteryInfo] = None
    uptime_seconds: float = 0
    last_input_seconds: float = 0

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_percent": self.disk_percent,
            "battery": self.battery.to_dict() if self.battery else None,
            "uptime_seconds": self.uptime_seconds,
            "last_input_seconds": self.last_input_seconds,
        }


class PowerManager:
    _is_windows = os.name == "nt"

    def __init__(self, config: dict = None):
        self.config = config or {}
        self._sleep_preventions: Dict[str, str] = {}
        self._scheduled_wakes: Dict[str, float] = {}
        self._last_power_state = PowerState.ACTIVE
        self._lock = threading.Lock()
        self._state_callbacks = []

        if self._is_windows:
            self._init_windows_api()

    def _init_windows_api(self):
        try:
            self._kernel32 = ctypes.windll.kernel32
            self._powrprof = ctypes.windll.powrprof
            self._user32 = ctypes.windll.user32
        except Exception as e:
            logger.warning(f"Failed to initialize Windows API: {e}")

    def get_power_state(self) -> PowerStateInfo:
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            battery = None
            if hasattr(psutil, "sensors_battery"):
                bat = psutil.sensors_battery()
                if bat:
                    battery = BatteryInfo(
                        percent=bat.percent,
                        power_plugged=bat.power_plugged
                        if hasattr(bat, "power_plugged")
                        else False,
                        time_remaining=bat.secsleft
                        if hasattr(bat, "secsleft") and bat.secsleft > 0
                        else None,
                        charging=bat.power_plugged
                        if hasattr(bat, "power_plugged")
                        else False,
                        discharging=not bat.power_plugged
                        if hasattr(bat, "power_plugged")
                        else True,
                    )

            uptime_seconds = time.time() - psutil.boot_time()
            last_input_seconds = self._get_idle_time()

            if last_input_seconds > 300:
                state = PowerState.IDLE
            else:
                state = PowerState.ACTIVE

            return PowerStateInfo(
                state=state,
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                battery=battery,
                uptime_seconds=uptime_seconds,
                last_input_seconds=last_input_seconds,
            )

        except Exception as e:
            logger.error(f"Failed to get power state: {e}")
            return PowerStateInfo(
                state=PowerState.UNKNOWN,
                cpu_percent=0,
                memory_percent=0,
                disk_percent=0,
            )

    def _get_idle_time(self) -> float:
        if not self._is_windows:
            return 0

        try:

            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

            lastInputInfo = LASTINPUTINFO()
            lastInputInfo.cbSize = ctypes.sizeof(LASTINPUTINFO)
            self._user32.GetLastInputInfo(ctypes.byref(lastInputInfo))

            millis = self._kernel32.GetTickCount() - lastInputInfo.dwTime
            return millis / 1000.0
        except Exception:
            return 0

    def prevent_sleep(self, reason: str) -> str:
        with self._lock:
            if reason in self._sleep_preventions:
                return self._sleep_preventions[reason]

            if self._is_windows:
                try:
                    ES_CONTINUOUS = 0x80000000
                    ES_SYSTEM_REQUIRED = 0x00000001
                    ES_DISPLAY_REQUIRED = 0x00000002

                    flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED
                    if self.config.get("keep_display_on", False):
                        flags |= ES_DISPLAY_REQUIRED

                    self._kernel32.SetThreadExecutionState(flags)
                    self._sleep_preventions[reason] = reason
                    logger.info(f"Preventing sleep: {reason}")
                    return reason
                except Exception as e:
                    logger.error(f"Failed to prevent sleep: {e}")
                    return None

            return reason

    def allow_sleep(self, reason: str = None) -> bool:
        with self._lock:
            if reason:
                if reason in self._sleep_preventions:
                    del self._sleep_preventions[reason]
            else:
                self._sleep_preventions.clear()

            if not self._sleep_preventions:
                if self._is_windows:
                    try:
                        ES_CONTINUOUS = 0x80000000
                        self._kernel32.SetThreadExecutionState(ES_CONTINUOUS)
                        logger.info("Allowed sleep")
                    except Exception as e:
                        logger.error(f"Failed to allow sleep: {e}")

            return True

    def enter_sleep(self) -> bool:
        if self._is_windows:
            try:
                self.allow_sleep()
                self._powrprof.SetSuspendState(0, 1, 0)
                logger.info("Entered sleep state")
                return True
            except Exception as e:
                logger.error(f"Failed to enter sleep: {e}")
                return False
        return False

    def enter_hibernate(self) -> bool:
        if self._is_windows:
            try:
                self.allow_sleep()
                self._powrprof.SetSuspendState(1, 1, 0)
                logger.info("Entered hibernate state")
                return True
            except Exception as e:
                logger.error(f"Failed to hibernate: {e}")
                return False
        return False

    def schedule_wake(self, wake_time: float, label: str = None) -> str:
        task_id = label or f"wake_{int(time.time())}"

        if self._is_windows:
            try:
                task_name = f"AlphaOmega_Wake_{task_id}"
                wake_dt = time.strftime("%H:%M:%S", time.localtime(wake_time))
                wake_date = time.strftime("%m/%d/%Y", time.localtime(wake_time))

                cmd = [
                    "schtasks",
                    "/create",
                    "/tn",
                    task_name,
                    "/tr",
                    f'"{sys.executable}" -c "import os; os.system(\'echo wake\')"',
                    "/sc",
                    "once",
                    "/st",
                    wake_dt,
                    "/sd",
                    wake_date,
                    "/rl",
                    "HIGHEST",
                    "/f",
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    self._scheduled_wakes[task_id] = wake_time
                    logger.info(f"Scheduled wake at {wake_dt}")
                    return task_id
                else:
                    logger.error(f"Failed to schedule wake: {result.stderr}")
                    return None

            except Exception as e:
                logger.error(f"Failed to schedule wake: {e}")
                return None

        return None

    def cancel_wake(self, task_id: str) -> bool:
        if task_id in self._scheduled_wakes:
            del self._scheduled_wakes[task_id]

        if self._is_windows:
            try:
                task_name = f"AlphaOmega_Wake_{task_id}"
                subprocess.run(
                    ["schtasks", "/delete", "/tn", task_name, "/f"], capture_output=True
                )
                logger.info(f"Cancelled wake: {task_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to cancel wake: {e}")
                return False

        return False

    def get_battery_status(self) -> BatteryInfo:
        state = self.get_power_state()
        return state.battery or BatteryInfo(percent=0, power_plugged=True)

    def set_power_profile(self, profile: PowerProfile) -> bool:
        if not self._is_windows:
            logger.warning("Power profiles only available on Windows")
            return False

        try:
            profile_map = {
                PowerProfile.BALANCED: "381b4222-f694-41f0-9685-ff5bb260df2e",
                PowerProfile.PERFORMANCE: "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
                PowerProfile.POWER_SAVER: "a1841308-3541-4fab-bc81-f71556f20b4a",
                PowerProfile.HIGH_PERFORMANCE: "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
            }

            guid = profile_map.get(profile)
            if guid:
                subprocess.run(
                    ["powercfg", "/setactive", guid], capture_output=True, check=True
                )
                logger.info(f"Set power profile: {profile.value}")
                return True

        except Exception as e:
            logger.error(f"Failed to set power profile: {e}")

        return False

    def get_power_profile(self) -> PowerProfile:
        if not self._is_windows:
            return PowerProfile.BALANCED

        try:
            result = subprocess.run(
                ["powercfg", "/getactivescheme"], capture_output=True, text=True
            )

            output = result.stdout.lower()
            if "balanced" in output:
                return PowerProfile.BALANCED
            elif "power saver" in output:
                return PowerProfile.POWER_SAVER
            elif "high performance" in output or "performance" in output:
                return PowerProfile.PERFORMANCE

        except Exception:
            pass

        return PowerProfile.BALANCED

    def register_state_callback(self, callback):
        self._state_callbacks.append(callback)

    def _notify_state_change(self, old_state: PowerState, new_state: PowerState):
        for callback in self._state_callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.error(f"State callback error: {e}")

    def monitor_power_events(self, interval: float = 60.0):
        def monitor_loop():
            while True:
                try:
                    state = self.get_power_state()

                    if state.state != self._last_power_state:
                        self._notify_state_change(self._last_power_state, state.state)
                        self._last_power_state = state.state

                except Exception as e:
                    logger.error(f"Power monitor error: {e}")

                time.sleep(interval)

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
        return thread

    def get_scheduled_wakes(self) -> Dict[str, float]:
        return self._scheduled_wakes.copy()

    def is_on_battery(self) -> bool:
        battery = self.get_battery_status()
        return battery and not battery.power_plugged

    def get_status(self) -> dict:
        state = self.get_power_state()
        return {
            "power_state": state.to_dict(),
            "power_profile": self.get_power_profile().value,
            "sleep_prevented": len(self._sleep_preventions) > 0,
            "prevention_reasons": list(self._sleep_preventions.keys()),
            "scheduled_wakes": self.get_scheduled_wakes(),
            "on_battery": self.is_on_battery(),
        }
