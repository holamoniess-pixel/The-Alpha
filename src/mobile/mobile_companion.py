#!/usr/bin/env python3
"""
ALPHA OMEGA - CROSS-PLATFORM MOBILE COMPANION
iOS/Android app for remote control
Version: 2.0.0
"""

import asyncio
import json
import logging
import time
import hashlib
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DeviceType(Enum):
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"
    DESKTOP = "desktop"


class ConnectionStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    ERROR = "error"


class NotificationType(Enum):
    ALERT = "alert"
    COMMAND = "command"
    STATUS = "status"
    SYNC = "sync"
    LOCATION = "location"


@dataclass
class MobileDevice:
    id: str
    name: str
    device_type: DeviceType
    push_token: str = ""
    os_version: str = ""
    app_version: str = ""
    last_seen: float = field(default_factory=time.time)
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.device_type.value,
            "os_version": self.os_version,
            "app_version": self.app_version,
            "last_seen": self.last_seen,
            "status": self.status.value,
            "capabilities": self.capabilities,
        }


@dataclass
class MobileCommand:
    id: str
    device_id: str
    command_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    status: str = "pending"
    result: Any = None
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "command_type": self.command_type,
            "parameters": self.parameters,
            "timestamp": self.timestamp,
            "status": self.status,
        }


@dataclass
class MobileNotification:
    id: str
    device_id: str
    notification_type: NotificationType
    title: str
    body: str
    data: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5
    created_at: float = field(default_factory=time.time)
    sent_at: float = 0
    delivered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "type": self.notification_type.value,
            "title": self.title,
            "body": self.body,
            "priority": self.priority,
            "delivered": self.delivered,
        }


@dataclass
class LocationTrigger:
    id: str
    device_id: str
    name: str
    latitude: float
    longitude: float
    radius_meters: float
    trigger_on_enter: bool = True
    trigger_on_exit: bool = False
    actions: List[Dict[str, Any]] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "location": {
                "lat": self.latitude,
                "lng": self.longitude,
                "radius": self.radius_meters,
            },
            "trigger_on_enter": self.trigger_on_enter,
            "trigger_on_exit": self.trigger_on_exit,
            "enabled": self.enabled,
        }


class DeviceRegistry:
    """Manage connected mobile devices"""

    def __init__(self):
        self.logger = logging.getLogger("DeviceRegistry")

        self._devices: Dict[str, MobileDevice] = {}
        self._connection_handlers: List[Callable] = []

    def register_device(
        self,
        device_id: str,
        name: str,
        device_type: DeviceType,
        capabilities: List[str] = None,
    ) -> MobileDevice:
        """Register a new device"""
        device = MobileDevice(
            id=device_id,
            name=name,
            device_type=device_type,
            status=ConnectionStatus.CONNECTED,
            capabilities=capabilities or [],
        )

        self._devices[device_id] = device

        self.logger.info(f"Device registered: {name} ({device_type.value})")

        for handler in self._connection_handlers:
            try:
                handler(device, "connected")
            except Exception as e:
                self.logger.error(f"Connection handler error: {e}")

        return device

    def unregister_device(self, device_id: str) -> bool:
        """Unregister a device"""
        device = self._devices.get(device_id)
        if not device:
            return False

        device.status = ConnectionStatus.DISCONNECTED

        for handler in self._connection_handlers:
            try:
                handler(device, "disconnected")
            except Exception as e:
                self.logger.error(f"Connection handler error: {e}")

        del self._devices[device_id]

        self.logger.info(f"Device unregistered: {device_id}")
        return True

    def update_device_status(
        self,
        device_id: str,
        status: ConnectionStatus,
    ):
        """Update device connection status"""
        device = self._devices.get(device_id)
        if device:
            device.status = status
            device.last_seen = time.time()

    def get_device(self, device_id: str) -> Optional[MobileDevice]:
        """Get device by ID"""
        return self._devices.get(device_id)

    def get_all_devices(self) -> List[MobileDevice]:
        """Get all devices"""
        return list(self._devices.values())

    def get_connected_devices(self) -> List[MobileDevice]:
        """Get connected devices"""
        return [
            d for d in self._devices.values() if d.status == ConnectionStatus.CONNECTED
        ]

    def on_connection_change(self, handler: Callable):
        """Register connection change handler"""
        self._connection_handlers.append(handler)


class MobileCommandHandler:
    """Handle commands from mobile devices"""

    def __init__(self):
        self.logger = logging.getLogger("MobileCommandHandler")

        self._command_handlers: Dict[str, Callable] = {}
        self._pending_commands: Dict[str, MobileCommand] = {}

        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default command handlers"""
        self._command_handlers = {
            "voice_command": self._handle_voice_command,
            "status_request": self._handle_status_request,
            "execute_automation": self._handle_automation,
            "get_location": self._handle_get_location,
            "send_notification": self._handle_send_notification,
            "sync_data": self._handle_sync_data,
        }

    async def process_command(
        self,
        device_id: str,
        command_type: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process a command from a device"""
        command_id = hashlib.md5(f"{device_id}{time.time()}".encode()).hexdigest()[:8]

        command = MobileCommand(
            id=command_id,
            device_id=device_id,
            command_type=command_type,
            parameters=parameters,
        )

        self._pending_commands[command_id] = command

        handler = self._command_handlers.get(command_type)

        if handler:
            try:
                result = await handler(device_id, parameters)
                command.status = "completed"
                command.result = result
                return {"success": True, "result": result}
            except Exception as e:
                command.status = "failed"
                command.error = str(e)
                return {"success": False, "error": str(e)}
        else:
            command.status = "unknown"
            return {"success": False, "error": "Unknown command"}

    async def _handle_voice_command(
        self,
        device_id: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle voice command from mobile"""
        command_text = params.get("text", "")

        return {
            "command": command_text,
            "status": "received",
            "message": f"Voice command received: {command_text}",
        }

    async def _handle_status_request(
        self,
        device_id: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle status request"""
        return {
            "status": "online",
            "version": "2.0.0",
            "timestamp": time.time(),
        }

    async def _handle_automation(
        self,
        device_id: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle automation trigger"""
        automation_id = params.get("automation_id")

        return {
            "triggered": True,
            "automation_id": automation_id,
        }

    async def _handle_get_location(
        self,
        device_id: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle location request"""
        return {
            "location": params.get("location", {}),
            "timestamp": time.time(),
        }

    async def _handle_send_notification(
        self,
        device_id: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle notification request"""
        return {
            "sent": True,
            "notification_id": hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
        }

    async def _handle_sync_data(
        self,
        device_id: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle data sync"""
        return {
            "synced": True,
            "timestamp": time.time(),
        }

    def register_handler(self, command_type: str, handler: Callable):
        """Register custom command handler"""
        self._command_handlers[command_type] = handler

    def get_pending_commands(self, device_id: str = None) -> List[MobileCommand]:
        """Get pending commands"""
        commands = list(self._pending_commands.values())

        if device_id:
            commands = [c for c in commands if c.device_id == device_id]

        return commands


class NotificationSender:
    """Send push notifications to mobile devices"""

    def __init__(self):
        self.logger = logging.getLogger("NotificationSender")

        self._notifications: List[MobileNotification] = []
        self._max_history = 100

    async def send_notification(
        self,
        device_id: str,
        title: str,
        body: str,
        data: Dict[str, Any] = None,
        priority: int = 5,
    ) -> MobileNotification:
        """Send push notification to device"""
        notification_id = hashlib.md5(f"{device_id}{time.time()}".encode()).hexdigest()[
            :8
        ]

        notification = MobileNotification(
            id=notification_id,
            device_id=device_id,
            notification_type=NotificationType.ALERT,
            title=title,
            body=body,
            data=data or {},
            priority=priority,
        )

        self._notifications.append(notification)

        if len(self._notifications) > self._max_history:
            self._notifications.pop(0)

        notification.sent_at = time.time()
        notification.delivered = True

        self.logger.info(f"Notification sent to {device_id}: {title}")

        return notification

    async def send_command_notification(
        self,
        device_id: str,
        command: str,
        parameters: Dict[str, Any] = None,
    ) -> MobileNotification:
        """Send command notification to device"""
        return await self.send_notification(
            device_id=device_id,
            title=f"Command: {command}",
            body="New command from Alpha Omega",
            data={"command": command, "parameters": parameters or {}},
        )

    async def broadcast_notification(
        self,
        device_ids: List[str],
        title: str,
        body: str,
        data: Dict[str, Any] = None,
    ) -> List[MobileNotification]:
        """Broadcast notification to multiple devices"""
        notifications = []

        for device_id in device_ids:
            notification = await self.send_notification(
                device_id=device_id,
                title=title,
                body=body,
                data=data,
            )
            notifications.append(notification)

        return notifications

    def get_notification_history(
        self,
        device_id: str = None,
        limit: int = 20,
    ) -> List[MobileNotification]:
        """Get notification history"""
        notifications = self._notifications

        if device_id:
            notifications = [n for n in notifications if n.device_id == device_id]

        return notifications[-limit:]


class LocationManager:
    """Manage location-based triggers"""

    def __init__(self):
        self.logger = logging.getLogger("LocationManager")

        self._triggers: Dict[str, LocationTrigger] = {}
        self._location_handlers: List[Callable] = []

    def create_location_trigger(
        self,
        device_id: str,
        name: str,
        latitude: float,
        longitude: float,
        radius_meters: float,
        trigger_on_enter: bool = True,
        trigger_on_exit: bool = False,
    ) -> LocationTrigger:
        """Create a location-based trigger"""
        trigger_id = hashlib.md5(
            f"{device_id}{name}{time.time()}".encode()
        ).hexdigest()[:8]

        trigger = LocationTrigger(
            id=trigger_id,
            device_id=device_id,
            name=name,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
            trigger_on_enter=trigger_on_enter,
            trigger_on_exit=trigger_on_exit,
        )

        self._triggers[trigger_id] = trigger

        self.logger.info(f"Created location trigger: {name}")
        return trigger

    def check_location(
        self,
        device_id: str,
        latitude: float,
        longitude: float,
    ) -> List[LocationTrigger]:
        """Check if location triggers any actions"""
        triggered = []

        for trigger in self._triggers.values():
            if not trigger.enabled:
                continue

            if trigger.device_id != device_id:
                continue

            distance = self._haversine_distance(
                latitude,
                longitude,
                trigger.latitude,
                trigger.longitude,
            )

            if distance <= trigger.radius_meters:
                triggered.append(trigger)

        return triggered

    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """Calculate distance between two points in meters"""
        import math

        R = 6371000

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def get_triggers(self, device_id: str = None) -> List[LocationTrigger]:
        """Get location triggers"""
        triggers = list(self._triggers.values())

        if device_id:
            triggers = [t for t in triggers if t.device_id == device_id]

        return triggers

    def delete_trigger(self, trigger_id: str) -> bool:
        """Delete a location trigger"""
        if trigger_id in self._triggers:
            del self._triggers[trigger_id]
            return True
        return False


class MobileCompanion:
    """Main mobile companion system"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("MobileCompanion")

        self.device_registry = DeviceRegistry()
        self.command_handler = MobileCommandHandler()
        self.notification_sender = NotificationSender()
        self.location_manager = LocationManager()

    async def initialize(self) -> bool:
        """Initialize mobile companion system"""
        self.logger.info("Mobile Companion System initialized")
        return True

    def register_device(
        self,
        device_id: str,
        name: str,
        device_type: str,
        capabilities: List[str] = None,
    ) -> MobileDevice:
        """Register a new device"""
        return self.device_registry.register_device(
            device_id=device_id,
            name=name,
            device_type=DeviceType(device_type),
            capabilities=capabilities,
        )

    def unregister_device(self, device_id: str) -> bool:
        """Unregister a device"""
        return self.device_registry.unregister_device(device_id)

    async def process_command(
        self,
        device_id: str,
        command_type: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process command from device"""
        return await self.command_handler.process_command(
            device_id=device_id,
            command_type=command_type,
            parameters=parameters,
        )

    async def send_notification(
        self,
        device_id: str,
        title: str,
        body: str,
        data: Dict[str, Any] = None,
    ) -> MobileNotification:
        """Send notification to device"""
        return await self.notification_sender.send_notification(
            device_id=device_id,
            title=title,
            body=body,
            data=data,
        )

    async def notify_all_devices(
        self,
        title: str,
        body: str,
        data: Dict[str, Any] = None,
    ) -> List[MobileNotification]:
        """Notify all connected devices"""
        devices = self.device_registry.get_connected_devices()
        device_ids = [d.id for d in devices]

        return await self.notification_sender.broadcast_notification(
            device_ids=device_ids,
            title=title,
            body=body,
            data=data,
        )

    def create_location_trigger(
        self,
        device_id: str,
        name: str,
        latitude: float,
        longitude: float,
        radius_meters: float,
    ) -> LocationTrigger:
        """Create location-based trigger"""
        return self.location_manager.create_location_trigger(
            device_id=device_id,
            name=name,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
        )

    async def update_device_location(
        self,
        device_id: str,
        latitude: float,
        longitude: float,
    ) -> List[LocationTrigger]:
        """Update device location and check triggers"""
        triggers = self.location_manager.check_location(
            device_id=device_id,
            latitude=latitude,
            longitude=longitude,
        )

        for trigger in triggers:
            for action in trigger.actions:
                await self.process_command(
                    device_id=device_id,
                    command_type=action.get("type", "status_request"),
                    parameters=action.get("parameters", {}),
                )

        return triggers

    def get_connected_devices(self) -> List[Dict[str, Any]]:
        """Get all connected devices"""
        return [d.to_dict() for d in self.device_registry.get_connected_devices()]

    def get_device_info(self, device_id: str) -> Dict[str, Any]:
        """Get device information"""
        device = self.device_registry.get_device(device_id)
        return device.to_dict() if device else {}

    def get_stats(self) -> Dict[str, Any]:
        """Get mobile companion statistics"""
        return {
            "registered_devices": len(self.device_registry._devices),
            "connected_devices": len(self.device_registry.get_connected_devices()),
            "pending_commands": len(self.command_handler._pending_commands),
            "location_triggers": len(self.location_manager._triggers),
        }
