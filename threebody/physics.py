"""N-body gravitational physics.

The engine is deliberately independent from pygame so it can be unit-tested
without a display. It integrates Newtonian gravity with a *symplectic*
velocity-Verlet (leapfrog) scheme, which conserves energy and linear momentum
far better than a naive Euler step over long runs.

Acceleration on body ``i``:

    a_i = G * Σ_{j≠i}  m_j * (r_j - r_i) / (|r_j - r_i|² + ε²)^{3/2}

where ``ε`` is a *softening* length that removes the singularity when two
bodies get arbitrarily close.  With ``ε = 0`` this is exact Newtonian gravity.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]


class System:
    """A set of point masses interacting through gravity.

    Positions and velocities are ``(N, 2)`` arrays; masses are ``(N,)``.
    The class is dimension-agnostic in principle, but the app uses 2D.
    """

    def __init__(
        self,
        positions: Array | list,
        velocities: Array | list,
        masses: Array | list,
        *,
        G: float = 1.0,
        softening: float = 0.0,
    ) -> None:
        self.pos = np.asarray(positions, dtype=float).reshape(-1, 2).copy()
        self.vel = np.asarray(velocities, dtype=float).reshape(-1, 2).copy()
        self.mass = np.asarray(masses, dtype=float).reshape(-1).copy()

        if not (len(self.pos) == len(self.vel) == len(self.mass)):
            raise ValueError("positions, velocities and masses must have equal length")

        self.G = float(G)
        self.softening = float(softening)
        self.time = 0.0
        # Cache the current acceleration so velocity-Verlet reuses it between steps.
        self._acc = self._accelerations(self.pos)

    # -- core dynamics ----------------------------------------------------

    def _accelerations(self, pos: Array) -> Array:
        """Pairwise gravitational acceleration for every body (vectorised)."""
        # diff[i, j] = r_j - r_i   -> shape (N, N, 2)
        diff = pos[np.newaxis, :, :] - pos[:, np.newaxis, :]
        dist2 = np.sum(diff * diff, axis=-1) + self.softening**2  # (N, N)

        with np.errstate(divide="ignore", invalid="ignore"):
            inv_r3 = dist2**-1.5
        # A body exerts no force on itself; also guard against coincident bodies.
        inv_r3[~np.isfinite(inv_r3)] = 0.0
        np.fill_diagonal(inv_r3, 0.0)

        # a_i = G Σ_j m_j * diff[i, j] * inv_r3[i, j]
        return self.G * np.einsum("j,ij,ijk->ik", self.mass, inv_r3, diff)

    def step(self, dt: float) -> None:
        """Advance the system by ``dt`` using velocity Verlet."""
        acc = self._acc
        self.pos += self.vel * dt + 0.5 * acc * dt * dt
        new_acc = self._accelerations(self.pos)
        self.vel += 0.5 * (acc + new_acc) * dt
        self._acc = new_acc
        self.time += dt

    def substeps(self, dt: float, n: int) -> None:
        """Run ``n`` Verlet steps of size ``dt`` (finer integration per frame)."""
        for _ in range(n):
            self.step(dt)

    # -- conserved quantities (great for verifying correctness) -----------

    def kinetic_energy(self) -> float:
        return 0.5 * float(np.sum(self.mass * np.sum(self.vel * self.vel, axis=1)))

    def potential_energy(self) -> float:
        i, j = np.triu_indices(len(self.mass), k=1)
        diff = self.pos[i] - self.pos[j]
        r = np.sqrt(np.sum(diff * diff, axis=1) + self.softening**2)
        # Floor the separation so coincident bodies (softening == 0) give a large
        # but finite energy instead of a divide-by-zero, matching the guarded
        # acceleration above.
        r = np.maximum(r, 1e-12)
        return -self.G * float(np.sum(self.mass[i] * self.mass[j] / r))

    def total_energy(self) -> float:
        return self.kinetic_energy() + self.potential_energy()

    def momentum(self) -> Array:
        return np.sum(self.mass[:, np.newaxis] * self.vel, axis=0)

    def center_of_mass(self) -> Array:
        return np.sum(self.mass[:, np.newaxis] * self.pos, axis=0) / np.sum(self.mass)

    # -- convenience ------------------------------------------------------

    @property
    def n(self) -> int:
        return len(self.mass)

    def recenter_momentum(self) -> None:
        """Remove the net drift so the centre of mass stays put on screen."""
        v_cm = self.momentum() / np.sum(self.mass)
        self.vel -= v_cm
        self._acc = self._accelerations(self.pos)
