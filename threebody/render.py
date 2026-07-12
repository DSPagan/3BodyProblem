"""Rendering: camera transform, glowing bodies, fading trails, velocity arrows.

The camera keeps the mathematical convention that +y points *up*, so what you
see on screen matches the physics rather than pixel coordinates.
"""

from __future__ import annotations

import math
from collections import deque

import pygame

from .vec import Vec2

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
        self.center = Vec2(0.0, 0.0)  # world point shown at the screen centre

    def to_screen(self, world: Vec2) -> tuple[float, float]:
        sx = self.width / 2 + self.scale * (world.x - self.center.x)
        sy = self.height / 2 - self.scale * (world.y - self.center.y)  # flip y
        return (sx, sy)

    def to_world(self, screen: tuple[float, float]) -> Vec2:
        wx = (screen[0] - self.width / 2) / self.scale + self.center.x
        wy = -(screen[1] - self.height / 2) / self.scale + self.center.y
        return Vec2(wx, wy)


class Trail:
    """A fading poly-line following one body, stored in world coordinates."""

    def __init__(self, maxlen: int = 350) -> None:
        self.points: deque[Vec2] = deque(maxlen=maxlen)

    def clear(self) -> None:
        self.points.clear()

    def add(self, world_pos: Vec2) -> None:
        self.points.append(world_pos.copy())

    def draw(self, surface: pygame.Surface, camera: Camera, color: tuple[int, int, int]) -> None:
        n = len(self.points)
        if n < 2:
            return
        pts = [camera.to_screen(p) for p in self.points]
        for k in range(1, n):
            # Fade older segments toward the background (brightness fade on dark bg).
            t = k / n
            faded = (int(color[0] * t), int(color[1] * t), int(color[2] * t))
            pygame.draw.aaline(surface, faded, pts[k - 1], pts[k])


def body_radius(mass: float, base: float = 7.0) -> int:
    """Radius grows with the cube root of mass and is clamped to a sane range."""
    return int(max(4.0, min(22.0, base * mass ** (1 / 3))))


def draw_body(
    surface: pygame.Surface,
    center: tuple[float, float],
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
    start: tuple[float, float],
    end: tuple[float, float],
    color: tuple[int, int, int] = ARROW_COLOR,
) -> None:
    """Draw an arrow from ``start`` to ``end`` (both in screen pixels)."""
    if math.hypot(end[0] - start[0], end[1] - start[1]) < 3:
        return
    pygame.draw.aaline(surface, color, start, end)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    head = 10.0
    for da in (math.radians(150), math.radians(-150)):
        wing = (end[0] + head * math.cos(angle + da), end[1] + head * math.sin(angle + da))
        pygame.draw.aaline(surface, color, end, wing)
