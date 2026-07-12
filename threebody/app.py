"""Application shell: window, state machine and main loop.

States
------
MENU   title screen
EDIT   set up initial conditions by direct manipulation (drag position,
       right-drag to set a velocity arrow); pick presets with number keys
RUN    the simulation advances in real time (symplectic velocity Verlet)
PAUSED frozen mid-run
"""

from __future__ import annotations

import asyncio
import contextlib
import math
from collections.abc import Callable

import pygame

from . import presets, render, ui
from .physics import System
from .presets import Scenario

MENU, EDIT, RUN, PAUSED = "menu", "edit", "run", "paused"

SPEEDS = [0.25, 0.5, 1.0, 2.0, 4.0]
ARROW_TIME = 0.6  # a velocity arrow previews ~0.6 time units of travel

# Auto-framing: keep every body (and its trail) on screen by following the centre
# of mass and adjusting the zoom. Zoom out fast so nothing escapes the view, zoom
# back in slowly so the picture doesn't pulse.
FRAME_MARGIN = 70.0  # px of padding around the content
MIN_EXTENT = 0.35  # world units; caps how far the auto-zoom will zoom *in*
MIN_SCALE, MAX_SCALE = 6.0, 400.0  # px per world unit
ZOOM_IN_LERP, ZOOM_OUT_LERP = 0.03, 0.15

# Number keys 1..6 -> preset factories, in this order. The pygame key *constants*
# are only referenced after pygame.init() (in App.__init__) because the browser
# (WebAssembly) build doesn't populate them until then.
PRESET_FACTORIES = [
    presets.figure_eight,
    presets.lagrange_triangle,
    presets.sun_and_planets,
    presets.random_cloud,
    presets.euler_collinear,
    presets.moth,
]


class App:
    def __init__(self, size: tuple[int, int] = (1280, 800)) -> None:
        pygame.init()
        pygame.display.set_caption("The Three-Body Problem")
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.show_help = False
        self.auto_frame = True  # auto follow + zoom to keep the bodies in view

        # Build the number-key -> preset map now that pygame is initialised.
        self.preset_keys = {
            pygame.K_1 + i: factory for i, factory in enumerate(PRESET_FACTORIES)
        }

        self.font_title = ui.get_font(72, bold=True)
        self.font_sub = ui.get_font(26)
        self.font_hud = ui.get_font(19)
        self.font_foot = ui.get_font(17)

        self.state = MENU
        self.current_factory: Callable[[], Scenario] = presets.figure_eight
        self.scenario: Scenario | None = None
        self.camera = render.Camera(self.screen.get_size(), 200.0)

        # RUN state
        self.sim: System | None = None
        self.trails: list[render.Trail] = []
        self.energy0 = 0.0
        self.speed_index = SPEEDS.index(1.0)
        self.base_substeps = 6
        self.dt = 0.003

        # EDIT interaction
        self.drag_pos: int | None = None
        self.drag_vel: int | None = None

        menu_font = ui.get_font(46)
        self.start_button = ui.Button((size[0] // 2, 470), "START", menu_font)

    # -- scenario management ---------------------------------------------

    def load_preset(self, factory: Callable[[], Scenario]) -> None:
        self.current_factory = factory
        self.scenario = factory()
        self.camera = render.Camera(self.screen.get_size(), self.scenario.view_scale)
        self.camera.center = self.scenario.system.center_of_mass()
        self.state = EDIT
        self.drag_pos = self.drag_vel = None

    def start_run(self) -> None:
        assert self.scenario is not None
        s = self.scenario.system
        self.sim = System(s.pos, s.vel, s.mass, G=s.G, softening=s.softening)
        self.energy0 = self.sim.total_energy()
        self.trails = [render.Trail() for _ in range(self.sim.n)]
        self.camera.center = self.sim.center_of_mass()
        self.state = RUN

    def reset_to_edit(self) -> None:
        self.state = EDIT
        self.drag_pos = self.drag_vel = None

    # -- main loop --------------------------------------------------------

    async def run_async(self) -> None:
        """Main loop. Async so the same code runs on the desktop and in the
        browser (pygbag/WebAssembly), where ``await`` yields to the page."""
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            self.update()
            self.draw()
            self.clock.tick(60)
            await asyncio.sleep(0)
        pygame.quit()

    def update(self) -> None:
        if self.state == RUN and self.sim is not None:
            substeps = max(1, round(self.base_substeps * SPEEDS[self.speed_index]))
            self.sim.substeps(self.dt, substeps)
            for i in range(self.sim.n):
                self.trails[i].add(self.sim.pos[i])
            self._frame_camera()

    def _frame_camera(self) -> None:
        """Follow the centre of mass and (optionally) auto-zoom to fit everything."""
        assert self.sim is not None
        com = self.sim.center_of_mass()
        self.camera.center = com
        if not self.auto_frame:
            return
        # Farthest body or trail point from the centre of mass sets the zoom.
        extent = MIN_EXTENT
        for p in self.sim.pos:
            extent = max(extent, (p - com).length())
        for trail in self.trails:
            for p in trail.points:
                extent = max(extent, (p - com).length())
        half = min(self.camera.width, self.camera.height) / 2 - FRAME_MARGIN
        target = max(MIN_SCALE, min(MAX_SCALE, half / extent))
        lerp = ZOOM_OUT_LERP if target < self.camera.scale else ZOOM_IN_LERP
        self.camera.scale += (target - self.camera.scale) * lerp

    # -- events -----------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self.camera.width, self.camera.height = event.w, event.h
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
            # toggle_fullscreen isn't supported in the browser build.
            with contextlib.suppress(pygame.error):
                pygame.display.toggle_fullscreen()
            return

        if self.state == MENU:
            self._event_menu(event)
        elif self.state == EDIT:
            self._event_edit(event)
        else:  # RUN or PAUSED
            self._event_sim(event)

    def _event_menu(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and self.start_button.hovered(event.pos):
            self.load_preset(presets.figure_eight)
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.load_preset(presets.figure_eight)
            elif event.key == pygame.K_ESCAPE:
                self.running = False

    def _event_edit(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = MENU
            elif event.key == pygame.K_SPACE:
                self.start_run()
            elif event.key == pygame.K_h:
                self.show_help = not self.show_help
            elif event.key in self.preset_keys:
                self.load_preset(self.preset_keys[event.key])
            elif event.key == pygame.K_r:
                self.load_preset(self.current_factory)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            idx = self._body_at(event.pos)
            if idx is not None:
                if event.button == 1:
                    self.drag_pos = idx
                elif event.button == 3:
                    self.drag_vel = idx
        elif event.type == pygame.MOUSEBUTTONUP:
            self.drag_pos = self.drag_vel = None
        elif event.type == pygame.MOUSEMOTION:
            self._handle_edit_drag(event.pos)

    def _event_sim(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.state = MENU
        elif event.key == pygame.K_SPACE:
            self.state = PAUSED if self.state == RUN else RUN
        elif event.key == pygame.K_r:
            self.reset_to_edit()
        elif event.key == pygame.K_h:
            self.show_help = not self.show_help
        elif event.key == pygame.K_a:
            self.auto_frame = not self.auto_frame
        elif event.key in (pygame.K_UP, pygame.K_EQUALS, pygame.K_PLUS):
            self.speed_index = min(len(SPEEDS) - 1, self.speed_index + 1)
        elif event.key in (pygame.K_DOWN, pygame.K_MINUS):
            self.speed_index = max(0, self.speed_index - 1)

    def _handle_edit_drag(self, mouse: tuple[int, int]) -> None:
        assert self.scenario is not None
        s = self.scenario.system
        if self.drag_pos is not None:
            s.pos[self.drag_pos] = self.camera.to_world(mouse)
        elif self.drag_vel is not None:
            target = self.camera.to_world(mouse)
            s.vel[self.drag_vel] = (target - s.pos[self.drag_vel]) / ARROW_TIME

    def _body_at(self, screen_pos: tuple[int, int]) -> int | None:
        assert self.scenario is not None
        s = self.scenario.system
        for i, p in enumerate(s.pos):
            sp = self.camera.to_screen(p)
            reach = render.body_radius(s.mass[i]) + 8
            if math.hypot(sp[0] - screen_pos[0], sp[1] - screen_pos[1]) <= reach:
                return i
        return None

    # -- drawing ----------------------------------------------------------

    def draw(self) -> None:
        self.screen.fill(render.BACKGROUND)
        if self.state == MENU:
            self._draw_menu()
        elif self.state == EDIT:
            self._draw_edit()
        else:
            self._draw_sim(paused=self.state == PAUSED)
        pygame.display.flip()

    def _draw_menu(self) -> None:
        w = self.screen.get_width()
        title = self.font_title.render("The Three-Body Problem", True, render.HUD_COLOR)
        self.screen.blit(title, title.get_rect(center=(w // 2, 260)))
        sub = self.font_sub.render(
            "A real-time symplectic gravity simulator", True, (150, 156, 168)
        )
        self.screen.blit(sub, sub.get_rect(center=(w // 2, 330)))
        self.start_button.rect.center = (w // 2, 470)
        self.start_button.draw(self.screen, pygame.mouse.get_pos())
        ui.draw_footer(
            self.screen,
            "Enter / click START  -  Esc quits",
            font=self.font_foot,
        )

    def _draw_edit(self) -> None:
        assert self.scenario is not None
        s = self.scenario.system
        for i in range(s.n):
            color = render.BODY_COLORS[i % len(render.BODY_COLORS)]
            start = self.camera.to_screen(s.pos[i])
            end = self.camera.to_screen(s.pos[i] + s.vel[i] * ARROW_TIME)
            render.draw_velocity_arrow(self.screen, start, end)
            render.draw_body(self.screen, start, render.body_radius(s.mass[i]), color)

        ui.draw_text_panel(
            self.screen,
            [
                f"SET-UP  -  {self.scenario.name}",
                self.scenario.description,
                "",
                "Left-drag a body: move    Right-drag: set velocity",
                "Space: launch    1-6: presets    R: reset    H: help",
            ],
            font=self.font_hud,
        )
        if self.show_help:
            self._draw_help()

    def _draw_sim(self, *, paused: bool) -> None:
        assert self.sim is not None and self.scenario is not None
        for i in range(self.sim.n):
            color = render.BODY_COLORS[i % len(render.BODY_COLORS)]
            self.trails[i].draw(self.screen, self.camera, color)
        for i in range(self.sim.n):
            color = render.BODY_COLORS[i % len(render.BODY_COLORS)]
            pos = self.camera.to_screen(self.sim.pos[i])
            render.draw_body(self.screen, pos, render.body_radius(self.sim.mass[i]), color)

        energy = self.sim.total_energy()
        drift = (energy - self.energy0) / max(abs(self.energy0), 1e-12) * 100.0
        speed = SPEEDS[self.speed_index]
        af = "on" if self.auto_frame else "off"
        ui.draw_text_panel(
            self.screen,
            [
                f"{'PAUSED' if paused else 'RUNNING'}  -  {self.scenario.name}",
                f"t = {self.sim.time:8.2f}      speed x{speed:g}",
                f"energy = {energy:9.4f}   drift {drift:+.3f}%",
                f"fps = {self.clock.get_fps():4.0f}   auto-frame {af}",
            ],
            font=self.font_hud,
        )
        ui.draw_footer(
            self.screen,
            "Space: pause/resume   Up/Down: speed   A: auto-frame   R: set-up   Esc: menu",
            font=self.font_foot,
        )
        if self.show_help:
            self._draw_help()

    def _draw_help(self) -> None:
        lines = [
            "Controls",
            "  Left-drag body ....... move it",
            "  Right-drag body ...... set its velocity",
            "  1 2 3 ................ figure-8 / Lagrange / sun",
            "  4 5 6 ................ random / Euler / moth",
            "  Space ................ launch / pause",
            "  Up / Down ............ simulation speed",
            "  A .................... auto-frame (follow + zoom)",
            "  R .................... reset to set-up",
            "  F .................... toggle fullscreen",
            "  H .................... hide this help",
            "  Esc .................. back to menu",
        ]
        w, h = self.screen.get_size()
        panel = pygame.Surface((430, len(lines) * 24 + 24), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 170))
        self.screen.blit(panel, (w - 450, h // 2 - panel.get_height() // 2))
        ui.draw_text_panel(
            self.screen,
            lines,
            font=self.font_hud,
            origin=(w - 434, h // 2 - panel.get_height() // 2 + 12),
            line_height=24,
        )


def main() -> None:
    """Synchronous entry point for the desktop app / console script."""
    asyncio.run(App().run_async())


if __name__ == "__main__":
    main()
