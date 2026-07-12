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
    """A poly-line following one body, stored in world coordinates.

    Each point remembers the body's speed there, so the trail can be brightened
    where the body moves fast (more kinetic energy). Older segments fade toward
    the background unless ``fade`` is off (the "trace" mode that keeps the whole
    orbit).
    """

    def __init__(self, maxlen: int = 350) -> None:
        self.points: deque[tuple[Vec2, float]] = deque(maxlen=maxlen)
        self.max_speed = 1e-9

    def clear(self) -> None:
        self.points.clear()
        self.max_speed = 1e-9

    def add(self, world_pos: Vec2, speed: float = 0.0) -> None:
        self.points.append((world_pos.copy(), speed))
        if speed > self.max_speed:
            self.max_speed = speed

    def draw(
        self,
        surface: pygame.Surface,
        camera: Camera,
        color: tuple[int, int, int],
        *,
        fade: bool = True,
        dim: float = 1.0,
    ) -> None:
        n = len(self.points)
        if n < 2:
            return
        pts = [(camera.to_screen(p), s) for p, s in self.points]
        inv_max = 1.0 / self.max_speed
        for k in range(1, n):
            age = k / n if fade else 1.0
            speed = 0.35 + 0.65 * min(1.0, pts[k][1] * inv_max)  # brighter when fast
            f = age * speed * dim
            faded = (int(color[0] * f), int(color[1] * f), int(color[2] * f))
            pygame.draw.aaline(surface, faded, pts[k - 1][0], pts[k][0])


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


def draw_sparkline(
    surface: pygame.Surface,
    rect: pygame.Rect,
    values: list[float],
    color: tuple[int, int, int],
    rel_floor: float = 0.02,
) -> None:
    """A small line graph of ``values`` inside ``rect``.

    The vertical scale never shrinks below ``rel_floor`` of the value's magnitude,
    so a *conserved* quantity draws as a near-flat line instead of amplified noise.
    """
    bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    bg.fill((255, 255, 255, 12))
    surface.blit(bg, (rect.x, rect.y))
    pygame.draw.rect(surface, (70, 74, 84), rect, 1)
    n = len(values)
    if n < 2:
        return
    lo, hi = min(values), max(values)
    mid = (lo + hi) / 2
    half = max((hi - lo) / 2, rel_floor * (abs(mid) + 1e-12))
    pad = 4.0
    top, bot = rect.y + 1, rect.bottom - 1
    pts = []
    for i, v in enumerate(values):
        x = rect.x + pad + (rect.width - 2 * pad) * i / (n - 1)
        y = rect.y + rect.height / 2 - (v - mid) / half * (rect.height / 2 - pad)
        pts.append((x, max(top, min(bot, y))))
    pygame.draw.aalines(surface, color, False, pts)


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
