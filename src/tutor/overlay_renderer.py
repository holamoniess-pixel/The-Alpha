#!/usr/bin/env python3
"""
ALPHA OMEGA - TUTOR VISUAL OVERLAY
Display green cursor and highlight overlays
Version: 2.0.0
"""

import asyncio
import logging
import math
import time
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
import threading


@dataclass
class OverlayConfig:
    cursor_color: str = "#00FF00"
    cursor_size: int = 20
    glow_radius: int = 30
    glow_color: str = "#00FF00"
    glow_alpha: float = 0.3
    trail_length: int = 20
    trail_fade: bool = True
    highlight_color: str = "#00FF00"
    highlight_alpha: float = 0.2
    highlight_border_width: int = 3
    show_labels: bool = True
    label_font_size: int = 14
    label_background: str = "#000000"
    label_text_color: str = "#FFFFFF"


class OverlayRenderer:
    """Render tutor overlay on screen"""

    def __init__(self, config: OverlayConfig = None):
        self.config = config or OverlayConfig()
        self.logger = logging.getLogger("OverlayRenderer")

        self._running = False
        self._window = None
        self._surface = None
        self._last_render_time = 0
        self._fps = 60

        self._cursor_x = 0.0
        self._cursor_y = 0.0
        self._cursor_trail: List[Tuple[float, float]] = []
        self._cursor_state = "idle"
        self._glow_intensity = 0.8
        self._glow_phase = 0.0

        self._highlights: List[Dict[str, Any]] = []
        self._labels: List[Dict[str, Any]] = []
        self._click_effects: List[Dict[str, Any]] = []

    async def start(self) -> bool:
        """Start the overlay renderer"""
        self.logger.info("Starting overlay renderer...")

        self._running = True

        try:
            import tkinter as tk

            self._window = tk.Tk()
            self._window.attributes("-fullscreen", True)
            self._window.attributes("-topmost", True)
            self._window.attributes("-transparentcolor", "#000000")
            self._window.configure(bg="#000000")
            self._window.overrideredirect(True)

            self._canvas = tk.Canvas(
                self._window,
                highlightthickness=0,
                bg="#000000",
            )
            self._canvas.pack(fill=tk.BOTH, expand=True)

            self._window.withdraw()

        except ImportError:
            self.logger.warning("tkinter not available, using alternative renderer")
            await self._start_pygame_renderer()

        return True

    async def _start_pygame_renderer(self):
        """Start pygame-based renderer"""
        try:
            import pygame
            import pygame.gfxdraw

            pygame.init()

            info = pygame.display.Info()
            width = info.current_w
            height = info.current_h

            self._screen = pygame.display.set_mode(
                (width, height),
                pygame.NOFRAME | pygame.SRCALPHA,
            )

            self._pygame_running = True
            pygame.display.set_caption("Alpha Tutor Overlay")

        except ImportError:
            self.logger.warning("pygame not available")
            self._pygame_running = False

    async def stop(self):
        """Stop the overlay renderer"""
        self._running = False

        if self._window:
            self._window.destroy()

    def show(self):
        """Show the overlay"""
        if self._window:
            self._window.deiconify()

    def hide(self):
        """Hide the overlay"""
        if self._window:
            self._window.withdraw()

    def update_cursor(
        self,
        x: float,
        y: float,
        trail: List[Tuple[float, float]] = None,
        state: str = "idle",
        glow_intensity: float = 0.8,
    ):
        """Update tutor cursor position and state"""
        self._cursor_x = x
        self._cursor_y = y
        self._cursor_trail = trail or []
        self._cursor_state = state
        self._glow_intensity = glow_intensity

    def add_highlight(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        label: str = "",
        color: str = None,
    ):
        """Add a highlight area"""
        self._highlights.append(
            {
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "label": label,
                "color": color or self.config.highlight_color,
                "alpha": self.config.highlight_alpha,
            }
        )

    def clear_highlights(self):
        """Clear all highlights"""
        self._highlights.clear()

    def add_click_effect(self, x: float, y: float):
        """Add click ripple effect"""
        self._click_effects.append(
            {
                "x": x,
                "y": y,
                "radius": 10,
                "max_radius": 60,
                "alpha": 1.0,
                "start_time": time.time(),
            }
        )

    def add_label(
        self,
        x: float,
        y: float,
        text: str,
        arrow_target: Tuple[float, float] = None,
    ):
        """Add a text label"""
        self._labels.append(
            {
                "x": x,
                "y": y,
                "text": text,
                "arrow_target": arrow_target,
            }
        )

    def clear_labels(self):
        """Clear all labels"""
        self._labels.clear()

    async def render_loop(self):
        """Main render loop"""
        while self._running:
            try:
                await self._render_frame()
                await asyncio.sleep(1.0 / self._fps)
            except Exception as e:
                self.logger.error(f"Render error: {e}")
                await asyncio.sleep(0.1)

    async def _render_frame(self):
        """Render a single frame"""
        if not self._window:
            return

        self._canvas.delete("all")

        for highlight in self._highlights:
            self._draw_highlight(highlight)

        self._draw_trail()

        self._draw_cursor()

        for click in self._click_effects:
            self._draw_click_effect(click)

        for label in self._labels:
            self._draw_label(label)

        self._update_click_effects()

        self._window.update()

    def _draw_cursor(self):
        """Draw the tutor cursor"""
        x = int(self._cursor_x)
        y = int(self._cursor_y)

        glow_radius = int(self.config.glow_radius * self._glow_intensity)

        for r in range(glow_radius, 0, -3):
            alpha = int(255 * (1 - r / glow_radius) * self._glow_intensity * 0.5)
            color = self._blend_color(self.config.glow_color, alpha)

            self._canvas.create_oval(
                x - r,
                y - r,
                x + r,
                y + r,
                fill=color,
                outline="",
            )

        size = self.config.cursor_size

        self._canvas.create_polygon(
            x,
            y - size,
            x - size // 2,
            y + size // 2,
            x + size // 2,
            y + size // 2,
            fill=self.config.cursor_color,
            outline="white",
            width=2,
        )

        if self._cursor_state == "waiting":
            self._draw_waiting_indicator(x, y)
        elif self._cursor_state == "clicking":
            self._draw_click_indicator(x, y)

    def _draw_trail(self):
        """Draw cursor trail"""
        if not self._cursor_trail or not self.config.trail_fade:
            return

        for i, (x, y) in enumerate(self._cursor_trail):
            alpha = (i + 1) / len(self._cursor_trail) * 0.5

            color = self._blend_color(self.config.cursor_color, int(255 * alpha))

            size = int(
                self.config.cursor_size * 0.5 * (i + 1) / len(self._cursor_trail)
            )

            self._canvas.create_oval(
                int(x - size),
                int(y - size),
                int(x + size),
                int(y + size),
                fill=color,
                outline="",
            )

    def _draw_highlight(self, highlight: Dict[str, Any]):
        """Draw a highlight area"""
        x, y = int(highlight["x"]), int(highlight["y"])
        w, h = int(highlight["width"]), int(highlight["height"])
        color = highlight["color"]

        self._canvas.create_rectangle(
            x,
            y,
            x + w,
            y + h,
            fill="",
            outline=color,
            width=self.config.highlight_border_width,
        )

        pulse = (math.sin(time.time() * 3) + 1) / 2
        for i in range(3):
            offset = int(5 * (i + 1) * pulse)
            alpha = int(100 * (1 - i / 3))
            pulse_color = self._blend_color(color, alpha)

            self._canvas.create_rectangle(
                x - offset,
                y - offset,
                x + w + offset,
                y + h + offset,
                fill="",
                outline=pulse_color,
                width=2,
            )

        if highlight["label"] and self.config.show_labels:
            self._draw_highlight_label(
                x,
                y - 30,
                highlight["label"],
                color,
            )

    def _draw_highlight_label(self, x: int, y: int, text: str, color: str):
        """Draw label for highlight"""
        padding = 8

        self._canvas.create_text(
            x + padding,
            y,
            text=text,
            anchor="w",
            fill="white",
            font=("Arial", self.config.label_font_size, "bold"),
        )

        text_bbox = self._canvas.bbox(self._canvas.create_text(0, 0, text=text))
        if text_bbox:
            tw = text_bbox[2] - text_bbox[0] + padding * 2
            th = text_bbox[3] - text_bbox[1] + padding

            self._canvas.create_rectangle(
                x,
                y - th // 2,
                x + tw,
                y + th // 2,
                fill=color,
                outline="",
            )

            self._canvas.create_text(
                x + padding,
                y,
                text=text,
                anchor="w",
                fill="white",
                font=("Arial", self.config.label_font_size, "bold"),
            )

    def _draw_click_effect(self, click: Dict[str, Any]):
        """Draw click ripple effect"""
        x, y = int(click["x"]), int(click["y"])
        radius = int(click["radius"])
        alpha = click["alpha"]

        color = self._blend_color(self.config.glow_color, int(255 * alpha))

        self._canvas.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill="",
            outline=color,
            width=3,
        )

    def _draw_waiting_indicator(self, x: int, y: int):
        """Draw waiting animation"""
        angle = time.time() * 2

        for i in range(3):
            a = angle + i * (2 * math.pi / 3)
            dx = int(20 * math.cos(a))
            dy = int(20 * math.sin(a))

            self._canvas.create_oval(
                x + dx - 4,
                y + dy - 4,
                x + dx + 4,
                y + dy + 4,
                fill=self.config.cursor_color,
                outline="",
            )

    def _draw_click_indicator(self, x: int, y: int):
        """Draw click animation"""
        self._canvas.create_oval(
            x - 25,
            y - 25,
            x + 25,
            y + 25,
            fill="",
            outline="white",
            width=3,
        )

    def _draw_label(self, label: Dict[str, Any]):
        """Draw a text label with optional arrow"""
        x, y = int(label["x"]), int(label["y"])
        text = label["text"]

        self._canvas.create_rectangle(
            x - 5,
            y - 15,
            x + len(text) * 8 + 10,
            y + 20,
            fill="#000000",
            outline=self.config.cursor_color,
        )

        self._canvas.create_text(
            x,
            y,
            text=text,
            anchor="w",
            fill="white",
            font=("Arial", 12),
        )

        if label["arrow_target"]:
            tx, ty = label["arrow_target"]
            self._canvas.create_line(
                x,
                y + 20,
                tx,
                ty,
                fill=self.config.cursor_color,
                width=2,
                arrow="last",
            )

    def _update_click_effects(self):
        """Update click effect animations"""
        now = time.time()
        updated = []

        for click in self._click_effects:
            elapsed = now - click["start_time"]

            if elapsed < 0.5:
                progress = elapsed / 0.5
                click["radius"] = 10 + (click["max_radius"] - 10) * progress
                click["alpha"] = 1.0 - progress
                updated.append(click)

        self._click_effects = updated

    def _blend_color(self, hex_color: str, alpha: int) -> str:
        """Blend color with alpha (simplified)"""
        if alpha >= 255:
            return hex_color

        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)

        return f"#{r:02x}{g:02x}{b:02x}"


class TutorOverlayManager:
    """Manage overlay state and rendering"""

    def __init__(self):
        self.logger = logging.getLogger("TutorOverlayManager")
        self.renderer = OverlayRenderer()
        self._running = False

    async def start(self) -> bool:
        """Start overlay manager"""
        self.logger.info("Starting Tutor Overlay Manager...")

        success = await self.renderer.start()
        if success:
            self._running = True
            asyncio.create_task(self.renderer.render_loop())

        return success

    async def show_tutor_cursor(
        self,
        x: float,
        y: float,
        trail: List[Tuple[float, float]] = None,
        state: str = "idle",
    ):
        """Show tutor cursor at position"""
        self.renderer.update_cursor(x, y, trail, state)
        self.renderer.show()

    async def highlight_element(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        label: str = "",
    ):
        """Highlight a UI element"""
        self.renderer.clear_highlights()
        self.renderer.add_highlight(x, y, width, height, label)
        self.renderer.show()

    async def show_instruction(
        self,
        text: str,
        position: Tuple[float, float] = None,
        arrow_to: Tuple[float, float] = None,
    ):
        """Show instruction text"""
        self.renderer.clear_labels()
        self.renderer.add_label(
            position[0] if position else 100,
            position[1] if position else 50,
            text,
            arrow_to,
        )
        self.renderer.show()

    async def show_click_animation(self, x: float, y: float):
        """Show click ripple animation"""
        self.renderer.add_click_effect(x, y)

    async def clear_all(self):
        """Clear all overlay elements"""
        self.renderer.clear_highlights()
        self.renderer.clear_labels()

    async def hide(self):
        """Hide the overlay"""
        self.renderer.hide()

    async def show(self):
        """Show the overlay"""
        self.renderer.show()

    async def stop(self):
        """Stop overlay manager"""
        self._running = False
        await self.renderer.stop()
