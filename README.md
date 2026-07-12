# The Three-Body Problem

[![CI](https://github.com/DSPagan/3BodyProblem/actions/workflows/ci.yml/badge.svg)](https://github.com/DSPagan/3BodyProblem/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A real-time, interactive simulator of the gravitational **three-body problem** — three
point masses orbiting one another under Newtonian gravity. Set up the initial conditions
by dragging the bodies around, then launch and watch the system evolve. Because the
three-body problem has no general closed-form solution, most configurations are
**chaotic**: a tiny nudge to the starting positions sends the orbits somewhere completely
different.

![The figure-eight choreography running in the simulator](docs/demo.gif)

The integrator is **symplectic** (velocity Verlet / leapfrog), so total energy stays
essentially constant over long runs — you can watch the live energy-drift readout hover
around `0.000%` even after thousands of steps.

> This started as a prototype I wrote while studying maths and set aside for a few years.
> This is the rewrite: correct physics, a clean architecture, and tests.

## Features

- **Real-time symplectic integration** — a 4th-order Yoshida integrator conserves energy
  and linear momentum, so orbits stay stable instead of spiralling out from numerical error.
- **Direct manipulation** — left-drag a body to move it, right-drag to set its velocity
  vector. No forms, no typing coordinates.
- **Famous presets** — the figure-eight choreography, the rotating Lagrange triangle and
  Euler collinear configurations, the Moth I periodic orbit, a sun-and-planets system, and
  a random generator.
- **Fading orbit trails** and a live HUD (time, total energy, energy drift, FPS).
- **Adjustable speed**, pause/resume, and reset — all from the keyboard.
- **Tested physics** — the engine is decoupled from the graphics and covered by a headless
  `pytest` suite (energy conservation, momentum conservation, figure-eight periodicity…).

## Install

Requires Python 3.10+.

```bash
git clone https://github.com/DSPagan/3BodyProblem.git
cd 3BodyProblem
python -m venv .venv && source .venv/bin/activate    # optional but recommended
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

Press **Start**, then drag the bodies to taste and hit **Space** to launch.

## Controls

| Action | Control |
| --- | --- |
| Move a body | **Left-drag** it |
| Set a body's velocity | **Right-drag** from it (an arrow appears) |
| Launch / pause | **Space** |
| Simulation speed | **Up / Down** |
| Load a preset | **1** figure-8 · **2** Lagrange · **3** sun · **4** random · **5** Euler · **6** moth |
| Reset to set-up | **R** |
| Toggle help / fullscreen | **H** / **F** |
| Back to menu | **Esc** |

## Presets

| Key | Preset | What it is |
| --- | --- | --- |
| 1 | **Figure-Eight** | The Chenciner–Montgomery / Moore choreography — three equal masses chasing each other around a single figure-eight curve. |
| 2 | **Lagrange Triangle** | Three equal masses at the corners of a rigidly rotating equilateral triangle (a circular central configuration). |
| 3 | **Sun & Planets** | A heavy central body with two lighter ones on near-circular orbits. |
| 4 | **Random** | Three random bodies with zero net momentum — usually chaotic. |
| 5 | **Euler Collinear** | Three masses on a line rotating rigidly like a spinning rod (Euler's collinear central configuration). |
| 6 | **Moth I** | A delicate periodic orbit from Šuvakov & Dmitrašinović (2013). |

> **Why not the butterfly / Broucke orbits too?** Many catalogued periodic orbits pass
> through very close two-body encounters, where gravity is nearly singular. A fixed-step
> integrator can't resolve those and the orbit flies apart — so only orbits that stay well
> separated (figure-eight, Moth I, the central configurations) are included. Adding the
> close-encounter families cleanly would need an adaptive or regularised integrator.

## The physics

Each body feels the gravitational pull of the others:

$$\mathbf{a}_i = G \sum_{j \neq i} m_j \, \frac{\mathbf{r}_j - \mathbf{r}_i}{\left(\lVert \mathbf{r}_j - \mathbf{r}_i \rVert^2 + \varepsilon^2\right)^{3/2}}$$

The small **softening length** $\varepsilon$ removes the singularity when two bodies get
arbitrarily close (with $\varepsilon = 0$ this is exact Newtonian gravity, used by the
figure-eight and Lagrange presets).

Time is advanced with **velocity Verlet**:

$$
\mathbf{r}_{n+1} = \mathbf{r}_n + \mathbf{v}_n \, \Delta t + \tfrac12 \mathbf{a}_n \, \Delta t^2,
\qquad
\mathbf{v}_{n+1} = \mathbf{v}_n + \tfrac12 (\mathbf{a}_n + \mathbf{a}_{n+1}) \, \Delta t.
$$

This scheme is *symplectic*: unlike naive Euler integration it does not systematically
gain or lose energy, which is exactly what you want for orbital mechanics. The engine
composes three such steps with **Yoshida's coefficients** ($2w_1 + w_0 = 1$,
$w_1 = 1/(2 - 2^{1/3})$) to get a **4th-order** symplectic integrator — the same low
energy drift at a much larger time step, which is what keeps the delicate Moth I orbit
stable in real time. You can watch the live energy-drift readout to confirm it.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

The suite runs headless (no window) and checks that momentum is conserved to machine
precision, that energy drift stays tiny over many orbits, and that the figure-eight
choreography returns to its starting point after one period.

## Project layout

```
threebody/
  physics.py    # System + velocity-Verlet integrator + conserved quantities (no pygame)
  presets.py    # figure-8, Lagrange triangle, sun & planets, random
  render.py     # camera, glowing bodies, fading trails, velocity arrows
  ui.py         # menu button, HUD, help overlay
  app.py        # window, state machine (menu / edit / run / paused), main loop
main.py         # entry point
tests/          # headless physics tests
```

## License

[MIT](LICENSE) © Daniel Sánchez Pagán
