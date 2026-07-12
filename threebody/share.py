"""Encode a scenario's initial conditions into a short, URL-safe token.

Lets the browser demo put the current set-up in the page URL so a specific orbit
can be shared with a link. Pure and dependency-free, so it is easy to unit-test.
"""

from __future__ import annotations

import base64
import json

from .physics import System
from .presets import Scenario


def encode(system: System) -> str:
    """Serialise a System's initial conditions to a compact base64url token."""
    data = {
        "g": round(system.G, 6),
        "s": round(system.softening, 6),
        "b": [
            [round(p.x, 6), round(p.y, 6), round(v.x, 6), round(v.y, 6), round(m, 6)]
            for p, v, m in zip(system.pos, system.vel, system.mass, strict=True)
        ],
    }
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode(token: str) -> System:
    """Rebuild a System from a token produced by :func:`encode`."""
    pad = "=" * (-len(token) % 4)
    data = json.loads(base64.urlsafe_b64decode(token + pad))
    bodies = data["b"]
    positions = [(b[0], b[1]) for b in bodies]
    velocities = [(b[2], b[3]) for b in bodies]
    masses = [b[4] for b in bodies]
    return System(
        positions, velocities, masses,
        G=data.get("g", 1.0), softening=data.get("s", 0.0),
    )


def scenario_from_token(token: str) -> Scenario:
    """Decode a token into a ready-to-run :class:`Scenario`."""
    system = decode(token)
    com = system.center_of_mass()
    extent = max((p - com).length() for p in system.pos) or 1.0
    return Scenario(
        key="shared",
        name="Shared orbit",
        description="Loaded from a shared link",
        system=system,
        view_scale=max(40.0, min(320.0, 220.0 / extent)),
    )
