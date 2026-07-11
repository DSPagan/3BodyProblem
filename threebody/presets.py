"""Ready-made initial conditions for the simulator.

Each factory returns a :class:`Scenario`: a configured :class:`System` plus a
suggested ``view_scale`` (pixels per simulation unit) and a short description
shown in the HUD.  All presets use ``G = 1`` and, unless noted, equal unit
masses so the numbers stay clean.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .physics import System


@dataclass
class Scenario:
    key: str
    name: str
    description: str
    system: System
    view_scale: float


def figure_eight() -> Scenario:
    """The Chenciner–Montgomery / Moore figure-eight choreography.

    Three equal masses chase each other around a single figure-eight curve.
    A famous stable periodic solution (period ≈ 6.3259); a strong sanity check
    that the integrator behaves, since it should retrace the same loop forever.
    """
    p = np.array([0.97000436, -0.24308753])
    v3 = np.array([-0.93240737, -0.86473146])
    positions = [-p, p, [0.0, 0.0]]
    velocities = [-v3 / 2, -v3 / 2, v3]
    system = System(positions, velocities, [1.0, 1.0, 1.0], G=1.0, softening=0.0)
    return Scenario(
        key="figure_eight",
        name="Figure-Eight",
        description="Chenciner-Montgomery choreography - three equal masses on one orbit",
        system=system,
        view_scale=260.0,
    )


def lagrange_triangle(radius: float = 1.0) -> Scenario:
    """Three equal masses at the corners of a rigidly rotating equilateral triangle.

    A circular central configuration: the tangential speed is derived so gravity
    exactly supplies the centripetal force, ``v = sqrt(G m / (sqrt(3) R))``.
    """
    angles = np.deg2rad([90.0, 210.0, 330.0])
    positions = radius * np.column_stack([np.cos(angles), np.sin(angles)])
    speed = np.sqrt(1.0 / (np.sqrt(3.0) * radius))  # G = m = 1
    tangential = np.column_stack([-np.sin(angles), np.cos(angles)])
    velocities = speed * tangential
    system = System(positions, velocities, [1.0, 1.0, 1.0], G=1.0, softening=0.0)
    return Scenario(
        key="lagrange",
        name="Lagrange Triangle",
        description="Equilateral central configuration rotating as a rigid body",
        system=system,
        view_scale=200.0,
    )


def sun_and_planets() -> Scenario:
    """A heavy central body with two lighter ones on near-circular orbits.

    Hierarchical and visually calm - a nice contrast to the chaotic presets.
    """
    m_sun, m_a, m_b = 50.0, 1.0, 1.0
    r_a, r_b = 1.2, 2.4
    positions = [[0.0, 0.0], [r_a, 0.0], [-r_b, 0.0]]
    v_a = np.sqrt(m_sun / r_a)
    v_b = np.sqrt(m_sun / r_b)
    velocities = [[0.0, 0.0], [0.0, v_a], [0.0, -v_b]]
    system = System(positions, velocities, [m_sun, m_a, m_b], G=1.0, softening=0.05)
    system.recenter_momentum()  # keep the centre of mass fixed on screen
    return Scenario(
        key="sun_planets",
        name="Sun & Planets",
        description="Heavy central mass with two orbiting bodies",
        system=system,
        view_scale=130.0,
    )


def random_cloud(seed: int | None = None) -> Scenario:
    """Three random bodies with zero net momentum - usually chaotic, often fun."""
    rng = np.random.default_rng(seed)
    positions = rng.uniform(-1.5, 1.5, size=(3, 2))
    velocities = rng.uniform(-0.4, 0.4, size=(3, 2))
    masses = rng.uniform(0.8, 1.5, size=3)
    system = System(positions, velocities, masses, G=1.0, softening=0.05)
    system.recenter_momentum()
    return Scenario(
        key="random",
        name="Random",
        description="Three random bodies, zero total momentum",
        system=system,
        view_scale=150.0,
    )


# Ordered so the UI can cycle through them predictably.
PRESETS = {
    "figure_eight": figure_eight,
    "lagrange": lagrange_triangle,
    "sun_planets": sun_and_planets,
    "random": random_cloud,
}
PRESET_ORDER = list(PRESETS)
