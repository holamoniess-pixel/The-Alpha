#!/usr/bin/env python3
"""
ALPHA OMEGA - SMART TUTOR SYSTEM
AI-powered visual guidance with green glowing cursor clone
Teaches users applications from beginner to pro
Version: 2.0.0
"""

import asyncio
import json
import logging
import time
import math
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import ctypes


class TutorialPhase(Enum):
    INTRODUCTION = "introduction"
    BASICS = "basics"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    PRO = "pro"
    PRACTICE = "practice"
    ASSESSMENT = "assessment"


class StepStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class ActionType(Enum):
    MOVE = "move"
    CLICK = "click"
    HOVER = "hover"
    DRAG = "drag"
    TYPE = "type"
    SCROLL = "scroll"
    WAIT = "wait"
    EXPLAIN = "explain"
    HIGHLIGHT = "highlight"
    DEMO = "demo"


@dataclass
class TutorialStep:
    id: str
    order: int
    action_type: ActionType
    description: str
    voice_instruction: str
    target_position: Tuple[int, int] = (0, 0)
    target_area: Tuple[int, int, int, int] = (0, 0, 0, 0)
    expected_action: str = ""
    timeout_seconds: float = 30.0
    prerequisites: List[str] = field(default_factory=list)
    tips: List[str] = field(default_factory=list)
    common_mistakes: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    started_at: float = 0
    completed_at: float = 0
    attempts: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "order": self.order,
            "action_type": self.action_type.value,
            "description": self.description,
            "voice_instruction": self.voice_instruction,
            "target_position": self.target_position,
            "status": self.status.value,
            "attempts": self.attempts,
        }


@dataclass
class TutorialLesson:
    id: str
    name: str
    application: str
    phase: TutorialPhase
    description: str
    objectives: List[str] = field(default_factory=list)
    steps: List[TutorialStep] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    estimated_time_minutes: int = 10
    difficulty: int = 1
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "application": self.application,
            "phase": self.phase.value,
            "description": self.description,
            "objectives": self.objectives,
            "step_count": len(self.steps),
            "difficulty": self.difficulty,
        }


@dataclass
class TutorialCourse:
    id: str
    name: str
    application: str
    description: str
    lessons: List[TutorialLesson] = field(default_factory=list)
    total_steps: int = 0
    current_lesson_index: int = 0
    current_step_index: int = 0
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "application": self.application,
            "description": self.description,
            "lesson_count": len(self.lessons),
            "total_steps": self.total_steps,
            "progress": self.get_progress(),
        }
    
    def get_progress(self) -> float:
        if self.total_steps == 0:
            return 0.0
        completed = sum(
            1 for lesson in self.lessons
            for step in lesson.steps
            if step.status == StepStatus.COMPLETED
        )
        return completed / self.total_steps


@dataclass
class UserMouseState:
    position: Tuple[int, int] = (0, 0)
    is_clicked: bool = False
    click_position: Tuple[int, int] = (0, 0)
    last_move_time: float = 0
    is_idle: bool = False
    idle_duration: float = 0


@dataclass
class TutorCursorState:
    position: Tuple[int, int] = (0, 0)
    target_position: Tuple[int, int] = (0, 0)
    is_visible: bool = False
    glow_intensity: float = 0.5
    pulse_phase: float = 0.0
    is_moving: bool = False
    animation_speed: float = 1.0


class GreenCursorClone:
    """The glowing green cursor that guides users"""
    
    CURSOR_SIZE = 32
    GLOW_COLOR = (0, 255, 100)
    INNER_COLOR = (100, 255, 150)
    PULSE_SPEED = 2.0
    
    def __init__(self):
        self.logger = logging.getLogger("GreenCursorClone")
        self.state = TutorCursorState()
        self._overlay_window = None
        self._running = False
        self._draw_thread: Optional[threading.Thread] = None
    
    async def initialize(self) -> bool:
        """Initialize the cursor overlay"""
        self.logger.info("Green Cursor Clone initialized")
        return True
    
    def start(self):
        """Start the cursor animation"""
        self._running = True
        self.state.is_visible = True
        self._draw_thread = threading.Thread(target=self._animation_loop, daemon=True)
        self._draw_thread.start()
    
    def stop(self):
        """Stop the cursor animation"""
        self._running = False
        self.state.is_visible = False
    
    def _animation_loop(self):
        """Main animation loop"""
        import tkinter as tk
        
        root = tk.Tk()
        root.attributes('-topmost', True)
        root.attributes('-transparentcolor', 'black')
        root.overrideredirect(True)
        root.config(bg='black')
        
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        root.geometry(f"{screen_width}x{screen_height}+0+0")
        
        canvas = tk.Canvas(root, width=screen_width, height=screen_height, 
                          bg='black', highlightthickness=0)
        canvas.pack()
        
        self._overlay_window = root
        self._canvas = canvas
        
        def update():
            if not self._running:
                root.destroy()
                return
            
            canvas.delete("all")
            
            if self.state.is_visible:
                self._draw_cursor(canvas)
            
            root.after(16, update)
        
        update()
        root.mainloop()
    
    def _draw_cursor(self, canvas):
        """Draw the green glowing cursor"""
        x, y = self.state.position
        
        self.state.pulse_phase += 0.05 * self.PULSE_SPEED
        pulse = (math.sin(self.state.pulse_phase) + 1) / 2
        
        glow_size = self.CURSOR_SIZE + int(20 * pulse)
        
        for i in range(5, 0, -1):
            alpha = int(50 * (1 - i/5) * self.state.glow_intensity)
            size = glow_size + i * 8
            color = f'#{self.GLOW_COLOR[0]:02x}{self.GLOW_COLOR[1]:02x}{self.GLOW_COLOR[2]:02x}'
            
            canvas.create_oval(
                x - size, y - size, x + size, y + size,
                fill='', outline=color, width=3
            )
        
        arrow_points = self._get_arrow_points(x, y, self.CURSOR_SIZE)
        canvas.create_polygon(
            arrow_points,
            fill=f'#{self.INNER_COLOR[0]:02x}{self.INNER_COLOR[1]:02x}{self.INNER_COLOR[2]:02x}',
            outline=f'#{self.GLOW_COLOR[0]:02x}{self.GLOW_COLOR[1]:02x}{self.GLOW_COLOR[2]:02x}',
            width=2
        )
    
    def _get_arrow_points(self, x: int, y: int, size: int) -> List[Tuple[int, int]]:
        """Get cursor arrow polygon points"""
        return [
            x, y,
            x, y + size,
            x + size // 4, y + size * 0.75,
            x + size // 2, y + size,
            x + size * 0.6, y + size * 0.85,
            x + size // 3, y + size * 0.6,
            x + size, y + size * 0.6,
            x, y
        ]
    
    async def move_to(self, target: Tuple[int, int], duration: float = 1.0):
        """Smoothly move cursor to target position"""
        start = self.state.position
        self.state.target_position = target
        self.state.is_moving = True
        
        steps = int(duration * 60)
        
        for i in range(steps):
            progress = i / steps
            eased = self._ease_out_cubic(progress)
            
            x = start[0] + (target[0] - start[0]) * eased
            y = start[1] + (target[1] - start[1]) * eased
            
            self.state.position = (int(x), int(y))
            await asyncio.sleep(1/60)
        
        self.state.position = target
        self.state.is_moving = False
    
    def _ease_out_cubic(self, t: float) -> float:
        """Cubic ease-out function for smooth animation"""
        return 1 - pow(1 - t, 3)
    
    async def click_at(self, position: Tuple[int, int]):
        """Animate a click at position"""
        await self.move_to(position, 0.5)
        
        for _ in range(3):
            self.state.glow_intensity = 1.0
            await asyncio.sleep(0.1)
            self.state.glow_intensity = 0.5
            await asyncio.sleep(0.1)
    
    async def highlight_area(self, area: Tuple[int, int, int, int], duration: float = 2.0):
        """Highlight an area on screen"""
        center_x = (area[0] + area[2]) // 2
        center_y = (area[1] + area[3]) // 2
        
        await self.move_to((center_x, center_y), 0.3)
        
        self.state.glow_intensity = 1.0
        await asyncio.sleep(duration)
        self.state.glow_intensity = 0.5
    
    def set_position(self, position: Tuple[int, int]):
        """Instantly set cursor position"""
        self.state.position = position
    
    def show(self):
        """Show the cursor"""
        self.state.is_visible = True
    
    def hide(self):
        """Hide the cursor"""
        self.state.is_visible = False


class UserMouseTracker:
    """Track user's mouse movements"""
    
    def __init__(self):
        self.logger = logging.getLogger("UserMouseTracker")
        self.state = UserMouseState()
        self._running = False
        self._listeners: List[Callable] = []
    
    async def initialize(self) -> bool:
        """Initialize mouse tracking"""
        self.logger.info("User Mouse Tracker initialized")
        return True
    
    def start(self):
        """Start tracking"""
        self._running = True
        threading.Thread(target=self._track_loop, daemon=True).start()
    
    def stop(self):
        """Stop tracking"""
        self._running = False
    
    def _track_loop(self):
        """Main tracking loop"""
        from pynput import mouse
        
        def on_move(x, y):
            self.state.position = (int(x), int(y))
            self.state.last_move_time = time.time()
            self.state.is_idle = False
            self.state.idle_duration = 0
            
            for listener in self._listeners:
                try:
                    listener("move", (int(x), int(y)))
                except Exception as e:
                    self.logger.error(f"Listener error: {e}")
        
        def on_click(x, y, button, pressed):
            if pressed:
                self.state.is_clicked = True
                self.state.click_position = (int(x), int(y))
                
                for listener in self._listeners:
                    try:
                        listener("click", (int(x), int(y)))
                    except Exception as e:
                        self.logger.error(f"Listener error: {e}")
            else:
                self.state.is_clicked = False
        
        def on_scroll(x, y, dx, dy):
            for listener in self._listeners:
                try:
                    listener("scroll", (int(x), int(y), dx, dy))
                except Exception as e:
                    self.logger.error(f"Listener error: {e}")
        
        listener = mouse.Listener(
            on_move=on_move,
            on_click=on_click,
            on_scroll=on_scroll
        )
        
        listener.start()
        
        while self._running:
            idle_time = time.time() - self.state.last_move_time
            if idle_time > 2.0:
                self.state.is_idle = True
                self.state.idle_duration = idle_time
            time.sleep(0.1)
        
        listener.stop()
    
    def add_listener(self, callback: Callable):
        """Add event listener"""
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable):
        """Remove event listener"""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def get_position(self) -> Tuple[int, int]:
        """Get current mouse position"""
        return self.state.position
    
    def is_near(self, target: Tuple[int, int], threshold: int = 50) -> bool:
        """Check if mouse is near target"""
        dx = self.state.position[0] - target[0]
        dy = self.state.position[1] - target[1]
        distance = math.sqrt(dx*dx + dy*dy)
        return distance < threshold


class VoiceTutor:
    """Voice guidance for tutorials"""
    
    def __init__(self, tts_engine=None):
        self.tts_engine = tts_engine
        self.logger = logging.getLogger("VoiceTutor")
        self._speaking = False
        self._queue: List[str] = []
    
    async def initialize(self) -> bool:
        """Initialize voice tutor"""
        self.logger.info("Voice Tutor initialized")
        return True
    
    async def speak(self, text: str, wait: bool = True):
        """Speak instruction"""
        self._speaking = True
        
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.setProperty('volume', 0.9)
            
            engine.say(text)
            engine.runAndWait()
            
        except Exception as e:
            self.logger.error(f"TTS error: {e}")
            print(f"[VOICE]: {text}")
        
        self._speaking = False
    
    async def speak_async(self, text: str):
        """Speak without waiting"""
        asyncio.create_task(self.speak(text, False))
    
    async def greet(self, app_name: str, lesson_name: str):
        """Greeting message"""
        await self.speak(f"Welcome! I'll guide you through {lesson_name} in {app_name}.")
    
    async def instruct(self, instruction: str):
        """Give instruction"""
        await self.speak(instruction)
    
    async fn encourage(self):
        """Encouragement message"""
        messages = [
            "Great job!",
            "Perfect!",
            "You're doing well!",
            "Excellent!",
            "That's it!",
        ]
        import random
        await self.speak(random.choice(messages))
    
    async def correct(self, message: str):
        """Correction message"""
        await self.speak(f"Let me help you. {message}")
    
    async def explain(self, explanation: str):
        """Explain concept"""
        await self.speak(explanation)
    
    async def warn(self, warning: str):
        """Warning message"""
        await self.speak(f"Be careful! {warning}")
    
    async def celebrate(self):
        """Celebration message"""
        await self.speak("Congratulations! You've completed this lesson!")
    
    def is_speaking(self) -> bool:
        """Check if speaking"""
        return self._speaking
    
    async def stop_speaking(self):
        """Stop current speech"""
        self._speaking = False


class ApplicationCurriculum:
    """Pre-built tutorials for popular applications"""
    
    CURRICULUM = {
        "capcut": {
            "name": "CapCut",
            "description": "Video editing from beginner to pro",
            "lessons": [
                {
                    "name": "Getting Started with CapCut",
                    "phase": "introduction",
                    "description": "Learn the basics of CapCut interface",
                    "objectives": [
                        "Open CapCut",
                        "Create a new project",
                        "Understand the interface layout"
                    ],
                    "steps": [
                        {
                            "action": "move",
                            "description": "Look at the CapCut icon",
                            "voice": "First, let's locate CapCut on your desktop or start menu. Follow my green cursor to find it.",
                            "tips": ["CapCut has a black and purple icon", "Look for it in your Start menu if not on desktop"]
                        },
                        {
                            "action": "click",
                            "description": "Open CapCut",
                            "voice": "Now double-click to open CapCut. I'll wait for you to do this.",
                            "expected": "double_click",
                            "tips": ["Make sure to double-click quickly", "You can also press Enter if the icon is selected"]
                        },
                        {
                            "action": "wait",
                            "description": "Wait for CapCut to load",
                            "voice": "Great! CapCut is now opening. This may take a few seconds.",
                            "timeout": 10
                        },
                        {
                            "action": "move",
                            "description": "Locate the New Project button",
                            "voice": "Once CapCut opens, look for the 'New Project' button. It's usually in the center or top right. Follow my cursor.",
                            "tips": ["The button is usually blue or purple", "It says 'New Project' clearly"]
                        },
                        {
                            "action": "click",
                            "description": "Click New Project",
                            "voice": "Click on 'New Project' to start a new video editing project. Go ahead, I'm watching.",
                            "expected": "click"
                        },
                        {
                            "action": "explain",
                            "description": "Interface overview",
                            "voice": "Excellent! Now you're in the CapCut editor. The left side shows your media library where you import videos. The center is your preview window. The bottom is your timeline where you arrange clips. The right side has your tools and effects.",
                            "tips": ["Take a moment to look around", "Don't worry, we'll cover each part in detail"]
                        }
                    ]
                },
                {
                    "name": "Importing Media",
                    "phase": "basics",
                    "description": "Learn to import videos and images",
                    "objectives": [
                        "Import video files",
                        "Import images",
                        "Organize media in the library"
                    ],
                    "steps": [
                        {
                            "action": "move",
                            "description": "Locate the import button",
                            "voice": "To add your videos, we need to import them. Look for the 'Import' button in the top left. Follow my green cursor.",
                        },
                        {
                            "action": "click",
                            "description": "Click Import",
                            "voice": "Click 'Import' to open the file browser. This lets you select videos from your computer.",
                            "expected": "click"
                        },
                        {
                            "action": "explain",
                            "description": "Selecting files",
                            "voice": "Now navigate to your video folder. You can hold Ctrl and click multiple files to import several at once. Try importing a video now.",
                            "tips": ["Use Ctrl+click to select multiple files", "Supported formats include MP4, MOV, and AVI"]
                        },
                        {
                            "action": "wait",
                            "description": "Wait for import",
                            "voice": "Great choice! The video is now importing. Watch as it appears in your media library on the left.",
                            "timeout": 5
                        }
                    ]
                },
                {
                    "name": "Adding Clips to Timeline",
                    "phase": "basics",
                    "description": "Learn to add clips to the timeline",
                    "objectives": [
                        "Drag clips to timeline",
                        "Arrange clip order",
                        "Understand timeline tracks"
                    ],
                    "steps": [
                        {
                            "action": "move",
                            "description": "Hover over a clip",
                            "voice": "Now let's add your clip to the timeline. Hover over the video in your media library. Follow my cursor.",
                        },
                        {
                            "action": "drag",
                            "description": "Drag to timeline",
                            "voice": "Click and hold the video, then drag it down to the timeline at the bottom. I'll show you where to drop it.",
                            "tips": ["The timeline is the striped area at the bottom", "A green line will show where the clip will be placed"]
                        },
                        {
                            "action": "explain",
                            "description": "Timeline explanation",
                            "voice": "Perfect! Your clip is now on the timeline. The timeline shows your video from left to right. Each clip is a rectangle. You can have multiple clips in a row, and they'll play one after another.",
                        }
                    ]
                },
                {
                    "name": "Basic Editing - Split and Delete",
                    "phase": "intermediate",
                    "description": "Learn to split and remove parts of clips",
                    "objectives": [
                        "Use the split tool",
                        "Delete unwanted sections",
                        "Trim clips"
                    ],
                    "steps": [
                        {
                            "action": "move",
                            "description": "Position playhead",
                            "voice": "Let's learn to cut out parts you don't want. First, click on the timeline where you want to make a cut. This white line is called the playhead. Follow my cursor to position it.",
                        },
                        {
                            "action": "move",
                            "description": "Locate Split button",
                            "voice": "Now look for the 'Split' button in the toolbar above the timeline. It looks like scissors. Or press Ctrl+B as a shortcut.",
                        },
                        {
                            "action": "click",
                            "description": "Click Split",
                            "voice": "Click Split to cut the clip at the playhead position. Your clip is now divided into two parts!",
                        },
                        {
                            "action": "move",
                            "description": "Select segment to delete",
                            "voice": "Click on the part you want to remove to select it. It will be highlighted.",
                        },
                        {
                            "action": "click",
                            "description": "Delete segment",
                            "voice": "Now press Delete on your keyboard, or right-click and select Delete. The unwanted part is gone!",
                        }
                    ]
                },
                {
                    "name": "Adding Transitions",
                    "phase": "intermediate",
                    "description": "Create smooth transitions between clips",
                    "objectives": [
                        "Apply transitions",
                        "Adjust transition duration",
                        "Preview transitions"
                    ],
                    "steps": [
                        {
                            "action": "move",
                            "description": "Open Transitions panel",
                            "voice": "Transitions make your video flow smoothly. Click on 'Transitions' in the left sidebar. Follow my cursor.",
                        },
                        {
                            "action": "explain",
                            "description": "Browse transitions",
                            "voice": "You'll see many transition options like dissolve, slide, and wipe. Hover over each to preview how it looks.",
                        },
                        {
                            "action": "drag",
                            "description": "Drag transition between clips",
                            "voice": "Drag a transition and drop it between two clips on your timeline. It will automatically apply.",
                        },
                        {
                            "action": "click",
                            "description": "Adjust duration",
                            "voice": "Click on the transition to select it. You can adjust its duration by dragging its edges, or use the settings panel on the right.",
                        }
                    ]
                },
                {
                    "name": "Adding Text and Titles",
                    "phase": "intermediate",
                    "description": "Add text overlays and titles",
                    "objectives": [
                        "Add text to video",
                        "Customize text style",
                        "Animate text"
                    ],
                    "steps": [
                        {
                            "action": "move",
                            "description": "Open Text panel",
                            "voice": "Let's add some text! Click 'Text' on the left sidebar. This opens all text options. Follow my green cursor.",
                        },
                        {
                            "action": "click",
                            "description": "Choose text template",
                            "voice": "You can choose from preset styles or create your own. Click on 'Add text' to create a basic text layer.",
                        },
                        {
                            "action": "type",
                            "description": "Enter your text",
                            "voice": "Type your text in the preview window. This is your title that will appear on screen.",
                        },
                        {
                            "action": "move",
                            "description": "Customize text",
                            "voice": "On the right panel, you can change font, size, color, and position. Follow my cursor to see these options.",
                        }
                    ]
                },
                {
                    "name": "Adding Music and Sound",
                    "phase": "intermediate",
                    "description": "Add background music and sound effects",
                    "objectives": [
                        "Import audio files",
                        "Add music to timeline",
                        "Adjust audio levels"
                    ],
                    "steps": [
                        {
                            "action": "move",
                            "description": "Open Audio panel",
                            "voice": "Music brings your video to life! Click 'Audio' on the left. You can browse CapCut's library or import your own music.",
                        },
                        {
                            "action": "drag",
                            "description": "Add audio track",
                            "voice": "Drag a song to the timeline. It will appear below your video clips on a separate audio track.",
                        },
                        {
                            "action": "move",
                            "description": "Adjust volume",
                            "voice": "Click on the audio clip and use the volume slider on the right to adjust how loud it plays. Background music should be softer than voice.",
                        }
                    ]
                },
                {
                    "name": "Applying Effects and Filters",
                    "phase": "advanced",
                    "description": "Enhance video with effects",
                    "objectives": [
                        "Apply video filters",
                        "Use effects",
                        "Adjust effect intensity"
                    ],
                    "steps": [
                        {
                            "action": "move",
                            "description": "Open Effects panel",
                            "voice": "Effects can transform your video's look! Click 'Effects' on the left. Follow my glowing cursor.",
                        },
                        {
                            "action": "explain",
                            "description": "Browse effect categories",
                            "voice": "You'll see categories like Video Effects, Filters, and Lens. Each has many options to explore.",
                        },
                        {
                            "action": "drag",
                            "description": "Apply effect to clip",
                            "voice": "Drag an effect onto a clip on the timeline. The effect will be applied to that entire clip.",
                        },
                        {
                            "action": "click",
                            "description": "Adjust effect settings",
                            "voice": "Click on the effect name above the clip to adjust its intensity and other settings.",
                        }
                    ]
                },
                {
                    "name": "Exporting Your Video",
                    "phase": "advanced",
                    "description": "Save and export your project",
                    "objectives": [
                        "Choose export settings",
                        "Select resolution and format",
                        "Export the final video"
                    ],
                    "steps": [
                        {
                            "action": "move",
                            "description": "Find Export button",
                            "voice": "Your masterpiece is ready! Look for the 'Export' button in the top right corner. Follow my cursor.",
                        },
                        {
                            "action": "click",
                            "description": "Click Export",
                            "voice": "Click 'Export' to open the export settings window.",
                        },
                        {
                            "action": "explain",
                            "description": "Choose resolution",
                            "voice": "Select your resolution. 1080p is good for most uses, 4K if you need higher quality. Higher resolution means larger file size.",
                        },
                        {
                            "action": "click",
                            "description": "Start export",
                            "voice": "Click 'Export' at the bottom to start rendering your video. This may take a few minutes depending on video length.",
                        },
                        {
                            "action": "wait",
                            "description": "Wait for completion",
                            "voice": "Watch the progress bar. Once complete, your video will be saved to your chosen location!",
                        }
                    ]
                },
                {
                    "name": "Advanced Tips for Pro Editing",
                    "phase": "pro",
                    "description": "Professional tips and tricks",
                    "objectives": [
                        "Use keyboard shortcuts",
                        "Master timeline navigation",
                        "Advanced editing techniques"
                    ],
                    "steps": [
                        {
                            "action": "explain",
                            "description": "Keyboard shortcuts",
                            "voice": "Let me share pro tips! Use Ctrl+S to save often. Spacebar plays and pauses. Arrow keys move frame by frame. Ctrl+Z undoes mistakes.",
                        },
                        {
                            "action": "explain",
                            "description": "Keyframe animations",
                            "voice": "Keyframes let you animate anything over time. Click the diamond icon next to any property to add a keyframe. Change the value at different points to create smooth animations.",
                        },
                        {
                            "action": "explain",
                            "description": "Speed ramping",
                            "voice": "Speed ramping creates dramatic slow-mo or fast motion. Select a clip, go to Speed, and choose 'Curve' to create custom speed changes.",
                        },
                        {
                            "action": "explain",
                            "description": "Color grading",
                            "voice": "For cinematic looks, use the Adjust panel. Play with saturation, temperature, and contrast to create your signature style.",
                        }
                    ]
                }
            ]
        },
        "vscode": {
            "name": "Visual Studio Code",
            "description": "Code editing mastery",
            "lessons": [
                {
                    "name": "VS Code Interface",
                    "phase": "introduction",
                    "description": "Learn the VS Code layout",
                    "objectives": ["Understand sidebar", "Know the editor area", "Use the terminal"],
                    "steps": [
                        {
                            "action": "move",
                            "description": "Look at the sidebar",
                            "voice": "Welcome to VS Code! The left sidebar has your file explorer, search, source control, and extensions. Follow my green cursor.",
                        },
                        {
                            "action": "explain",
                            "description": "Editor area",
                            "voice": "The center is where you write code. You can have multiple files open as tabs at the top.",
                        },
                        {
                            "action": "move",
                            "description": "Terminal location",
                            "voice": "At the bottom is the terminal. Press Ctrl+` to toggle it. This lets you run commands without leaving VS Code.",
                        }
                    ]
                }
            ]
        }
    }
    
    @classmethod
    def get_available_applications(cls) -> List[str]:
        """Get list of available application tutorials"""
        return list(cls.CURRICULUM.keys())
    
    @classmethod
    def get_course(cls, app_name: str) -> Optional[Dict[str, Any]]:
        """Get course for an application"""
        return cls.CURRICULUM.get(app_name.lower())


class SmartTutor:
    """Main Smart Tutor system that combines all components"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("SmartTutor")
        
        self.green_cursor = GreenCursorClone()
        self.mouse_tracker = UserMouseTracker()
        self.voice_tutor = VoiceTutor()
        
        self._current_course: Optional[TutorialCourse] = None
        self._current_lesson: Optional[TutorialLesson] = None
        self._current_step: Optional[TutorialStep] = None
        
        self._is_teaching = False
        self._is_paused = False
        self._waiting_for_user = False
        
        self._progress_callbacks: List[Callable] = []
    
    async def initialize(self) -> bool:
        """Initialize the smart tutor"""
        self.logger.info("Initializing Smart Tutor...")
        
        await self.green_cursor.initialize()
        await self.mouse_tracker.initialize()
        await self.voice_tutor.initialize()
        
        self.mouse_tracker.add_listener(self._on_user_action)
        
        self.logger.info("Smart Tutor initialized")
        return True
    
    def _on_user_action(self, action_type: str, data: Any):
        """Handle user action events"""
        if not self._is_teaching or self._is_paused:
            return
        
        if self._waiting_for_user:
            if action_type == "click":
                self._check_user_action(data)
    
    def _check_user_action(self, position: Tuple[int, int]):
        """Check if user performed expected action"""
        if not self._current_step:
            return
        
        target = self._current_step.target_position
        
        if target and self.mouse_tracker.is_near(target, threshold=30):
            self._waiting_for_user = False
            self._current_step.status = StepStatus.COMPLETED
            self._current_step.completed_at = time.time()
            
            asyncio.create_task(self._on_step_completed())
    
    async def _on_step_completed(self):
        """Handle step completion"""
        await self.voice_tutor.encourage()
        await self._next_step()
    
    def get_available_courses(self) -> List[str]:
        """Get available tutorial courses"""
        return ApplicationCurriculum.get_available_applications()
    
    async def start_course(self, app_name: str, start_phase: str = "introduction") -> bool:
        """Start a tutorial course"""
        curriculum = ApplicationCurriculum.get_course(app_name)
        
        if not curriculum:
            self.logger.error(f"No curriculum found for: {app_name}")
            return False
        
        course = TutorialCourse(
            id=f"{app_name}_{int(time.time())}",
            name=curriculum["name"],
            application=app_name,
            description=curriculum["description"],
        )
        
        for lesson_data in curriculum["lessons"]:
            lesson = TutorialLesson(
                id=f"{course.id}_lesson_{len(course.lessons)}",
                name=lesson_data["name"],
                application=app_name,
                phase=TutorialPhase(lesson_data.get("phase", "basics")),
                description=lesson_data["description"],
                objectives=lesson_data.get("objectives", []),
            )
            
            for i, step_data in enumerate(lesson_data.get("steps", [])):
                step = TutorialStep(
                    id=f"{lesson.id}_step_{i}",
                    order=i,
                    action_type=ActionType(step_data.get("action", "move")),
                    description=step_data.get("description", ""),
                    voice_instruction=step_data.get("voice", ""),
                    tips=step_data.get("tips", []),
                )
                lesson.steps.append(step)
            
            course.lessons.append(lesson)
            course.total_steps += len(lesson.steps)
        
        self._current_course = course
        self._is_teaching = True
        
        self.green_cursor.start()
        self.mouse_tracker.start()
        
        self.green_cursor.show()
        
        await self.voice_tutor.greet(curriculum["name"], course.lessons[0].name if course.lessons else "")
        
        await self._start_lesson(0)
        
        return True
    
    async def _start_lesson(self, lesson_index: int):
        """Start a specific lesson"""
        if not self._current_course:
            return
        
        if lesson_index >= len(self._current_course.lessons):
            await self._complete_course()
            return
        
        self._current_course.current_lesson_index = lesson_index
        self._current_lesson = self._current_course.lessons[lesson_index]
        self._current_lesson_index = 0
        
        await self.voice_tutor.speak(f"Now let's learn: {self._current_lesson.name}")
        await asyncio.sleep(1)
        
        await self._next_step()
    
    async def _next_step(self):
        """Proceed to next step"""
        if not self._current_lesson:
            return
        
        step_index = self._current_course.current_step_index
        
        if step_index >= len(self._current_lesson.steps):
            await self._complete_lesson()
            return
        
        self._current_step = self._current_lesson.steps[step_index]
        self._current_step.status = StepStatus.IN_PROGRESS
        self._current_step.started_at = time.time()
        
        await self._execute_step(self._current_step)
    
    async def _execute_step(self, step: TutorialStep):
        """Execute a tutorial step"""
        await self.voice_tutor.speak(step.voice_instruction)
        
        if step.action_type == ActionType.MOVE:
            await self.green_cursor.move_to(step.target_position, 1.5)
            self._waiting_for_user = True
        
        elif step.action_type == ActionType.CLICK:
            await self.green_cursor.click_at(step.target_position)
            self._waiting_for_user = True
        
        elif step.action_type == ActionType.HOVER:
            await self.green_cursor.highlight_area(step.target_area, 2.0)
            self._waiting_for_user = True
        
        elif step.action_type == ActionType.EXPLAIN:
            await asyncio.sleep(2)
            step.status = StepStatus.COMPLETED
            self._current_course.current_step_index += 1
            await self._next_step()
        
        elif step.action_type == ActionType.WAIT:
            await asyncio.sleep(step.timeout_seconds)
            step.status = StepStatus.COMPLETED
            self._current_course.current_step_index += 1
            await self._next_step()
    
    async def _complete_lesson(self):
        """Complete current lesson"""
        if self._current_lesson:
            await self.voice_tutor.celebrate()
        
        next_lesson_index = self._current_course.current_lesson_index + 1
        self._current_course.current_step_index = 0
        
        if next_lesson_index < len(self._current_course.lessons):
            await self._start_lesson(next_lesson_index)
        else:
            await self._complete_course()
    
    async def _complete_course(self):
        """Complete the entire course"""
        await self.voice_tutor.speak("Congratulations! You have completed the entire course!")
        self.green_cursor.hide()
        self._is_teaching = False
    
    def pause(self):
        """Pause the tutorial"""
        self._is_paused = True
        self.green_cursor.hide()
    
    def resume(self):
        """Resume the tutorial"""
        self._is_paused = False
        self.green_cursor.show()
    
    async def skip_step(self):
        """Skip current step"""
        if self._current_step:
            self._current_step.status = StepStatus.SKIPPED
            self._current_course.current_step_index += 1
            await self._next_step()
    
    async def repeat_step(self):
        """Repeat current step"""
        if self._current_step:
            self._current_step.attempts += 1
            await self._execute_step(self._current_step)
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress"""
        if not self._current_course:
            return {}
        
        return {
            "course": self._current_course.to_dict(),
            "current_lesson": self._current_lesson.to_dict() if self._current_lesson else None,
            "current_step": self._current_step.to_dict() if self._current_step else None,
            "progress_percent": self._current_course.get_progress() * 100,
        }
    
    def stop(self):
        """Stop the tutorial"""
        self._is_teaching = False
        self.green_cursor.stop()
        self.mouse_tracker.stop()
    
    async def suggest_next_topic(self) -> List[str]:
        """Suggest what to learn next"""
        suggestions = []
        
        if self._current_course:
            remaining_lessons = self._current_course.lessons[self._current_course.current_lesson_index+1:]
            suggestions.extend([l.name for l in remaining_lessons[:3]])
        
        return suggestions
