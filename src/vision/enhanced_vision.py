#!/usr/bin/env python3
"""
ALPHA OMEGA - COMPUTER VISION ENHANCEMENT
OCR, UI element recognition, face detection, gestures
Version: 2.0.0
"""

import asyncio
import json
import logging
import time
import base64
import io
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class VisionTask(Enum):
    OCR = "ocr"
    OBJECT_DETECTION = "object_detection"
    FACE_DETECTION = "face_detection"
    UI_ELEMENT = "ui_element"
    SCREEN_CAPTURE = "screen_capture"
    TEXT_SEARCH = "text_search"
    IMAGE_SEARCH = "image_search"
    GESTURE = "gesture"
    MOTION = "motion"


@dataclass
class BoundingBox:
    x: int
    y: int
    width: int
    height: int
    
    def to_dict(self) -> Dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass
class DetectedObject:
    label: str
    confidence: float
    bbox: BoundingBox
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "bbox": self.bbox.to_dict(),
            "attributes": self.attributes,
        }


@dataclass
class DetectedText:
    text: str
    confidence: float
    bbox: BoundingBox
    language: str = "en"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bbox": self.bbox.to_dict(),
            "language": self.language,
        }


@dataclass
class UIElement:
    element_type: str
    text: str
    bbox: BoundingBox
    is_clickable: bool = False
    is_visible: bool = True
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.element_type,
            "text": self.text,
            "bbox": self.bbox.to_dict(),
            "clickable": self.is_clickable,
            "visible": self.is_visible,
        }


@dataclass
class DetectedFace:
    bbox: BoundingBox
    landmarks: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    emotion: str = ""
    identity: str = ""
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "bbox": self.bbox.to_dict(),
            "emotion": self.emotion,
            "identity": self.identity,
            "confidence": self.confidence,
        }


@dataclass
class GestureResult:
    gesture: str
    confidence: float
    hand_landmarks: List[Tuple[int, int]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "gesture": self.gesture,
            "confidence": self.confidence,
        }


class ScreenCapture:
    """Capture screen content"""
    
    def __init__(self):
        self.logger = logging.getLogger("ScreenCapture")
    
    async def capture_screen(self, region: Tuple[int, int, int, int] = None) -> bytes:
        """Capture screen or region"""
        try:
            import mss
            
            with mss.mss() as sct:
                if region:
                    monitor = {
                        "left": region[0],
                        "top": region[1],
                        "width": region[2] - region[0],
                        "height": region[3] - region[1],
                    }
                else:
                    monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                
                screenshot = sct.grab(monitor)
                
                import mss.tools
                return mss.tools.to_png(screenshot.rgb, screenshot.size)
                
        except ImportError:
            self.logger.warning("mss not installed, trying PIL")
            return await self._capture_with_pil(region)
    
    async def _capture_with_pil(self, region: Tuple[int, int, int, int] = None) -> bytes:
        """Fallback capture with PIL"""
        try:
            from PIL import ImageGrab
            import io
            
            if region:
                screenshot = ImageGrab.grab(bbox=region)
            else:
                screenshot = ImageGrab.grab()
            
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            return buffer.getvalue()
            
        except ImportError:
            self.logger.error("PIL not available")
            return b''
    
    async def capture_window(self, window_title: str) -> bytes:
        """Capture specific window"""
        return await self.capture_screen()
    
    async def capture_active_window(self) -> bytes:
        """Capture currently active window"""
        return await self.capture_screen()


class OCREngine:
    """Optical Character Recognition"""
    
    def __init__(self):
        self.logger = logging.getLogger("OCREngine")
        self._ocr = None
    
    def _init_ocr(self):
        """Initialize OCR engine"""
        if self._ocr is not None:
            return
        
        try:
            import pytesseract
            self._ocr = pytesseract
        except ImportError:
            try:
                import easyocr
                self._ocr = easyocr.Reader(['en'])
            except ImportError:
                self.logger.warning("No OCR library available")
    
    async def extract_text(self, image_data: bytes) -> List[DetectedText]:
        """Extract text from image"""
        self._init_ocr()
        
        results = []
        
        if self._ocr is None:
            return results
        
        try:
            from PIL import Image
            import io
            
            image = Image.open(io.BytesIO(image_data))
            
            try:
                import pytesseract
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                
                for i in range(len(data['text'])):
                    if data['text'][i].strip():
                        text = data['text'][i]
                        conf = float(data['conf'][i]) / 100.0 if data['conf'][i] != '-1' else 0.5
                        bbox = BoundingBox(
                            x=data['left'][i],
                            y=data['top'][i],
                            width=data['width'][i],
                            height=data['height'][i],
                        )
                        
                        results.append(DetectedText(
                            text=text,
                            confidence=conf,
                            bbox=bbox,
                        ))
                        
            except Exception as e:
                self.logger.error(f"OCR error: {e}")
                
        except Exception as e:
            self.logger.error(f"Image processing error: {e}")
        
        return results
    
    async def find_text(self, image_data: bytes, search_text: str) -> List[DetectedText]:
        """Find specific text in image"""
        all_text = await self.extract_text(image_data)
        
        search_lower = search_text.lower()
        
        return [
            t for t in all_text
            if search_lower in t.text.lower()
        ]


class UIDetector:
    """Detect UI elements on screen"""
    
    UI_ELEMENT_TYPES = [
        "button", "input", "link", "image", "text", "icon",
        "menu", "checkbox", "radio", "dropdown", "modal", "panel"
    ]
    
    def __init__(self):
        self.logger = logging.getLogger("UIDetector")
    
    async def detect_elements(self, image_data: bytes) -> List[UIElement]:
        """Detect UI elements in image"""
        elements = []
        
        try:
            ocr = OCREngine()
            texts = await ocr.extract_text(image_data)
            
            for text in texts:
                element_type = self._classify_element(text.text)
                
                elements.append(UIElement(
                    element_type=element_type,
                    text=text.text,
                    bbox=text.bbox,
                    is_clickable=self._is_clickable(element_type, text.text),
                ))
                
        except Exception as e:
            self.logger.error(f"UI detection error: {e}")
        
        return elements
    
    def _classify_element(self, text: str) -> str:
        """Classify UI element type from text"""
        text_lower = text.lower()
        
        if any(kw in text_lower for kw in ["click", "submit", "save", "cancel", "ok", "yes", "no"]):
            return "button"
        
        if any(kw in text_lower for kw in ["enter", "input", "type", "search"]):
            return "input"
        
        if "http" in text_lower or "www" in text_lower:
            return "link"
        
        return "text"
    
    def _is_clickable(self, element_type: str, text: str) -> bool:
        """Determine if element is clickable"""
        return element_type in ["button", "link", "checkbox", "radio"]
    
    async def find_element(
        self,
        image_data: bytes,
        element_type: str = None,
        text: str = None,
    ) -> Optional[UIElement]:
        """Find specific UI element"""
        elements = await self.detect_elements(image_data)
        
        for element in elements:
            if element_type and element.element_type != element_type:
                continue
            
            if text and text.lower() not in element.text.lower():
                continue
            
            return element
        
        return None


class FaceDetector:
    """Detect faces and expressions"""
    
    def __init__(self):
        self.logger = logging.getLogger("FaceDetector")
        self._cascade = None
    
    def _init_detector(self):
        """Initialize face detector"""
        if self._cascade is not None:
            return
        
        try:
            import cv2
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self._cascade = cv2.CascadeClassifier(cascade_path)
        except ImportError:
            self.logger.warning("OpenCV not available")
    
    async def detect_faces(self, image_data: bytes) -> List[DetectedFace]:
        """Detect faces in image"""
        self._init_detector()
        
        faces = []
        
        if self._cascade is None:
            return faces
        
        try:
            import cv2
            import numpy as np
            
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return faces
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            detected = self._cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
            )
            
            for (x, y, w, h) in detected:
                face = DetectedFace(
                    bbox=BoundingBox(x=x, y=y, width=w, height=h),
                    confidence=0.9,
                )
                faces.append(face)
                
        except Exception as e:
            self.logger.error(f"Face detection error: {e}")
        
        return faces


class GestureRecognizer:
    """Recognize hand gestures"""
    
    GESTURES = {
        "thumbs_up": "👍",
        "thumbs_down": "👎",
        "peace": "✌️",
        "fist": "✊",
        "open_hand": "🖐️",
        "pointing": "👆",
    }
    
    def __init__(self):
        self.logger = logging.getLogger("GestureRecognizer")
    
    async def detect_gesture(self, image_data: bytes) -> GestureResult:
        """Detect hand gesture in image"""
        return GestureResult(
            gesture="unknown",
            confidence=0.0,
        )
    
    def get_gesture_command(self, gesture: str) -> str:
        """Map gesture to command"""
        gesture_commands = {
            "thumbs_up": "confirm",
            "thumbs_down": "cancel",
            "peace": "pause",
            "fist": "stop",
            "open_hand": "start",
            "pointing": "select",
        }
        
        return gesture_commands.get(gesture, "")


class EnhancedVisionSystem:
    """Enhanced computer vision system"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("EnhancedVisionSystem")
        
        self.screen_capture = ScreenCapture()
        self.ocr_engine = OCREngine()
        self.ui_detector = UIDetector()
        self.face_detector = FaceDetector()
        self.gesture_recognizer = GestureRecognizer()
    
    async def initialize(self) -> bool:
        """Initialize the vision system"""
        self.logger.info("Enhanced Vision System initialized")
        return True
    
    async def analyze_screen(self) -> Dict[str, Any]:
        """Full screen analysis"""
        image = await self.screen_capture.capture_screen()
        
        texts = await self.ocr_engine.extract_text(image)
        elements = await self.ui_detector.detect_elements(image)
        
        return {
            "texts": [t.to_dict() for t in texts],
            "elements": [e.to_dict() for e in elements],
            "screen_text": " ".join(t.text for t in texts),
        }
    
    async def find_text_on_screen(self, text: str) -> Optional[BoundingBox]:
        """Find text on screen"""
        image = await self.screen_capture.capture_screen()
        found = await self.ocr_engine.find_text(image, text)
        
        if found:
            return found[0].bbox
        
        return None
    
    async def find_element(
        self,
        element_type: str = None,
        text: str = None,
    ) -> Optional[UIElement]:
        """Find UI element on screen"""
        image = await self.screen_capture.capture_screen()
        return await self.ui_detector.find_element(image, element_type, text)
    
    async def click_element(self, element: UIElement) -> bool:
        """Click on a detected element"""
        if not element.is_clickable:
            return False
        
        center = element.bbox.center
        
        import pyautogui
        pyautogui.click(center[0], center[1])
        
        return True
    
    async def type_text(self, text: str):
        """Type text using automation"""
        import pyautogui
        pyautogui.write(text)
    
    async def read_screen_text(self) -> str:
        """Read all visible text on screen"""
        image = await self.screen_capture.capture_screen()
        texts = await self.ocr_engine.extract_text(image)
        
        return " ".join(t.text for t in texts)
    
    async def detect_faces(self) -> List[DetectedFace]:
        """Detect faces in current view"""
        image = await self.screen_capture.capture_screen()
        return await self.face_detector.detect_faces(image)
    
    async def take_screenshot(self, save_path: str = None) -> bytes:
        """Take a screenshot"""
        image = await self.screen_capture.capture_screen()
        
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(image)
        
        return image
    
    async def search_screen(
        self,
        query: str,
        search_type: str = "text",
    ) -> List[Dict[str, Any]]:
        """Search screen for content"""
        results = []
        
        if search_type == "text":
            image = await self.screen_capture.capture_screen()
            found = await self.ocr_engine.find_text(image, query)
            results = [t.to_dict() for t in found]
        
        elif search_type == "element":
            element = await self.find_element(text=query)
            if element:
                results.append(element.to_dict())
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vision system stats"""
        return {
            "ocr_available": self.ocr_engine._ocr is not None,
            "face_detection_available": self.face_detector._cascade is not None,
        }
