"""Physics correctness tests - all run headless, no display or numpy required.

These are the tests that justify the "symplectic" claim: over long runs the
integrator must conserve linear momentum (exactly) and total energy (to a small
drift), and the famous figure-eight orbit must return to its starting point.
"""

from __future__ import annotations

import pytest

from threebody import presets
from threebody.physics import System


def two_body_circular() -> System:
    """Two equal masses on a circular orbit about their common centre.

    For separation d, ``v = sqrt(G m / (2 d))`` gives a circular orbit.
    Here G = m = 1, d = 2  ->  v = 0.5, period = 4*pi.
    """
    return System(
        positions=[(-1.0, 0.0), (1.0, 0.0)],
        velocities=[(0.0, -0.5), (0.0, 0.5)],
        masses=[1.0, 1.0],
        G=1.0,
        softening=0.0,
    )


def sep(system: System, i: int, j: int) -> float:
    return (system.pos[i] - system.pos[j]).length()


def max_component_dev(a, b) -> float:
    return max(max(abs(p.x - q.x), abs(p.y - q.y)) for p, q in zip(a, b, strict=True))


def max_extent_from_com(system: System) -> float:
    c = system.center_of_mass()
    return max(max(abs(p.x - c.x), abs(p.y - c.y)) for p in system.pos)


def test_momentum_conserved_to_machine_precision():
    sys = two_body_circular()
    p0 = sys.momentum()
    for _ in range(5000):
        sys.step(0.005)
    p = sys.momentum()
    assert abs(p.x - p0.x) < 1e-9 and abs(p.y - p0.y) < 1e-9


def test_center_of_mass_stays_put_with_zero_momentum():
    sys = presets.figure_eight().system
    c0 = sys.center_of_mass()
    for _ in range(3000):
        sys.step(0.002)
    c = sys.center_of_mass()
    assert abs(c.x - c0.x) < 1e-8 and abs(c.y - c0.y) < 1e-8


def test_energy_drift_is_small_over_many_orbits():
    from math import pi

    sys = two_body_circular()
    e0 = sys.total_energy()
    steps = round(10 * (4 * pi) / 0.002)  # ten orbits
    for _ in range(steps):
        sys.step(0.002)
    drift = abs(sys.total_energy() - e0) / abs(e0)
    assert drift < 1e-3


def test_two_body_orbit_stays_circular():
    sys = two_body_circular()
    worst = 0.0
    for _ in range(4000):
        sys.step(0.002)
        worst = max(worst, abs(sep(sys, 0, 1) - 2.0))
    assert worst < 0.02


def test_figure_eight_is_periodic():
    sys = presets.figure_eight().system
    start = [p.copy() for p in sys.pos]
    period = 6.32591398  # known period of this choreography (G = m = 1)
    n = 6326
    dt = period / n
    for _ in range(n):
        sys.step(dt)
    assert max_component_dev(sys.pos, start) < 0.05


def test_euler_collinear_stays_rigid():
    sys = presets.euler_collinear().system
    d0 = [sep(sys, i, j) for i, j in ((0, 1), (1, 2), (0, 2))]
    for _ in range(4000):
        sys.step(0.002)
    d1 = [sep(sys, i, j) for i, j in ((0, 1), (1, 2), (0, 2))]
    assert max(abs(a - b) for a, b in zip(d0, d1, strict=True)) < 1e-3


def test_moth_is_periodic_and_bounded():
    sys = presets.moth().system
    start = [p.copy() for p in sys.pos]
    period = 14.8939  # Suvakov-Dmitrasinovic 2013
    dt = 0.003
    max_extent = 0.0
    for _ in range(5):  # five full periods
        for _ in range(round(period / dt)):
            sys.step(dt)
            max_extent = max(max_extent, max_extent_from_com(sys))
    assert max_extent < 3.0  # stays bounded thanks to the 4th-order integrator
    assert max_component_dev(sys.pos, start) < 0.1  # returns near its start


def test_sun_and_planets_conserves_energy():
    sys = presets.sun_and_planets().system
    e0 = sys.total_energy()
    for _ in range(4000):
        sys.step(0.002)
    drift = abs(sys.total_energy() - e0) / abs(e0)
    assert drift < 1e-2


def test_potential_energy_finite_for_coincident_bodies():
    import math

    sys = System(
        positions=[(0.0, 0.0), (0.0, 0.0)],
        velocities=[(0.0, 0.0), (0.0, 0.0)],
        masses=[1.0, 1.0],
        softening=0.0,
    )
    assert math.isfinite(sys.total_energy())


def test_softening_removes_the_singularity():
    import math

    sys = System(
        positions=[(0.0, 0.0), (0.0, 0.0)],
        velocities=[(0.0, 0.0), (0.0, 0.0)],
        masses=[1.0, 1.0],
        softening=0.1,
    )
    sys.step(0.01)
    assert all(math.isfinite(p.x) and math.isfinite(p.y) for p in sys.pos)


def test_mismatched_input_lengths_raise():
    with pytest.raises(ValueError):
        System(positions=[(0, 0), (1, 1)], velocities=[(0, 0)], masses=[1, 1])
