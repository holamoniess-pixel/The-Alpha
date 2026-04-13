"""
Learning System - Observe user behavior and learn patterns
Automates repetitive tasks based on user habits
"""

import asyncio
import pickle
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

class LearningSystem:
    """
    Observe user and learn patterns for automation
    """
    
    def __init__(self, memory_system):
        self.memory = memory_system
        self.action_buffer = []
        self.patterns = []
        self.observing = False
        
        # Configuration
        self.buffer_size = 1000
        self.min_pattern_frequency = 3
        self.min_pattern_length = 3
        self.max_pattern_length = 10
        
        # Learning data file
        self.patterns_file = Path("data/learned_patterns.pkl")
        self.workflows_file = Path("data/user_workflows.json")
    
    async def initialize(self):
        """Initialize learning system"""
        # Create data directory
        Path("data").mkdir(exist_ok=True)
        
        # Load existing patterns
        self.patterns = await self.load_patterns()
        await self.load_workflows()
        
        print(f"Loaded {len(self.patterns)} learned patterns")
    
    async def start_observing(self):
        """Start observing user actions"""
        self.observing = True
        print("Started observing user behavior...")
        
        while self.observing:
            try:
                # Capture current user action
                action = await self.capture_action()
                
                if action:
                    # Add to buffer
                    self.action_buffer.append(action)
                    
                    # Keep buffer size limited
                    if len(self.action_buffer) > self.buffer_size:
                        self.action_buffer.pop(0)
                    
                    # Check for patterns periodically
                    if len(self.action_buffer) % 50 == 0:
                        await self.detect_patterns()
                
                await asyncio.sleep(0.1)  # Check every 100ms
                
            except Exception as e:
                print(f"Learning system error: {e}")
                await asyncio.sleep(1)  # Wait before retrying
    
    async def capture_action(self) -> Optional[Dict]:
        """Capture current user action"""
        try:
            # Get active window and mouse position
            action = await self.get_current_action()
            
            if action:
                action['timestamp'] = datetime.now()
                return action
                
        except Exception as e:
            print(f"Error capturing action: {e}")
        
        return None
    
    async def get_current_action(self) -> Optional[Dict]:
        """Get current user action (window, mouse, keyboard)"""
        try:
            # Try to get window title
            window_title = await self.get_active_window()
            
            # Get mouse position
            mouse_pos = await self.get_mouse_position()
            
            if window_title or mouse_pos:
                return {
                    'window': window_title or "Unknown",
                    'mouse_x': mouse_pos[0] if mouse_pos else 0,
                    'mouse_y': mouse_pos[1] if mouse_pos else 0,
                    'type': 'user_action'
                }
                
        except Exception as e:
            print(f"Error getting current action: {e}")
        
        return None
    
    async def get_active_window(self) -> Optional[str]:
        """Get active window title"""
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            return win32gui.GetWindowText(hwnd)
        except ImportError:
            return None
        except Exception as e:
            print(f"Error getting active window: {e}")
            return None
    
    async def get_mouse_position(self) -> Optional[Tuple[int, int]]:
        """Get current mouse position"""
        try:
            import pyautogui
            return pyautogui.position()
        except ImportError:
            return None
        except Exception as e:
            print(f"Error getting mouse position: {e}")
            return None
    
    async def detect_patterns(self):
        """Detect repeated patterns in user actions"""
        if len(self.action_buffer) < self.min_pattern_length:
            return
        
        # Look for sequences that repeat
        new_patterns = []
        
        for length in range(self.min_pattern_length, self.max_pattern_length + 1):
            sequences = self.find_sequences(length)
            
            for sequence in sequences:
                if sequence['frequency'] >= self.min_pattern_frequency:
                    # Check if we already have this pattern
                    if not self.has_pattern(sequence):
                        new_patterns.append(sequence)
                        print(f"New pattern detected: {sequence['sequence'][:3]}... (frequency: {sequence['frequency']})")
        
        # Add new patterns
        if new_patterns:
            self.patterns.extend(new_patterns)
            await self.save_patterns()
            
            # Suggest automation for new patterns
            for pattern in new_patterns:
                await self.suggest_automation(pattern)
    
    def find_sequences(self, length: int) -> List[Dict]:
        """Find repeated sequences of given length"""
        sequences = {}
        
        for i in range(len(self.action_buffer) - length + 1):
            # Extract sequence
            seq = tuple([
                self.action_to_key(self.action_buffer[i + j])
                for j in range(length)
            ])
            
            # Count occurrences
            if seq in sequences:
                sequences[seq] += 1
            else:
                sequences[seq] = 1
        
        # Convert to list of patterns
        patterns = []
        for seq, count in sequences.items():
            if count >= self.min_pattern_frequency:
                patterns.append({
                    'sequence': seq,
                    'frequency': count,
                    'length': length,
                    'detected_at': datetime.now(),
                    'id': str(datetime.now().timestamp())
                })
        
        return patterns
    
    def action_to_key(self, action: Dict) -> str:
        """Convert action to a simple key for pattern matching"""
        # Simplify action to key components
        window = action.get('window', '').lower()
        
        # Extract app name from window title
        app_name = self.extract_app_name(window)
        
        # Create key based on action type
        if 'click' in window.lower() or 'button' in window.lower():
            return f"click_{app_name}"
        elif 'type' in window.lower() or 'input' in window.lower():
            return f"type_{app_name}"
        elif 'scroll' in window.lower():
            return f"scroll_{app_name}"
        else:
            return f"open_{app_name}"
    
    def extract_app_name(self, window_title: str) -> str:
        """Extract app name from window title"""
        window_lower = window_title.lower()
        
        # Common app identifiers
        app_keywords = {
            'chrome': ['chrome', 'google chrome'],
            'firefox': ['firefox'],
            'notepad': ['notepad', 'untitled'],
            'calculator': ['calculator', 'calc'],
            'explorer': ['file explorer', 'explorer'],
            'word': ['word', 'microsoft word'],
            'excel': ['excel', 'microsoft excel']
        }
        
        for app, keywords in app_keywords.items():
            if any(keyword in window_lower for keyword in keywords):
                return app
        
        # Fallback: first word of title
        words = window_lower.split()
        return words[0] if words else 'unknown'
    
    def has_pattern(self, pattern: Dict) -> bool:
        """Check if pattern already exists"""
        for existing in self.patterns:
            if existing['sequence'] == pattern['sequence']:
                return True
        return False
    
    async def suggest_automation(self, pattern: Dict):
        """Suggest automating a detected pattern"""
        try:
            print(f"\n=== LEARNING DETECTION ===")
            print(f"Pattern detected {pattern['frequency']} times:")
            
            for i, step in enumerate(pattern['sequence'], 1):
                print(f"  {i}. {step}")
            
            print(f"\nWould you like me to automate this pattern?")
            print("Say 'automate this' to create a workflow")
            
            # Store suggestion for later reference
            await self.memory.store(
                content=f"automation_suggestion: {pattern['id']}",
                memory_type="suggestion",
                priority=2
            )
            
        except Exception as e:
            print(f"Error suggesting automation: {e}")
    
    async def create_workflow_from_pattern(self, pattern_id: str) -> str:
        """Create workflow from detected pattern"""
        try:
            # Find the pattern
            pattern = None
            for p in self.patterns:
                if p.get('id') == pattern_id:
                    pattern = p
                    break
            
            if not pattern:
                return "Pattern not found"
            
            # Convert pattern to workflow steps
            steps = []
            for i, action_key in enumerate(pattern['sequence']):
                step = self.action_key_to_step(action_key, i + 1)
                if step:
                    steps.append(step)
            
            # Create workflow
            workflow = {
                'id': f"workflow_{pattern_id}",
                'name': f"Automated {pattern['length']} steps",
                'description': f"Created from detected pattern",
                'steps': steps,
                'created_at': datetime.now().isoformat(),
                'pattern_id': pattern_id
            }
            
            # Save workflow
            await self.save_workflow(workflow)
            
            return f"Created workflow: {workflow['name']}"
            
        except Exception as e:
            return f"Error creating workflow: {str(e)}"
    
    def action_key_to_step(self, action_key: str, step_number: int) -> Optional[Dict]:
        """Convert action key to workflow step"""
        try:
            if 'click_' in action_key:
                app = action_key.replace('click_', '')
                return {
                    'action': 'click',
                    'description': f'Click in {app}',
                    'entities': {'app': app}
                }
            elif 'type_' in action_key:
                app = action_key.replace('type_', '')
                return {
                    'action': 'type',
                    'description': f'Type in {app}',
                    'entities': {'app': app}
                }
            elif 'open_' in action_key:
                app = action_key.replace('open_', '')
                return {
                    'action': 'open',
                    'description': f'Open {app}',
                    'entities': {'app': app}
                }
            else:
                return None
        except Exception as e:
            print(f"Error converting action key: {e}")
            return None
    
    async def save_workflow(self, workflow: Dict):
        """Save workflow to file"""
        try:
            workflows = await self.load_workflows()
            workflows.append(workflow)
            
            with open(self.workflows_file, 'w') as f:
                json.dump(workflows, f, indent=2)
                
            print(f"Saved workflow: {workflow['name']}")
            
        except Exception as e:
            print(f"Error saving workflow: {e}")
    
    async def load_workflows(self) -> List[Dict]:
        """Load workflows from file"""
        try:
            if self.workflows_file.exists():
                with open(self.workflows_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading workflows: {e}")
        
        return []
    
    async def load_patterns(self) -> List[Dict]:
        """Load saved patterns"""
        try:
            if self.patterns_file.exists():
                with open(self.patterns_file, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            print(f"Error loading patterns: {e}")
        
        return []
    
    async def save_patterns(self):
        """Save patterns to disk"""
        try:
            with open(self.patterns_file, 'wb') as f:
                pickle.dump(self.patterns, f)
        except Exception as e:
            print(f"Error saving patterns: {e}")
    
    async def get_learning_stats(self) -> Dict:
        """Get learning system statistics"""
        return {
            'patterns_detected': len(self.patterns),
            'actions_buffered': len(self.action_buffer),
            'observing': self.observing,
            'workflows_created': len(await self.load_workflows())
        }
    
    async def stop(self):
        """Stop observing"""
        self.observing = False
        await self.save_patterns()
        print("Learning system stopped")
