"""Physics correctness tests - all run headless, no display required.

These are the tests that justify the "symplectic" claim: over long runs the
integrator must conserve linear momentum (exactly) and total energy (to a small
drift), and the famous figure-eight orbit must return to its starting point.
"""

from __future__ import annotations

import numpy as np
import pytest

from threebody import presets
from threebody.physics import System


def two_body_circular() -> System:
    """Two equal masses on a circular orbit about their common centre.

    For separation d, ``v = sqrt(G m / (2 d))`` gives a circular orbit.
    Here G = m = 1, d = 2  ->  v = 0.5, period = 4*pi.
    """
    return System(
        positions=[[-1.0, 0.0], [1.0, 0.0]],
        velocities=[[0.0, -0.5], [0.0, 0.5]],
        masses=[1.0, 1.0],
        G=1.0,
        softening=0.0,
    )


def test_momentum_conserved_to_machine_precision():
    sys = two_body_circular()
    p0 = sys.momentum().copy()
    for _ in range(5000):
        sys.step(0.005)
    assert np.allclose(sys.momentum(), p0, atol=1e-9)


def test_center_of_mass_stays_put_with_zero_momentum():
    sys = presets.figure_eight().system
    com0 = sys.center_of_mass().copy()
    for _ in range(3000):
        sys.step(0.002)
    assert np.allclose(sys.center_of_mass(), com0, atol=1e-8)


def test_energy_drift_is_small_over_many_orbits():
    sys = two_body_circular()
    e0 = sys.total_energy()
    period = 4 * np.pi
    steps = int(round(10 * period / 0.002))  # ten orbits
    for _ in range(steps):
        sys.step(0.002)
    drift = abs(sys.total_energy() - e0) / abs(e0)
    assert drift < 1e-3


def test_two_body_orbit_stays_circular():
    sys = two_body_circular()
    seps = []
    for _ in range(4000):
        sys.step(0.002)
        seps.append(np.linalg.norm(sys.pos[0] - sys.pos[1]))
    seps = np.array(seps)
    # Separation should hover around the initial value of 2 with tiny variation.
    assert np.max(np.abs(seps - 2.0)) < 0.02


def test_figure_eight_is_periodic():
    scenario = presets.figure_eight()
    sys = scenario.system
    start = sys.pos.copy()
    period = 6.32591398  # known period of this choreography (G = m = 1)
    n = 6326
    dt = period / n
    for _ in range(n):
        sys.step(dt)
    # After one full period the three bodies should be back where they started.
    assert np.max(np.abs(sys.pos - start)) < 0.05


def test_lagrange_triangle_keeps_its_shape():
    sys = presets.lagrange_triangle().system
    side0 = np.linalg.norm(sys.pos[0] - sys.pos[1])
    for _ in range(3000):
        sys.step(0.002)
    sides = [
        np.linalg.norm(sys.pos[i] - sys.pos[j]) for i, j in ((0, 1), (1, 2), (2, 0))
    ]
    # A rigidly rotating equilateral triangle stays equilateral.
    assert max(abs(s - side0) for s in sides) < 0.02


def test_sun_and_planets_conserves_energy():
    sys = presets.sun_and_planets().system
    e0 = sys.total_energy()
    for _ in range(4000):
        sys.step(0.002)
    drift = abs(sys.total_energy() - e0) / abs(e0)
    assert drift < 1e-2


def test_potential_energy_finite_for_coincident_bodies():
    # Two bodies at the same point with no softening must not divide by zero.
    sys = System(
        positions=[[0.0, 0.0], [0.0, 0.0]],
        velocities=[[0.0, 0.0], [0.0, 0.0]],
        masses=[1.0, 1.0],
        softening=0.0,
    )
    assert np.isfinite(sys.total_energy())


def test_softening_removes_the_singularity():
    # Two coincident bodies would blow up with no softening; softening keeps
    # accelerations finite.
    sys = System(
        positions=[[0.0, 0.0], [0.0, 0.0]],
        velocities=[[0.0, 0.0], [0.0, 0.0]],
        masses=[1.0, 1.0],
        softening=0.1,
    )
    sys.step(0.01)
    assert np.all(np.isfinite(sys.pos))


def test_mismatched_input_lengths_raise():
    with pytest.raises(ValueError):
        System(positions=[[0, 0], [1, 1]], velocities=[[0, 0]], masses=[1, 1])
