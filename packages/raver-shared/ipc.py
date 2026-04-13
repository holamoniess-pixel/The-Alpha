"""
IPC (Inter-Process Communication) contracts and utilities for RAVER.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from .schemas import WebSocketMessage


logger = logging.getLogger(__name__)


class IPCMessage:
    """IPC message wrapper."""
    
    def __init__(self, message_type: str, data: Dict[str, Any], 
                 source: str, destination: str, message_id: Optional[str] = None):
        self.message_id = message_id or f"{source}-{datetime.now().timestamp()}"
        self.message_type = message_type
        self.data = data
        self.source = source
        self.destination = destination
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type,
            "data": self.data,
            "source": self.source,
            "destination": self.destination,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IPCMessage":
        """Create message from dictionary."""
        msg = cls(
            message_type=data["message_type"],
            data=data["data"],
            source=data["source"],
            destination=data["destination"],
            message_id=data["message_id"]
        )
        msg.timestamp = datetime.fromisoformat(data["timestamp"])
        return msg


class IPCBroker:
    """Simple in-memory IPC broker for local communication."""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.message_history: list[IPCMessage] = []
        self.max_history = 1000
    
    def subscribe(self, destination: str, callback: Callable[[IPCMessage], None]):
        """Subscribe to messages for a destination."""
        if destination not in self.subscribers:
            self.subscribers[destination] = []
        self.subscribers[destination].append(callback)
        logger.info(f"Subscribed {destination} to IPC broker")
    
    def unsubscribe(self, destination: str, callback: Callable[[IPCMessage], None]):
        """Unsubscribe from messages."""
        if destination in self.subscribers:
            try:
                self.subscribers[destination].remove(callback)
                logger.info(f"Unsubscribed {destination} from IPC broker")
            except ValueError:
                pass
    
    async def publish(self, message: IPCMessage):
        """Publish a message to all subscribers."""
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
        
        if message.destination in self.subscribers:
            for callback in self.subscribers[message.destination]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(message)
                    else:
                        callback(message)
                except Exception as e:
                    logger.error(f"Error in IPC callback: {e}")
        
        logger.debug(f"Published IPC message: {message.message_type} from {message.source} to {message.destination}")
    
    def get_history(self, destination: Optional[str] = None, 
                   message_type: Optional[str] = None,
                   limit: int = 100) -> list[IPCMessage]:
        """Get message history with optional filters."""
        filtered = self.message_history
        
        if destination:
            filtered = [msg for msg in filtered if msg.destination == destination]
        
        if message_type:
            filtered = [msg for msg in filtered if msg.message_type == message_type]
        
        return filtered[-limit:]


# Global IPC broker instance
ipc_broker = IPCBroker()


class IPCClient:
    """Client for communicating with IPC broker."""
    
    def __init__(self, client_name: str):
        self.client_name = client_name
        self.broker = ipc_broker
    
    async def send_message(self, destination: str, message_type: str, 
                          data: Dict[str, Any]) -> IPCMessage:
        """Send a message through IPC."""
        message = IPCMessage(message_type, data, self.client_name, destination)
        await self.broker.publish(message)
        return message
    
    def subscribe_to_messages(self, message_types: list[str], 
                            callback: Callable[[IPCMessage], None]):
        """Subscribe to specific message types."""
        for message_type in message_types:
            self.broker.subscribe(f"{self.client_name}:{message_type}", callback)
    
    def unsubscribe_from_messages(self, message_types: list[str],
                                callback: Callable[[IPCMessage], None]):
        """Unsubscribe from message types."""
        for message_type in message_types:
            self.broker.unsubscribe(f"{self.client_name}:{message_type}", callback)
