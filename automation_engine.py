#!/usr/bin/env python3
"""
ALPHA OMEGA - AUTOMATION ENGINE
Advanced automation and control system
Version: 1.1.0 Production Ready
"""

import asyncio
import json
import logging
import pyautogui
import subprocess
import webbrowser
import time
import psutil
import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import win32gui
import win32con
import win32api
from PIL import Image
import pytesseract

class AutomationType(Enum):
    GUI = "gui"
    SYSTEM = "system"
    WEB = "web"
    FILE = "file"
    PROCESS = "process"

@dataclass
class AutomationTask:
    task_id: str
    task_type: AutomationType
    action: str
    parameters: Dict[str, Any]
    priority: int = 1
    timeout: int = 30
    confirmation_required: bool = False

@dataclass
class AutomationResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    execution_time: float = 0.0

class AutomationEngine:
    """
    Advanced automation and control system for Windows
    """
    
    def __init__(self, config: Dict[str, Any], intelligence_engine):
        self.config = config
        self.intelligence_engine = intelligence_engine
        self.logger = logging.getLogger('AutomationEngine')
        
        # Automation state
        self.is_active = False
        self.task_queue = []
        self.running_tasks = {}
        self.task_history = []
        
        # Safety settings
        self.safety_mode = config.get('safety_mode', True)
        self.confirmation_required = config.get('confirmation_required', False)
        self.max_concurrent_tasks = config.get('max_concurrent_tasks', 5)
        
        # Performance settings
        self.execution_timeout = 30
        self.retry_attempts = 3
        self.retry_delay = 1.0
        
        # Initialize automation components
        self.gui_automation = GUIAutomation(self.config)
        self.system_automation = SystemAutomation(self.config)
        self.web_automation = WebAutomation(self.config)
        self.file_automation = FileAutomation(self.config)
        self.process_automation = ProcessAutomation(self.config)
        
    async def initialize(self):
        """Initialize automation engine"""
        self.logger.info("Initializing Automation Engine...")
        
        try:
            # Initialize automation components
            await self.gui_automation.initialize()
            await self.system_automation.initialize()
            await self.web_automation.initialize()
            await self.file_automation.initialize()
            await self.process_automation.initialize()
            
            # Setup pyautogui safety
            pyautogui.FAILSAFE = self.safety_mode
            pyautogui.PAUSE = 0.1
            
            self.logger.info("Automation Engine initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Automation Engine initialization failed: {e}")
            raise
    
    async def execute(self, intent: Dict[str, Any]) -> AutomationResult:
        """Execute automation based on intent"""
        start_time = time.time()
        
        try:
            self.logger.info(f"Executing automation: {intent}")
            
            # Extract automation parameters
            automation_type = self._determine_automation_type(intent)
            action = intent.get('action', '')
            parameters = intent.get('parameters', {})
            
            # Safety check
            if self.safety_mode and not self._is_action_safe(action, parameters):
                return AutomationResult(
                    success=False,
                    message="Action blocked by safety settings",
                    execution_time=time.time() - start_time
                )
            
            # Execute based on automation type
            if automation_type == AutomationType.GUI:
                result = await self.gui_automation.execute(action, parameters)
            elif automation_type == AutomationType.SYSTEM:
                result = await self.system_automation.execute(action, parameters)
            elif automation_type == AutomationType.WEB:
                result = await self.web_automation.execute(action, parameters)
            elif automation_type == AutomationType.FILE:
                result = await self.file_automation.execute(action, parameters)
            elif automation_type == AutomationType.PROCESS:
                result = await self.process_automation.execute(action, parameters)
            else:
                result = AutomationResult(
                    success=False,
                    message=f"Unknown automation type: {automation_type}",
                    execution_time=time.time() - start_time
                )
            
            # Record in history
            self.task_history.append({
                'timestamp': time.time(),
                'intent': intent,
                'result': result,
                'execution_time': time.time() - start_time
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Automation execution error: {e}")
            return AutomationResult(
                success=False,
                message=f"Automation failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def _determine_automation_type(self, intent: Dict[str, Any]) -> AutomationType:
        """Determine automation type from intent"""
        command = intent.get('command', '').lower()
        
        # GUI automation keywords
        gui_keywords = ['click', 'type', 'move', 'scroll', 'drag', 'screenshot']
        if any(keyword in command for keyword in gui_keywords):
            return AutomationType.GUI
        
        # System automation keywords
        system_keywords = ['shutdown', 'restart', 'sleep', 'lock', 'volume', 'brightness']
        if any(keyword in command for keyword in system_keywords):
            return AutomationType.SYSTEM
        
        # Web automation keywords
        web_keywords = ['browser', 'website', 'url', 'search', 'navigate']
        if any(keyword in command for keyword in web_keywords):
            return AutomationType.WEB
        
        # File automation keywords
        file_keywords = ['file', 'folder', 'directory', 'create', 'delete', 'copy', 'move']
        if any(keyword in command for keyword in file_keywords):
            return AutomationType.FILE
        
        # Process automation keywords
        process_keywords = ['process', 'task', 'kill', 'start', 'stop', 'monitor']
        if any(keyword in command for keyword in process_keywords):
            return AutomationType.PROCESS
        
        # Default to GUI automation
        return AutomationType.GUI
    
    def _is_action_safe(self, action: str, parameters: Dict[str, Any]) -> bool:
        """Check if action is safe to execute"""
        # Dangerous actions blacklist
        dangerous_actions = [
            'format', 'delete system', 'delete windows', 'rm -rf',
            'shutdown -s -t 0', 'del /q /f', 'rd /s /q'
        ]
        
        action_lower = action.lower()
        for dangerous in dangerous_actions:
            if dangerous in action_lower:
                return False
        
        # Check parameters for dangerous content
        for key, value in parameters.items():
            if isinstance(value, str):
                for dangerous in dangerous_actions:
                    if dangerous in value.lower():
                        return False
        
        return True
    
    async def queue_task(self, task: AutomationTask) -> str:
        """Queue automation task for execution"""
        task_id = f"task_{int(time.time() * 1000)}"
        task.task_id = task_id
        
        self.task_queue.append(task)
        self.logger.info(f"Task queued: {task_id} - {task.action}")
        
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task execution status"""
        # Check running tasks
        if task_id in self.running_tasks:
            return self.running_tasks[task_id]
        
        # Check completed tasks
        for task_info in self.task_history:
            if task_info.get('task_id') == task_id:
                return task_info
        
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel running task"""
        if task_id in self.running_tasks:
            # Cancel task implementation
            del self.running_tasks[task_id]
            self.logger.info(f"Task cancelled: {task_id}")
            return True
        
        return False
    
    def get_available_actions(self) -> Dict[str, List[str]]:
        """Get list of available automation actions"""
        return {
            'gui': [
                'click', 'double_click', 'right_click', 'move_mouse',
                'scroll', 'drag', 'type_text', 'press_key', 'screenshot',
                'find_image', 'wait_for_image', 'get_mouse_position'
            ],
            'system': [
                'shutdown', 'restart', 'sleep', 'hibernate', 'lock',
                'volume_up', 'volume_down', 'mute', 'brightness_up',
                'brightness_down', 'open_settings', 'open_control_panel'
            ],
            'web': [
                'open_browser', 'navigate_to', 'search_google', 'search_bing',
                'open_url', 'refresh_page', 'go_back', 'go_forward',
                'open_new_tab', 'close_tab'
            ],
            'file': [
                'create_file', 'create_folder', 'delete_file', 'delete_folder',
                'copy_file', 'move_file', 'rename_file', 'list_files',
                'get_file_info', 'search_files'
            ],
            'process': [
                'start_process', 'kill_process', 'get_process_list',
                'get_process_info', 'monitor_process', 'find_process'
            ]
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get automation system status"""
        return {
            'active': self.is_active,
            'queued_tasks': len(self.task_queue),
            'running_tasks': len(self.running_tasks),
            'completed_tasks': len(self.task_history),
            'safety_mode': self.safety_mode,
            'max_concurrent_tasks': self.max_concurrent_tasks,
            'recent_actions': self.task_history[-10:] if self.task_history else []
        }


class GUIAutomation:
    """GUI automation and control"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('GUIAutomation')
        
    async def initialize(self):
        """Initialize GUI automation"""
        self.logger.info("GUI Automation initialized")
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> AutomationResult:
        """Execute GUI automation action"""
        start_time = time.time()
        
        try:
            self.logger.info(f"Executing GUI action: {action}")
            
            if action == 'click':
                x = parameters.get('x')
                y = parameters.get('y')
                if x is not None and y is not None:
                    pyautogui.click(x, y)
                    return AutomationResult(
                        success=True,
                        message=f"Clicked at ({x}, {y})",
                        execution_time=time.time() - start_time
                    )
                else:
                    return AutomationResult(
                        success=False,
                        message="Missing coordinates for click action",
                        execution_time=time.time() - start_time
                    )
            
            elif action == 'type_text':
                text = parameters.get('text', '')
                interval = parameters.get('interval', 0.1)
                pyautogui.typewrite(text, interval=interval)
                return AutomationResult(
                    success=True,
                    message=f"Typed text: {text}",
                    execution_time=time.time() - start_time
                )
            
            elif action == 'screenshot':
                screenshot = pyautogui.screenshot()
                screenshot_data = np.array(screenshot)
                return AutomationResult(
                    success=True,
                    message="Screenshot captured",
                    data={'screenshot': screenshot_data},
                    execution_time=time.time() - start_time
                )
            
            elif action == 'get_mouse_position':
                position = pyautogui.position()
                return AutomationResult(
                    success=True,
                    message=f"Mouse position: {position}",
                    data={'position': {'x': position.x, 'y': position.y}},
                    execution_time=time.time() - start_time
                )
            
            else:
                return AutomationResult(
                    success=False,
                    message=f"Unknown GUI action: {action}",
                    execution_time=time.time() - start_time
                )
                
        except Exception as e:
            return AutomationResult(
                success=False,
                message=f"GUI automation failed: {str(e)}",
                execution_time=time.time() - start_time
            )


class SystemAutomation:
    """System-level automation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('SystemAutomation')
        
    async def initialize(self):
        """Initialize system automation"""
        self.logger.info("System Automation initialized")
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> AutomationResult:
        """Execute system automation action"""
        start_time = time.time()
        
        try:
            self.logger.info(f"Executing system action: {action}")
            
            if action == 'volume_up':
                # Simulate volume up key press
                pyautogui.press('volumeup')
                return AutomationResult(
                    success=True,
                    message="Volume increased",
                    execution_time=time.time() - start_time
                )
            
            elif action == 'volume_down':
                pyautogui.press('volumedown')
                return AutomationResult(
                    success=True,
                    message="Volume decreased",
                    execution_time=time.time() - start_time
                )
            
            elif action == 'mute':
                pyautogui.press('volumemute')
                return AutomationResult(
                    success=True,
                    message="Volume muted",
                    execution_time=time.time() - start_time
                )
            
            elif action == 'open_settings':
                subprocess.Popen(['start', 'ms-settings:'], shell=True)
                return AutomationResult(
                    success=True,
                    message="Settings opened",
                    execution_time=time.time() - start_time
                )
            
            else:
                return AutomationResult(
                    success=False,
                    message=f"Unknown system action: {action}",
                    execution_time=time.time() - start_time
                )
                
        except Exception as e:
            return AutomationResult(
                success=False,
                message=f"System automation failed: {str(e)}",
                execution_time=time.time() - start_time
            )


class WebAutomation:
    """Web browser automation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('WebAutomation')
        
    async def initialize(self):
        """Initialize web automation"""
        self.logger.info("Web Automation initialized")
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> AutomationResult:
        """Execute web automation action"""
        start_time = time.time()
        
        try:
            self.logger.info(f"Executing web action: {action}")
            
            if action == 'open_browser':
                browser = parameters.get('browser', 'chrome')
                url = parameters.get('url', 'https://www.google.com')
                webbrowser.open(url)
                return AutomationResult(
                    success=True,
                    message=f"Opened {browser} with {url}",
                    execution_time=time.time() - start_time
                )
            
            elif action == 'search_google':
                query = parameters.get('query', '')
                if query:
                    search_url = f"https://www.google.com/search?q={query}"
                    webbrowser.open(search_url)
                    return AutomationResult(
                        success=True,
                        message=f"Searched Google for: {query}",
                        execution_time=time.time() - start_time
                    )
                else:
                    return AutomationResult(
                        success=False,
                        message="No search query provided",
                        execution_time=time.time() - start_time
                    )
            
            else:
                return AutomationResult(
                    success=False,
                    message=f"Unknown web action: {action}",
                    execution_time=time.time() - start_time
                )
                
        except Exception as e:
            return AutomationResult(
                success=False,
                message=f"Web automation failed: {str(e)}",
                execution_time=time.time() - start_time
            )


class FileAutomation:
    """File system automation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('FileAutomation')
        
    async def initialize(self):
        """Initialize file automation"""
        self.logger.info("File Automation initialized")
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> AutomationResult:
        """Execute file automation action"""
        start_time = time.time()
        
        try:
            self.logger.info(f"Executing file action: {action}")
            
            if action == 'create_file':
                filename = parameters.get('filename')
                content = parameters.get('content', '')
                
                if filename:
                    with open(filename, 'w') as f:
                        f.write(content)
                    return AutomationResult(
                        success=True,
                        message=f"Created file: {filename}",
                        execution_time=time.time() - start_time
                    )
                else:
                    return AutomationResult(
                        success=False,
                        message="No filename provided",
                        execution_time=time.time() - start_time
                    )
            
            elif action == 'list_files':
                directory = parameters.get('directory', '.')
                import os
                files = os.listdir(directory)
                return AutomationResult(
                    success=True,
                    message=f"Listed files in {directory}",
                    data={'files': files, 'count': len(files)},
                    execution_time=time.time() - start_time
                )
            
            else:
                return AutomationResult(
                    success=False,
                    message=f"Unknown file action: {action}",
                    execution_time=time.time() - start_time
                )
                
        except Exception as e:
            return AutomationResult(
                success=False,
                message=f"File automation failed: {str(e)}",
                execution_time=time.time() - start_time
            )


class ProcessAutomation:
    """Process management automation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('ProcessAutomation')
        
    async def initialize(self):
        """Initialize process automation"""
        self.logger.info("Process Automation initialized")
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> AutomationResult:
        """Execute process automation action"""
        start_time = time.time()
        
        try:
            self.logger.info(f"Executing process action: {action}")
            
            if action == 'get_process_list':
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                    try:
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cpu_percent': proc.info['cpu_percent'],
                            'memory_percent': proc.info['memory_percent']
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                return AutomationResult(
                    success=True,
                    message=f"Found {len(processes)} processes",
                    data={'processes': processes},
                    execution_time=time.time() - start_time
                )
            
            elif action == 'find_process':
                name = parameters.get('name', '')
                if name:
                    found_processes = []
                    for proc in psutil.process_iter(['pid', 'name']):
                        try:
                            if name.lower() in proc.info['name'].lower():
                                found_processes.append({
                                    'pid': proc.info['pid'],
                                    'name': proc.info['name']
                                })
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    
                    return AutomationResult(
                        success=True,
                        message=f"Found {len(found_processes)} processes matching '{name}'",
                        data={'processes': found_processes},
                        execution_time=time.time() - start_time
                    )
                else:
                    return AutomationResult(
                        success=False,
                        message="No process name provided",
                        execution_time=time.time() - start_time
                    )
            
            else:
                return AutomationResult(
                    success=False,
                    message=f"Unknown process action: {action}",
                    execution_time=time.time() - start_time
                )
                
        except Exception as e:
            return AutomationResult(
                success=False,
                message=f"Process automation failed: {str(e)}",
                execution_time=time.time() - start_time
            )


# Example usage and testing
if __name__ == "__main__":
    async def test_automation():
        # Mock intelligence engine
        class MockIntelligence:
            pass
        
        config = {
            'gui_automation': True,
            'system_automation': True,
            'web_automation': True,
            'file_automation': True,
            'process_automation': True,
            'safety_mode': True,
            'confirmation_required': False,
            'max_concurrent_tasks': 5
        }
        
        engine = AutomationEngine(config, MockIntelligence())
        await engine.initialize()
        
        # Test automation
        test_intent = {
            'action': 'screenshot',
            'parameters': {},
            'command': 'take screenshot'
        }
        
        result = await engine.execute(test_intent)
        print(f"Automation result: {result}")
        
        # Test system status
        status = engine.get_system_status()
        print(f"System status: {status}")
    
    asyncio.run(test_automation())