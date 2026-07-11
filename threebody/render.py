"""Rendering: camera transform, glowing bodies, fading trails, velocity arrows.

The camera keeps the mathematical convention that +y points *up*, so what you
see on screen matches the physics rather than pixel coordinates.
"""

from __future__ import annotations

import math
from collections import deque

import numpy as np
import pygame

# A dark, slightly blue background makes the glowing trails pop.
BACKGROUND = (8, 9, 14)
BODY_COLORS = [(255, 92, 108), (80, 214, 160), (95, 160, 255)]
HUD_COLOR = (210, 214, 224)
ARROW_COLOR = (240, 240, 120)


class Camera:
    """Maps world (simulation) coordinates to screen pixels and back."""

    def __init__(self, screen_size: tuple[int, int], scale: float) -> None:
        self.width, self.height = screen_size
        self.scale = scale
        self.center = np.array([0.0, 0.0])  # world point shown at screen centre

    def to_screen(self, world) -> np.ndarray:
        w = np.asarray(world, dtype=float)
        cx, cy = self.width / 2, self.height / 2
        sx = cx + self.scale * (w[..., 0] - self.center[0])
        sy = cy - self.scale * (w[..., 1] - self.center[1])  # flip y
        return np.stack([sx, sy], axis=-1)

    def to_world(self, screen) -> np.ndarray:
        sx, sy = screen
        cx, cy = self.width / 2, self.height / 2
        wx = (sx - cx) / self.scale + self.center[0]
        wy = -(sy - cy) / self.scale + self.center[1]
        return np.array([wx, wy])


class Trail:
    """A fading poly-line following one body, stored in world coordinates."""

    def __init__(self, maxlen: int = 350) -> None:
        self.points: deque[np.ndarray] = deque(maxlen=maxlen)

    def clear(self) -> None:
        self.points.clear()

    def add(self, world_pos: np.ndarray) -> None:
        self.points.append(np.array(world_pos, dtype=float))

    def draw(self, surface: pygame.Surface, camera: Camera, color: tuple[int, int, int]) -> None:
        n = len(self.points)
        if n < 2:
            return
        pts = camera.to_screen(np.array(self.points))
        for k in range(1, n):
            # Fade older segments toward the background (brightness fade on dark bg).
            t = k / n
            faded = tuple(int(c * t) for c in color)
            pygame.draw.aaline(surface, faded, pts[k - 1], pts[k])


def body_radius(mass: float, base: float = 7.0) -> int:
    """Radius grows with the cube root of mass and is clamped to a sane range."""
    return int(max(4.0, min(22.0, base * mass ** (1 / 3))))


def draw_body(
    surface: pygame.Surface,
    center: np.ndarray,
    radius: int,
    color: tuple[int, int, int],
) -> None:
    x, y = int(center[0]), int(center[1])
    # Soft glow: a couple of translucent halos behind the solid core.
    glow = pygame.Surface((radius * 6, radius * 6), pygame.SRCALPHA)
    gx = radius * 3
    for r, alpha in ((radius * 3, 40), (radius * 2, 70)):
        pygame.draw.circle(glow, (*color, alpha), (gx, gx), r)
    surface.blit(glow, (x - gx, y - gx))
    pygame.draw.circle(surface, color, (x, y), radius)
    pygame.draw.circle(surface, (255, 255, 255), (x, y), max(2, radius // 3))


def draw_velocity_arrow(
    surface: pygame.Surface,
    start: np.ndarray,
    end: np.ndarray,
    color: tuple[int, int, int] = ARROW_COLOR,
) -> None:
    """Draw an arrow from ``start`` to ``end`` (both in screen pixels)."""
    start = np.asarray(start, dtype=float)
    end = np.asarray(end, dtype=float)
    if np.hypot(*(end - start)) < 3:
        return
    pygame.draw.aaline(surface, color, start, end)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    head = 10.0
    for da in (math.radians(150), math.radians(-150)):
        wing = (end[0] + head * math.cos(angle + da), end[1] + head * math.sin(angle + da))
        pygame.draw.aaline(surface, color, end, wing)
