"""N-body gravitational physics (pure Python — no compiled dependencies).

Newtonian gravity, integrated with a *4th-order symplectic* scheme (Yoshida's
composition of velocity-Verlet steps), which conserves energy and linear
momentum far better than a naive Euler step over long runs.

Acceleration on body ``i``:

    a_i = G * Σ_{j≠i}  m_j * (r_j - r_i) / (|r_j - r_i|² + ε²)^{3/2}

where ``ε`` is a *softening* length that removes the singularity when two
bodies get arbitrarily close.  With ``ε = 0`` this is exact Newtonian gravity.

The engine has no numpy/pygame dependency, so it is unit-testable headless and
runs unchanged in the browser (WebAssembly) build.
"""

from __future__ import annotations

from collections.abc import Sequence

from .vec import Vec2

# Yoshida (1990) 4th-order symplectic coefficients: a 4th-order step is the
# composition  Verlet(w1·dt) ∘ Verlet(w0·dt) ∘ Verlet(w1·dt),  with 2·w1 + w0 = 1.
_CBRT2 = 2.0 ** (1.0 / 3.0)
_YOSHIDA_W1 = 1.0 / (2.0 - _CBRT2)
_YOSHIDA_W0 = -_CBRT2 / (2.0 - _CBRT2)


def _as_vecs(items: Sequence) -> list[Vec2]:
    # Always build fresh Vec2s so a System never aliases a caller's data.
    return [Vec2(p[0], p[1]) for p in items]


class System:
    """A set of point masses interacting through gravity."""

    def __init__(
        self,
        positions: Sequence,
        velocities: Sequence,
        masses: Sequence[float],
        *,
        G: float = 1.0,
        softening: float = 0.0,
    ) -> None:
        self.pos = _as_vecs(positions)
        self.vel = _as_vecs(velocities)
        self.mass = [float(m) for m in masses]

        if not (len(self.pos) == len(self.vel) == len(self.mass)):
            raise ValueError("positions, velocities and masses must have equal length")

        self.G = float(G)
        self.softening = float(softening)
        self.time = 0.0
        # Cache the current acceleration so velocity-Verlet reuses it between steps.
        self._acc = self._accelerations(self.pos)

    # -- core dynamics ----------------------------------------------------

    def _accelerations(self, pos: list[Vec2]) -> list[Vec2]:
        n = len(pos)
        eps2 = self.softening * self.softening
        acc = [Vec2(0.0, 0.0) for _ in range(n)]
        for i in range(n):
            pi = pos[i]
            ax = ay = 0.0
            for j in range(n):
                if i == j:
                    continue
                dx = pos[j].x - pi.x
                dy = pos[j].y - pi.y
                r2 = dx * dx + dy * dy + eps2
                if r2 == 0.0:
                    continue  # coincident bodies with no softening: skip
                inv_r3 = self.mass[j] / (r2 * (r2**0.5))
                ax += dx * inv_r3
                ay += dy * inv_r3
            acc[i] = Vec2(self.G * ax, self.G * ay)
        return acc

    def _verlet(self, dt: float) -> None:
        """One symplectic velocity-Verlet (leapfrog) step. Works for dt < 0 too."""
        acc = self._acc
        half = 0.5 * dt * dt
        self.pos = [
            Vec2(p.x + v.x * dt + a.x * half, p.y + v.y * dt + a.y * half)
            for p, v, a in zip(self.pos, self.vel, acc, strict=True)
        ]
        new_acc = self._accelerations(self.pos)
        hdt = 0.5 * dt
        self.vel = [
            Vec2(v.x + (a.x + na.x) * hdt, v.y + (a.y + na.y) * hdt)
            for v, a, na in zip(self.vel, acc, new_acc, strict=True)
        ]
        self._acc = new_acc
        self.time += dt

    def step(self, dt: float) -> None:
        """Advance the system by ``dt`` with a 4th-order symplectic integrator.

        Composes three velocity-Verlet sub-steps with Yoshida's coefficients
        (Yoshida, 1990); the negative middle step cancels the 2nd-order error.
        Conserves energy far better than plain Verlet at the same ``dt`` and keeps
        delicate periodic orbits (e.g. Moth I) stable, while staying symplectic
        and exactly momentum-conserving.
        """
        self._verlet(_YOSHIDA_W1 * dt)
        self._verlet(_YOSHIDA_W0 * dt)
        self._verlet(_YOSHIDA_W1 * dt)

    def substeps(self, dt: float, n: int) -> None:
        """Run ``n`` integration steps of size ``dt`` (finer integration per frame)."""
        for _ in range(n):
            self.step(dt)

    # -- conserved quantities (great for verifying correctness) -----------

    def kinetic_energy(self) -> float:
        return 0.5 * sum(m * v.length_squared() for m, v in zip(self.mass, self.vel, strict=True))

    def potential_energy(self) -> float:
        n = len(self.mass)
        eps2 = self.softening * self.softening
        total = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                d = self.pos[i] - self.pos[j]
                # Floor the separation so coincident bodies (softening == 0) give a
                # large but finite energy instead of a divide-by-zero.
                r = max((d.length_squared() + eps2) ** 0.5, 1e-12)
                total += self.mass[i] * self.mass[j] / r
        return -self.G * total

    def total_energy(self) -> float:
        return self.kinetic_energy() + self.potential_energy()

    def momentum(self) -> Vec2:
        px = sum(m * v.x for m, v in zip(self.mass, self.vel, strict=True))
        py = sum(m * v.y for m, v in zip(self.mass, self.vel, strict=True))
        return Vec2(px, py)

    def center_of_mass(self) -> Vec2:
        total = sum(self.mass)
        cx = sum(m * p.x for m, p in zip(self.mass, self.pos, strict=True)) / total
        cy = sum(m * p.y for m, p in zip(self.mass, self.pos, strict=True)) / total
        return Vec2(cx, cy)

    # -- convenience ------------------------------------------------------

    @property
    def n(self) -> int:
        return len(self.mass)

    def recenter_momentum(self) -> None:
        """Remove the net drift so the centre of mass stays put on screen."""
        total = sum(self.mass)
        v_cm = self.momentum() / total
        self.vel = [v - v_cm for v in self.vel]
        self._acc = self._accelerations(self.pos)
