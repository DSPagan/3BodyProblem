"""A tiny 2D vector.

The simulator only ever deals with a handful of bodies, so a small pure-Python
vector is more than fast enough — and it keeps the whole project free of any
compiled dependency (numpy), which is what lets it run unchanged in the browser
via WebAssembly.
"""

from __future__ import annotations

import math


class Vec2:
    __slots__ = ("x", "y")

    def __init__(self, x: float, y: float) -> None:
        self.x = float(x)
        self.y = float(y)

    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, s: float) -> Vec2:
        return Vec2(self.x * s, self.y * s)

    __rmul__ = __mul__

    def __truediv__(self, s: float) -> Vec2:
        return Vec2(self.x / s, self.y / s)

    def __neg__(self) -> Vec2:
        return Vec2(-self.x, -self.y)

    def __iter__(self):
        yield self.x
        yield self.y

    def __getitem__(self, i: int) -> float:
        return (self.x, self.y)[i]

    def dot(self, other: Vec2) -> float:
        return self.x * other.x + self.y * other.y

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y

    def copy(self) -> Vec2:
        return Vec2(self.x, self.y)

    def __repr__(self) -> str:
        return f"Vec2({self.x:g}, {self.y:g})"
