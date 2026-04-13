import cv2
import numpy as np
import pyautogui
import logging
from PIL import Image
import io
import base64
import time
from typing import Dict, List, Tuple, Optional

class OpenClawVision:
    """
    Advanced screen vision system inspired by OpenClaw capabilities.
    Provides real-time screen analysis, object detection, and UI automation.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("OpenClawVision")
        self.screen_cache = {}
        self.vision_history = []
        self.max_history = 100
        
    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """Capture screen with optional region parameter."""
        try:
            screenshot = pyautogui.screenshot(region=region)
            return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        except Exception as e:
            self.logger.error(f"Screen capture failed: {e}")
            return np.zeros((480, 640, 3), dtype=np.uint8)
    
    def analyze_screen_realtime(self) -> Dict:
        """Real-time screen analysis with OpenClaw-level intelligence."""
        screen = self.capture_screen()
        
        analysis = {
            "timestamp": time.time(),
            "resolution": screen.shape[:2],
            "color_analysis": self._analyze_colors(screen),
            "ui_elements": self._detect_ui_elements(screen),
            "text_regions": self._detect_text_regions(screen),
            "active_windows": self._detect_window_regions(screen),
            "anomalies": self._detect_anomalies(screen),
            "automation_opportunities": self._find_automation_targets(screen)
        }
        
        # Cache for comparison
        self._update_cache(analysis)
        return analysis
    
    def _analyze_colors(self, screen: np.ndarray) -> Dict:
        """Advanced color analysis for UI theme detection."""
        # Convert to different color spaces
        hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(screen, cv2.COLOR_BGR2LAB)
        
        # Calculate color statistics
        mean_color = np.mean(screen, axis=(0,1))
        std_color = np.std(screen, axis=(0,1))
        
        # Dominant colors
        pixels = screen.reshape(-1, 3)
        unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)
        top_colors = unique_colors[np.argsort(counts)[-5:]]
        
        return {
            "mean_bgr": mean_color.tolist(),
            "std_bgr": std_color.tolist(),
            "dominant_colors": top_colors.tolist(),
            "brightness": np.mean(lab[:,:,0]),
            "contrast": np.std(lab[:,:,0]),
            "theme": self._classify_theme(mean_color)
        }
    
    def _detect_ui_elements(self, screen: np.ndarray) -> List[Dict]:
        """Detect buttons, input fields, and interactive elements."""
        # Convert to grayscale
        gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        
        # Edge detection for UI boundaries
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        ui_elements = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 100:  # Filter small noise
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                
                # Classify element type
                element_type = self._classify_ui_element(w, h, aspect_ratio, area)
                
                ui_elements.append({
                    "type": element_type,
                    "bbox": [x, y, w, h],
                    "area": area,
                    "aspect_ratio": aspect_ratio,
                    "confidence": self._calculate_element_confidence(contour)
                })
        
        return ui_elements
    
    def _detect_text_regions(self, screen: np.ndarray) -> List[Dict]:
        """Detect text regions using MSER (Maximally Stable Extremal Regions)."""
        gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        
        # MSER for text detection
        mser = cv2.MSER_create()
        regions, _ = mser.detectRegions(gray)
        
        text_regions = []
        for region in regions:
            x, y, w, h = cv2.boundingRect(region)
            
            # Filter by aspect ratio and size (text characteristics)
            if 0.2 < w/h < 5 and w > 10 and h > 8:
                text_regions.append({
                    "bbox": [x, y, w, h],
                    "area": w * h,
                    "type": "text_region"
                })
        
        return text_regions
    
    def _detect_window_regions(self, screen: np.ndarray) -> List[Dict]:
        """Detect window-like rectangular regions."""
        gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        
        # Use morphological operations to find rectangular regions
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        morph = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        
        # Find rectangular contours
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        windows = []
        for contour in contours:
            approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
            
            if len(approx) == 4:  # Rectangle
                x, y, w, h = cv2.boundingRect(approx)
                area = w * h
                
                if area > 1000:  # Reasonable window size
                    windows.append({
                        "bbox": [x, y, w, h],
                        "area": area,
                        "type": "window",
                        "corners": len(approx)
                    })
        
        return windows
    
    def _detect_anomalies(self, screen: np.ndarray) -> List[Dict]:
        """Detect unusual patterns or anomalies on screen."""
        gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        
        # Calculate local binary patterns
        lbp = self._local_binary_pattern(gray)
        
        # Find statistical anomalies
        mean_intensity = np.mean(gray)
        std_intensity = np.std(gray)
        
        anomalies = []
        
        # Detect sudden brightness changes
        if abs(mean_intensity - 128) > 50:
            anomalies.append({
                "type": "brightness_anomaly",
                "severity": abs(mean_intensity - 128) / 128,
                "description": f"Unusual brightness: {mean_intensity:.1f}"
            })
        
        # Detect high contrast regions (possible errors/alerts)
        if std_intensity > 60:
            anomalies.append({
                "type": "contrast_anomaly",
                "severity": std_intensity / 100,
                "description": f"High contrast detected: {std_intensity:.1f}"
            })
        
        return anomalies
    
    def _find_automation_targets(self, screen: np.ndarray) -> List[Dict]:
        """Find potential automation targets (buttons, inputs, etc.)."""
        ui_elements = self._detect_ui_elements(screen)
        text_regions = self._detect_text_regions(screen)
        
        targets = []
        
        # Combine UI elements and text regions
        for element in ui_elements:
            if element["confidence"] > 0.7:  # High confidence targets
                targets.append({
                    "type": "clickable_element",
                    "bbox": element["bbox"],
                    "confidence": element["confidence"],
                    "element_type": element["type"]
                })
        
        # Add text input areas
        for text_region in text_regions:
            if text_region["area"] > 200:  # Reasonable text area
                targets.append({
                    "type": "text_input",
                    "bbox": text_region["bbox"],
                    "confidence": 0.8
                })
        
        return targets
    
    def _classify_theme(self, mean_color: np.ndarray) -> str:
        """Classify UI theme based on dominant colors."""
        b, g, r = mean_color
        
        if r > g and r > b:
            return "red_theme"
        elif g > r and g > b:
            return "green_theme"
        elif b > r and b > g:
            return "blue_theme"
        elif np.mean([r, g, b]) < 50:
            return "dark_theme"
        else:
            return "light_theme"
    
    def _classify_ui_element(self, width: int, height: int, aspect_ratio: float, area: float) -> str:
        """Classify UI element type based on geometric properties."""
        if 0.8 < aspect_ratio < 1.2 and area > 500:
            return "button"
        elif aspect_ratio > 3 and height < 30:
            return "text_input"
        elif aspect_ratio > 2 and area > 1000:
            return "window"
        elif area > 2000:
            return "panel"
        else:
            return "unknown"
    
    def _calculate_element_confidence(self, contour: np.ndarray) -> float:
        """Calculate confidence score for UI element detection."""
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        
        if perimeter == 0:
            return 0.0
        
        # Calculate shape factor (closer to 1 = more rectangular)
        shape_factor = (4 * np.pi * area) / (perimeter ** 2)
        
        # Calculate convexity
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        convexity = area / hull_area if hull_area > 0 else 0
        
        return (shape_factor + convexity) / 2
    
    def _local_binary_pattern(self, gray: np.ndarray) -> np.ndarray:
        """Calculate Local Binary Pattern for texture analysis."""
        height, width = gray.shape
        lbp = np.zeros_like(gray)
        
        for i in range(1, height-1):
            for j in range(1, width-1):
                center = gray[i, j]
                binary = 0
                
                # 8-neighborhood
                neighbors = [
                    gray[i-1, j-1], gray[i-1, j], gray[i-1, j+1],
                    gray[i, j-1],                 gray[i, j+1],
                    gray[i+1, j-1], gray[i+1, j], gray[i+1, j+1]
                ]
                
                for k, neighbor in enumerate(neighbors):
                    if neighbor >= center:
                        binary += (1 << k)
                
                lbp[i, j] = binary
        
        return lbp
    
    def _update_cache(self, analysis: Dict):
        """Update vision history cache."""
        self.vision_history.append(analysis)
        
        # Keep only recent history
        if len(self.vision_history) > self.max_history:
            self.vision_history.pop(0)
    
    def get_screen_summary(self) -> str:
        """Generate human-readable screen summary."""
        if not self.vision_history:
            return "No screen data available."
        
        latest = self.vision_history[-1]
        
        summary = f"Screen Analysis: {latest['resolution'][1]}x{latest['resolution'][0]} resolution. "
        summary += f"Theme: {latest['color_analysis']['theme']}. "
        summary += f"Detected {len(latest['ui_elements'])} UI elements, "
        summary += f"{len(latest['text_regions'])} text regions, "
        summary += f"{len(latest['active_windows'])} active windows. "
        
        if latest['anomalies']:
            summary += f"Found {len(latest['anomalies'])} anomalies. "
        
        if latest['automation_opportunities']:
            summary += f"{len(latest['automation_opportunities'])} automation targets available."
        
        return summary
    
    def export_vision_data(self, format: str = "json") -> str:
        """Export vision analysis data in various formats."""
        if format == "json":
            import json
            return json.dumps(self.vision_history, indent=2)
        elif format == "csv":
            import csv
            output = io.StringIO()
            if self.vision_history:
                writer = csv.DictWriter(output, fieldnames=self.vision_history[0].keys())
                writer.writeheader()
                writer.writerows(self.vision_history)
            return output.getvalue()
        else:
            return str(self.vision_history)

# Global instance for easy access
vision_engine = OpenClawVision()

def analyze_screen() -> str:
    """Quick screen analysis function for integration."""
    try:
        analysis = vision_engine.analyze_screen_realtime()
        return vision_engine.get_screen_summary()
    except Exception as e:
        return f"Vision analysis error: {str(e)}"