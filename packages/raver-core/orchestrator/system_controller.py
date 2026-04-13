"""
System Controller - Handles system-level operations with safety bounds.
"""

import asyncio
import psutil
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from ...raver_shared.schemas import ActionType, LinkInspectionResult


logger = logging.getLogger(__name__)


class SystemController:
    """Controls system operations with safety constraints."""
    
    def __init__(self):
        self.allowed_processes = ["notepad.exe", "calc.exe", "explorer.exe"]
        self.allowed_directories = [
            "C:\\Users\\Public\\Documents",
            "C:\\Temp\\RAVER"
        ]
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize the system controller."""
        # Create RAVER temp directory
        import os
        os.makedirs("C:\\Temp\\RAVER", exist_ok=True)
        
        self.is_initialized = True
        logger.info("System Controller initialized")
    
    async def cleanup(self):
        """Cleanup system controller resources."""
        self.is_initialized = False
        logger.info("System Controller cleaned up")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get system controller status."""
        return {
            "initialized": self.is_initialized,
            "allowed_processes": self.allowed_processes,
            "allowed_directories": self.allowed_directories,
            "system_info": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('C:\\').percent
            }
        }
    
    async def terminate_process(self, process_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Safely terminate a process."""
        try:
            # Check if process is allowed to be terminated
            if process_name not in self.allowed_processes:
                return {
                    "success": False,
                    "error": f"Process {process_name} is not in allowed list"
                }
            
            # Find the process
            process_found = False
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() == process_name.lower():
                        proc.terminate()
                        proc.wait(timeout=5)
                        process_found = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if process_found:
                return {
                    "success": True,
                    "message": f"Process {process_name} terminated successfully"
                }
            else:
                return {
                    "success": False,
                    "error": f"Process {process_name} not found"
                }
                
        except Exception as e:
            logger.error(f"Error terminating process: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def modify_file(self, file_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Safely modify a file."""
        try:
            import os
            
            # Check if file path is allowed
            file_allowed = False
            for allowed_dir in self.allowed_directories:
                if file_path.startswith(allowed_dir):
                    file_allowed = True
                    break
            
            if not file_allowed:
                return {
                    "success": False,
                    "error": f"File path {file_path} is not in allowed directories"
                }
            
            # Check operation type
            operation = parameters.get("operation", "write")
            
            if operation == "write":
                content = parameters.get("content", "")
                with open(file_path, 'w') as f:
                    f.write(content)
                
                return {
                    "success": True,
                    "message": f"File {file_path} written successfully"
                }
            
            elif operation == "append":
                content = parameters.get("content", "")
                with open(file_path, 'a') as f:
                    f.write(content)
                
                return {
                    "success": True,
                    "message": f"Content appended to {file_path}"
                }
            
            elif operation == "delete":
                if os.path.exists(file_path):
                    os.remove(file_path)
                    return {
                        "success": True,
                        "message": f"File {file_path} deleted successfully"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"File {file_path} does not exist"
                    }
            
            else:
                return {
                    "success": False,
                    "error": f"Unsupported operation: {operation}"
                }
                
        except Exception as e:
            logger.error(f"Error modifying file: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def access_vault(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Access vault operations."""
        try:
            # This would integrate with the vault system
            # For now, return a placeholder response
            return {
                "success": True,
                "message": f"Vault operation {operation} completed",
                "operation": operation,
                "parameters": parameters
            }
            
        except Exception as e:
            logger.error(f"Error accessing vault: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_ui_automation(self, target: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute UI automation with safety bounds."""
        try:
            # This would integrate with the HAL (Hardware Abstraction Layer)
            # For now, return a placeholder response
            
            action = parameters.get("action", "click")
            x = parameters.get("x", 0)
            y = parameters.get("y", 0)
            
            # Validate coordinates
            if x < 0 or y < 0 or x > 1920 or y > 1080:  # Basic screen bounds
                return {
                    "success": False,
                    "error": "Coordinates out of screen bounds"
                }
            
            return {
                "success": True,
                "message": f"UI automation {action} at ({x}, {y}) completed",
                "action": action,
                "coordinates": {"x": x, "y": y}
            }
            
        except Exception as e:
            logger.error(f"Error executing UI automation: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def inspect_link(self, url: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a link for safety."""
        try:
            # This would integrate with the link sandbox worker
            # For now, perform basic URL validation
            
            if not url.startswith(('http://', 'https://')):
                return {
                    "success": False,
                    "error": "Invalid URL format"
                }
            
            # Basic safety checks
            suspicious_indicators = []
            confidence_score = 0.8  # Default confidence
            
            # Check for suspicious patterns
            if any(suspicious in url.lower() for suspicious in ['phish', 'malware', 'virus']):
                suspicious_indicators.append("Suspicious keywords in URL")
                confidence_score -= 0.3
            
            if url.count('.') > 3:
                suspicious_indicators.append("Excessive subdomains")
                confidence_score -= 0.2
            
            # Create inspection result
            result = LinkInspectionResult(
                url=url,
                safe=confidence_score > 0.5,
                confidence_score=confidence_score,
                redirects=[],  # Would be populated by sandbox worker
                suspicious_patterns=suspicious_indicators,
                has_forms=False,  # Would be detected by sandbox worker
                has_password_fields=False,  # Would be detected by sandbox worker
                recommendation="Safe to proceed" if confidence_score > 0.7 else "Proceed with caution"
            )
            
            return {
                "success": True,
                "inspection_result": result.dict()
            }
            
        except Exception as e:
            logger.error(f"Error inspecting link: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class SystemPauseManager:
    """Manages system pause/resume functionality."""
    
    def __init__(self):
        self.is_paused = False
        self.pause_time: Optional[datetime] = None
        self.paused_operations: List[str] = []
        self.pause_user_id: Optional[str] = None
    
    async def pause_system(self, pause_request) -> Dict[str, Any]:
        """Pause all system operations."""
        try:
            self.is_paused = True
            self.pause_time = datetime.now()
            self.pause_user_id = pause_request.user_id
            
            # Define operations that should be paused
            self.paused_operations = [
                "ui_automation",
                "file_modification",
                "process_termination",
                "network_changes",
                "vault_access"
            ]
            
            return {
                "success": True,
                "paused_operations": self.paused_operations,
                "message": f"System paused by user {pause_request.user_id}",
                "pause_time": self.pause_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error pausing system: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def resume_system(self, user_id: str) -> Dict[str, Any]:
        """Resume system operations."""
        try:
            if not self.is_paused:
                return {
                    "success": False,
                    "error": "System is not currently paused"
                }
            
            self.is_paused = False
            pause_duration = datetime.now() - self.pause_time if self.pause_time else None
            
            result = {
                "success": True,
                "message": f"System resumed by user {user_id}",
                "paused_duration": pause_duration.total_seconds() if pause_duration else None,
                "resumed_operations": self.paused_operations.copy()
            }
            
            # Reset pause state
            self.paused_operations = []
            self.pause_time = None
            self.pause_user_id = None
            
            return result
            
        except Exception as e:
            logger.error(f"Error resuming system: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_pause_status(self) -> Dict[str, Any]:
        """Get current pause status."""
        return {
            "is_paused": self.is_paused,
            "pause_time": self.pause_time.isoformat() if self.pause_time else None,
            "paused_operations": self.paused_operations.copy(),
            "pause_user_id": self.pause_user_id
        }
