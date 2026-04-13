#!/usr/bin/env python3
"""
ALPHA OMEGA - VISION SYSTEM
Real-time Screen Analysis, UI Detection, and Computer Vision
Version: 2.0.0
"""

import asyncio
import logging
import time
import threading
import base64
import io
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque

try:
    import cv2
    import numpy as np

    HAS_CV = True
except ImportError:
    HAS_CV = False
    logging.warning("OpenCV not available")

try:
    import pyautogui
    from PIL import Image

    HAS_GUI = True
except ImportError:
    HAS_GUI = False
    logging.warning("GUI automation not available")


@dataclass
class UIElement:
    element_type: str
    bbox: Tuple[int, int, int, int]
    confidence: float
    area: int
    center: Tuple[int, int]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.element_type,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "area": self.area,
            "center": self.center,
            "metadata": self.metadata,
        }


@dataclass
class ScreenAnalysis:
    timestamp: float
    resolution: Tuple[int, int]
    color_analysis: Dict[str, Any]
    ui_elements: List[UIElement]
    text_regions: List[Dict[str, Any]]
    windows: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]
    automation_targets: List[Dict[str, Any]]
    theme: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "resolution": self.resolution,
            "color_analysis": self.color_analysis,
            "ui_elements": [e.to_dict() for e in self.ui_elements],
            "text_regions": self.text_regions,
            "windows": self.windows,
            "anomalies": self.anomalies,
            "automation_targets": self.automation_targets,
            "theme": self.theme,
        }


class ScreenCapture:
    def __init__(self):
        self.logger = logging.getLogger("ScreenCapture")
        self._last_capture = None
        self._capture_time = 0

    def capture(self, region: Tuple[int, int, int, int] = None) -> "np.ndarray":
        if not HAS_GUI:
            return None

        try:
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()

            img_array = np.array(screenshot)

            if HAS_CV:
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            else:
                img_bgr = img_array

            self._last_capture = img_bgr
            self._capture_time = time.time()

            return img_bgr
        except Exception as e:
            self.logger.error(f"Screen capture failed: {e}")
            return None

    def capture_region(self, x: int, y: int, width: int, height: int) -> "np.ndarray":
        return self.capture((x, y, width, height))

    def get_last_capture(self) -> Tuple["np.ndarray", float]:
        return self._last_capture, self._capture_time


class ColorAnalyzer:
    def analyze(self, image: "np.ndarray") -> Dict[str, Any]:
        if not HAS_CV or image is None:
            return {}

        try:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

            mean_color = np.mean(image, axis=(0, 1))
            std_color = np.std(image, axis=(0, 1))

            pixels = image.reshape(-1, 3)

            unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)
            top_indices = np.argsort(counts)[-5:][::-1]
            dominant_colors = unique_colors[top_indices].tolist()
            dominant_counts = counts[top_indices].tolist()

            brightness = np.mean(lab[:, :, 0])
            contrast = np.std(lab[:, :, 0])

            theme = self._classify_theme(mean_color)

            return {
                "mean_bgr": mean_color.tolist(),
                "std_bgr": std_color.tolist(),
                "dominant_colors": dominant_colors,
                "dominant_counts": dominant_counts,
                "brightness": float(brightness),
                "contrast": float(contrast),
                "theme": theme,
                "saturation": float(np.mean(hsv[:, :, 1])),
            }
        except Exception as e:
            return {"error": str(e)}

    def _classify_theme(self, mean_color: "np.ndarray") -> str:
        b, g, r = mean_color

        if np.mean([r, g, b]) < 50:
            return "dark"
        elif np.mean([r, g, b]) > 200:
            return "light"
        elif r > g and r > b:
            return "red_tint"
        elif g > r and g > b:
            return "green_tint"
        elif b > r and b > g:
            return "blue_tint"
        else:
            return "neutral"


class UIElementDetector:
    def __init__(self):
        self.min_area = 100
        self.max_area = 500000

    def detect(self, image: "np.ndarray") -> List[UIElement]:
        if not HAS_CV or image is None:
            return []

        elements = []

        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            edges = cv2.Canny(gray, 50, 150)

            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            for contour in contours:
                area = cv2.contourArea(contour)

                if area < self.min_area or area > self.max_area:
                    continue

                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0

                element_type = self._classify_element(w, h, aspect_ratio, area)

                confidence = self._calculate_confidence(contour)

                if confidence > 0.3:
                    elements.append(
                        UIElement(
                            element_type=element_type,
                            bbox=(int(x), int(y), int(w), int(h)),
                            confidence=confidence,
                            area=int(area),
                            center=(int(x + w / 2), int(y + h / 2)),
                        )
                    )

            return elements
        except Exception as e:
            return []

    def _classify_element(
        self, width: int, height: int, aspect_ratio: float, area: int
    ) -> str:
        if 0.8 < aspect_ratio < 1.2 and area > 500:
            return "button"
        elif aspect_ratio > 3 and height < 40:
            return "input"
        elif aspect_ratio > 2 and area > 10000:
            return "panel"
        elif area > 50000:
            return "window"
        elif aspect_ratio < 0.5:
            return "vertical_bar"
        elif aspect_ratio > 5:
            return "horizontal_bar"
        else:
            return "unknown"

    def _calculate_confidence(self, contour: "np.ndarray") -> float:
        try:
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)

            if perimeter == 0:
                return 0.0

            circularity = (4 * np.pi * area) / (perimeter**2)

            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            convexity = area / hull_area if hull_area > 0 else 0

            return (circularity + convexity) / 2
        except:
            return 0.0


class TextRegionDetector:
    def detect(self, image: "np.ndarray") -> List[Dict[str, Any]]:
        if not HAS_CV or image is None:
            return []

        regions = []

        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            mser = cv2.MSER_create()
            msers, _ = mser.detectRegions(gray)

            for mser in msers:
                x, y, w, h = cv2.boundingRect(mser)

                if w > 10 and h > 8:
                    aspect_ratio = w / h if h > 0 else 0

                    if 0.1 < aspect_ratio < 20:
                        regions.append(
                            {
                                "bbox": (int(x), int(y), int(w), int(h)),
                                "area": int(w * h),
                                "type": "text_region",
                            }
                        )

            return regions
        except Exception as e:
            return []


class AnomalyDetector:
    def detect(self, image: "np.ndarray") -> List[Dict[str, Any]]:
        if not HAS_CV or image is None:
            return []

        anomalies = []

        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            mean_intensity = np.mean(gray)
            std_intensity = np.std(gray)

            if abs(mean_intensity - 128) > 50:
                anomalies.append(
                    {
                        "type": "brightness_anomaly",
                        "severity": min(abs(mean_intensity - 128) / 128, 1.0),
                        "description": f"Unusual brightness: {mean_intensity:.1f}",
                    }
                )

            if std_intensity > 60:
                anomalies.append(
                    {
                        "type": "high_contrast",
                        "severity": min(std_intensity / 100, 1.0),
                        "description": f"High contrast detected: {std_intensity:.1f}",
                    }
                )

            red_channel = image[:, :, 2]
            red_ratio = np.mean(red_channel) / (np.mean(image) + 1e-6)
            if red_ratio > 1.5:
                anomalies.append(
                    {
                        "type": "red_dominance",
                        "severity": min(red_ratio / 2, 1.0),
                        "description": "Possible error/alert state",
                    }
                )

            return anomalies
        except:
            return []


class AutomationTargetFinder:
    def find_targets(
        self, image: "np.ndarray", ui_elements: List[UIElement]
    ) -> List[Dict[str, Any]]:
        targets = []

        for element in ui_elements:
            if element.confidence > 0.5:
                if element.element_type in ["button", "input"]:
                    targets.append(
                        {
                            "type": "clickable",
                            "element_type": element.element_type,
                            "bbox": element.bbox,
                            "center": element.center,
                            "confidence": element.confidence,
                        }
                    )

        return targets


class VisionSystem:
    def __init__(self, config: Dict[str, Any], memory_system=None):
        self.config = config
        self.memory = memory_system
        self.logger = logging.getLogger("VisionSystem")

        self.screen_capture = ScreenCapture()
        self.color_analyzer = ColorAnalyzer()
        self.ui_detector = UIElementDetector()
        self.text_detector = TextRegionDetector()
        self.anomaly_detector = AnomalyDetector()
        self.target_finder = AutomationTargetFinder()

        self._history: deque = deque(maxlen=100)
        self._running = False
        self._analysis_interval = config.get("analysis_interval", 3.0)

        self._stats = {
            "captures": 0,
            "analyses": 0,
            "elements_detected": 0,
            "anomalies_detected": 0,
        }

    async def initialize(self) -> bool:
        self.logger.info("Initializing Vision System...")

        if not HAS_CV:
            self.logger.warning("OpenCV not available - vision features limited")

        if not HAS_GUI:
            self.logger.warning("GUI automation not available")

        self._running = True
        self.logger.info("Vision System initialized")
        return True

    def capture_screen(
        self, region: Tuple[int, int, int, int] = None
    ) -> Optional["np.ndarray"]:
        return self.screen_capture.capture(region)

    def analyze_screen(self, image: "np.ndarray" = None) -> ScreenAnalysis:
        if image is None:
            image = self.capture_screen()

        if image is None:
            return self._empty_analysis()

        self._stats["captures"] += 1
        self._stats["analyses"] += 1

        try:
            resolution = image.shape[:2]

            color_analysis = self.color_analyzer.analyze(image)

            ui_elements = self.ui_detector.detect(image)
            self._stats["elements_detected"] += len(ui_elements)

            text_regions = self.text_detector.detect(image)

            anomalies = self.anomaly_detector.detect(image)
            self._stats["anomalies_detected"] += len(anomalies)

            automation_targets = self.target_finder.find_targets(image, ui_elements)

            theme = color_analysis.get("theme", "unknown")

            analysis = ScreenAnalysis(
                timestamp=time.time(),
                resolution=(resolution[1], resolution[0]),
                color_analysis=color_analysis,
                ui_elements=ui_elements,
                text_regions=text_regions,
                windows=[],
                anomalies=anomalies,
                automation_targets=automation_targets,
                theme=theme,
            )

            self._history.append(analysis)

            return analysis
        except Exception as e:
            self.logger.error(f"Screen analysis failed: {e}")
            return self._empty_analysis()

    def _empty_analysis(self) -> ScreenAnalysis:
        return ScreenAnalysis(
            timestamp=time.time(),
            resolution=(0, 0),
            color_analysis={},
            ui_elements=[],
            text_regions=[],
            windows=[],
            anomalies=[],
            automation_targets=[],
            theme="unknown",
        )

    def get_automation_targets(self) -> List[Dict[str, Any]]:
        if self._history:
            return self._history[-1].automation_targets
        return []

    def find_element_by_type(self, element_type: str) -> List[UIElement]:
        if not self._history:
            return []

        latest = self._history[-1]
        return [e for e in latest.ui_elements if e.element_type == element_type]

    def get_screen_summary(self) -> str:
        if not self._history:
            return "No screen data available"

        latest = self._history[-1]

        summary = f"Screen {latest.resolution[0]}x{latest.resolution[1]}. "
        summary += f"Theme: {latest.theme}. "
        summary += f"Elements: {len(latest.ui_elements)}. "
        summary += f"Text regions: {len(latest.text_regions)}. "

        if latest.anomalies:
            summary += f"Anomalies: {len(latest.anomalies)}. "

        if latest.automation_targets:
            summary += f"Targets: {len(latest.automation_targets)}."

        return summary

    def encode_image_base64(self, image: "np.ndarray" = None) -> str:
        if image is None:
            image = self.capture_screen()

        if image is None:
            return ""

        try:
            if HAS_CV:
                _, buffer = cv2.imencode(".png", image)
                return base64.b64encode(buffer).decode()
            else:
                return ""
        except:
            return ""

    def get_history(self, limit: int = 10) -> List[ScreenAnalysis]:
        return list(self._history)[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return self._stats

    async def stop(self):
        self._running = False
        self.logger.info("Vision system stopped")
