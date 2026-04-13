"""
Automation Engine - Execute automated actions
Controls applications, types text, clicks buttons, etc.
"""

import asyncio
import subprocess
import re
from typing import Dict, Any, Optional
from datetime import datetime

class AutomationEngine:
    """
    Execute automated actions on Windows
    """
    
    def __init__(self, intelligence, memory):
        self.intelligence = intelligence
        self.memory = memory
        
        # Windows application paths
        self.app_paths = {
            'chrome': r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            'firefox': r'C:\Program Files\Mozilla Firefox\firefox.exe',
            'notepad': r'C:\Windows\System32\notepad.exe',
            'calculator': r'C:\Windows\System32\calc.exe',
            'explorer': r'C:\Windows\explorer.exe',
            'cmd': r'C:\Windows\System32\cmd.exe',
            'taskmgr': r'C:\Windows\System32\taskmgr.exe',
            'word': r'C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE',
            'excel': r'C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE'
        }
    
    async def initialize(self):
        """Initialize automation engine"""
        print("Automation engine initialized")
    
    async def execute_command(self, command: str, intent) -> str:
        """Execute automation command"""
        try:
            action = intent.entities.get('action')
            target = intent.entities.get('target')
            
            print(f"Executing: {action} on {target}")
            
            if action == 'open':
                return await self.open_application(target)
            
            elif action == 'close':
                return await self.close_application(target)
            
            elif action == 'type':
                text = intent.entities.get('text', '')
                return await self.type_text(text)
            
            elif action == 'click':
                x = intent.entities.get('x', 0)
                y = intent.entities.get('y', 0)
                return await self.click_position(x, y)
            
            elif action == 'minimize':
                return await self.minimize_window(target)
            
            elif action == 'maximize':
                return await self.maximize_window(target)
            
            elif action == 'switch':
                return await self.switch_application(target)
            
            elif action == 'scroll':
                direction = intent.entities.get('direction', 'down')
                return await self.scroll(direction)
            
            else:
                return f"Action '{action}' not recognized"
                
        except Exception as e:
            return f"Automation error: {str(e)}"
    
    async def open_application(self, app_name: str) -> str:
        """Open an application"""
        app_lower = app_name.lower()
        
        # Check direct paths
        if app_lower in self.app_paths:
            app_path = self.app_paths[app_lower]
            try:
                subprocess.Popen(app_path)
                return f"Opening {app_name}"
            except Exception as e:
                return f"Failed to open {app_name}: {str(e)}"
        
        # Try to open by name
        try:
            subprocess.Popen(app_name)
            return f"Opening {app_name}"
        except Exception as e:
            return f"Could not find {app_name}: {str(e)}"
    
    async def close_application(self, app_name: str) -> str:
        """Close an application"""
        try:
            import psutil
            app_lower = app_name.lower()
            
            closed = False
            for proc in psutil.process_iter(['name']):
                if app_lower in proc.info['name'].lower():
                    proc.kill()
                    closed = True
                    break
            
            if closed:
                return f"Closed {app_name}"
            else:
                return f"Could not find {app_name}"
                
        except ImportError:
            return "psutil not available for process management"
        except Exception as e:
            return f"Error closing {app_name}: {str(e)}"
    
    async def type_text(self, text: str) -> str:
        """Type text using keyboard"""
        try:
            import pyautogui
            pyautogui.write(text, interval=0.05)
            return f"Typed: {text}"
        except ImportError:
            return "pyautogui not available for typing"
        except Exception as e:
            return f"Error typing text: {str(e)}"
    
    async def click_position(self, x: int, y: int) -> str:
        """Click at specific position"""
        try:
            import pyautogui
            pyautogui.click(x, y)
            return f"Clicked at ({x}, {y})"
        except ImportError:
            return "pyautogui not available for clicking"
        except Exception as e:
            return f"Error clicking: {str(e)}"
    
    async def minimize_window(self, app_name: str) -> str:
        """Minimize a window"""
        try:
            import win32gui
            import win32con
            
            app_lower = app_name.lower()
            
            def callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if app_lower in title.lower():
                        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                        windows.append(hwnd)
            
            windows = []
            win32gui.EnumWindows(callback, windows)
            
            if windows:
                return f"Minimized {app_name}"
            else:
                return f"Could not find window for {app_name}"
                
        except ImportError:
            return "win32gui not available for window control"
        except Exception as e:
            return f"Error minimizing window: {str(e)}"
    
    async def maximize_window(self, app_name: str) -> str:
        """Maximize a window"""
        try:
            import win32gui
            import win32con
            
            app_lower = app_name.lower()
            
            def callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if app_lower in title.lower():
                        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                        windows.append(hwnd)
            
            windows = []
            win32gui.EnumWindows(callback, windows)
            
            if windows:
                return f"Maximized {app_name}"
            else:
                return f"Could not find window for {app_name}"
                
        except ImportError:
            return "win32gui not available for window control"
        except Exception as e:
            return f"Error maximizing window: {str(e)}"
    
    async def switch_application(self, app_name: str) -> str:
        """Switch to an application"""
        try:
            import win32gui
            
            app_lower = app_name.lower()
            
            def callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if app_lower in title.lower():
                        win32gui.SetForegroundWindow(hwnd)
                        windows.append(hwnd)
            
            windows = []
            win32gui.EnumWindows(callback, windows)
            
            if windows:
                return f"Switched to {app_name}"
            else:
                return f"Could not find window for {app_name}"
                
        except ImportError:
            return "win32gui not available for window switching"
        except Exception as e:
            return f"Error switching application: {str(e)}"
    
    async def scroll(self, direction: str) -> str:
        """Scroll in specified direction"""
        try:
            import pyautogui
            
            if direction == 'down':
                pyautogui.scroll(-10)
                return "Scrolled down"
            elif direction == 'up':
                pyautogui.scroll(10)
                return "Scrolled up"
            elif direction == 'left':
                pyautogui.scroll(-10, x=10)
                return "Scrolled left"
            elif direction == 'right':
                pyautogui.scroll(10, x=10)
                return "Scrolled right"
            else:
                return f"Invalid scroll direction: {direction}"
                
        except ImportError:
            return "pyautogui not available for scrolling"
        except Exception as e:
            return f"Error scrolling: {str(e)}"
    
    async def get_open_applications(self) -> List[Dict]:
        """Get list of currently open applications"""
        try:
            import psutil
            apps = []
            
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    apps.append({
                        'name': proc.info['name'],
                        'pid': proc.info['pid'],
                        'status': proc.status()
                    })
                except:
                    continue
            
            return apps
        except ImportError:
            return []
        except Exception as e:
            print(f"Error getting open apps: {e}")
            return []
    
    async def create_workflow(self, steps: List[Dict]) -> str:
        """Create and store a workflow"""
        try:
            workflow = {
                'id': str(datetime.now().timestamp()),
                'name': f"Workflow {len(steps)} steps",
                'steps': steps,
                'created_at': datetime.now().isoformat()
            }
            
            # Store in memory system
            await self.memory.store(
                content=f"workflow: {workflow['name']}",
                memory_type="workflow",
                priority=2
            )
            
            return f"Created workflow: {workflow['name']}"
            
        except Exception as e:
            return f"Error creating workflow: {str(e)}"
    
    async def execute_workflow(self, workflow_id: str) -> str:
        """Execute a stored workflow"""
        try:
            # Retrieve workflow from memory
            workflows = await self.memory.search_memories("workflow", "workflow")
            
            for workflow in workflows:
                if workflow_id in workflow['content']:
                    # Parse and execute steps
                    steps = workflow['steps']
                    
                    for i, step in enumerate(steps):
                        print(f"Executing step {i+1}: {step.get('action', 'unknown')}")
                        
                        # Create intent for step
                        step_intent = type('Intent', (), {
                            'type': 'automation',
                            'entities': step.get('entities', {})
                        })
                        
                        # Execute step
                        result = await self.execute_command(
                            f"execute {step.get('action', '')}",
                            step_intent
                        )
                        
                        print(f"Step result: {result}")
                        
                        # Wait between steps
                        await asyncio.sleep(1)
                    
                    return f"Executed workflow with {len(steps)} steps"
            
            return f"Workflow {workflow_id} not found"
            
        except Exception as e:
            return f"Error executing workflow: {str(e)}"
