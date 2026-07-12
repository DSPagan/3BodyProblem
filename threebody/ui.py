"""Menu button, HUD panel and text helpers (presentation only)."""

from __future__ import annotations

import pygame

from .render import HUD_COLOR

_FONT_CACHE: dict[tuple[str | None, int, bool], pygame.font.Font] = {}


def get_font(size: int, *, bold: bool = False, name: str | None = None) -> pygame.font.Font:
    key = (name, size, bold)
    if key not in _FONT_CACHE:
        if name is None:
            # Default bundled font — works identically on desktop and in the
            # browser (pygbag/WASM), where system fonts may be unavailable.
            font = pygame.font.Font(None, size)
            font.set_bold(bold)
        else:
            font = pygame.font.SysFont(name, size, bold=bold)
        _FONT_CACHE[key] = font
    return _FONT_CACHE[key]


class Button:
    """A text button that highlights on hover."""

    def __init__(
        self,
        pos: tuple[int, int],
        text: str,
        font: pygame.font.Font,
        base_color: str = "#d7fcd4",
        hover_color: str = "white",
    ) -> None:
        self.pos = pos
        self.text = text
        self.font = font
        self.base_color = base_color
        self.hover_color = hover_color
        self.surface = font.render(text, True, base_color)
        self.rect = self.surface.get_rect(center=pos)

    def draw(self, screen: pygame.Surface, mouse_pos: tuple[int, int]) -> None:
        color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.base_color
        self.surface = self.font.render(self.text, True, color)
        screen.blit(self.surface, self.rect)

    def hovered(self, mouse_pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(mouse_pos)


def draw_text_panel(
    screen: pygame.Surface,
    lines: list[str],
    *,
    font: pygame.font.Font,
    origin: tuple[int, int] = (16, 14),
    color: tuple[int, int, int] = HUD_COLOR,
    line_height: int = 22,
) -> None:
    """Draw a left-aligned block of text lines."""
    x, y = origin
    for i, line in enumerate(lines):
        screen.blit(font.render(line, True, color), (x, y + i * line_height))


def draw_footer(
    screen: pygame.Surface,
    text: str,
    *,
    font: pygame.font.Font,
    color: tuple[int, int, int] = HUD_COLOR,
    margin: int = 14,
) -> None:
    """Draw a hint line pinned to the bottom-left corner."""
    surf = font.render(text, True, color)
    screen.blit(surf, (margin, screen.get_height() - surf.get_height() - margin))
