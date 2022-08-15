from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from dispmanx import DispmanX
import pygame
import pygame.freetype


if TYPE_CHECKING:
    from ..app import OverlayApp


pygame.freetype.init()


def format_duration(seconds: int, force_hour: bool=False):
    seconds = round(seconds)
    s = f"{seconds // 3600}:" if (seconds >= 3600 or force_hour) else ""
    return f"{s}{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


class UIThread:
    name = "ui"
    BG_SEMI_TRANS = "#00000099"

    def __init__(self, app: OverlayApp):
        self.app = app
        self.clear_all()
        app.subscribe_to_state_change("currentlyPlaying", self.currently_playing_changed)
        app.subscribe_to_state_change("muted", self.muted_changed)
        app.subscribe_to_notification("seek", self.show_progress_bar)
        app.subscribe_to_notification("keyPress", self.key_press)

        fonts_dir = Path(__file__).parent.parent.parent / "fonts"
        self.fonts = {
            "regular": pygame.freetype.Font(fonts_dir / "SpaceMono-Bold.ttf"),
            "italic": pygame.freetype.Font(fonts_dir / "SpaceMono-BoldItalic.ttf"),
        }
        for font in self.fonts.values():
            font.antialiased = True
            font.kerning = True

    def get_dimension(self, dim, margin=25):
        value = self.app.overscan[dim] + margin
        if dim == "right":
            value = self.display.width - value - 1
        elif dim == "bottom":
            value = self.display.height - value - 1
        return value

    def clear_all(self):
        self._display_channel = (-1, None, None)
        self._display_muted = (-1, None)
        self._display_progress_bar = -1

    def key_press(self, data):
        button = data["button"]
        if button in "KEY_MENUBACK":
            expires, _, _ = self._display_channel
            if expires < pygame.time.get_ticks():
                menuback_timeout = 10000
                self.currently_playing_changed(timeout=menuback_timeout)
                self.muted_changed(timeout=menuback_timeout)
                self.show_progress_bar(timeout=menuback_timeout)
            else:
                self.clear_all()
        elif button in ("KEY_VOLUMEUP", "KEY_VOLUMEDOWN"):
            self.muted_changed()

    def currently_playing_changed(self, timeout=4500):
        currently_playing = self.app.state['currentlyPlaying']

        if currently_playing is None:
            self._display_channel = (-1, None, None)
        else:
            channel, title = "0", currently_playing
            for channel, video in enumerate(self.app.state["videos"], 1):
                if video["path"] == currently_playing:
                    title = video["title"]
                    break
            self._display_channel = (pygame.time.get_ticks() + timeout, str(channel), title)

    def muted_changed(self, timeout=4500):
        muted = self.app.state["muted"]
        self._display_muted = (pygame.time.get_ticks() + timeout, muted)

    def show_progress_bar(self, data=None, timeout=4500):
        self._display_progress_bar = pygame.time.get_ticks() + timeout

    def render_font(self, text, fgcolor="#FFFFFFFF", bgcolor="#00000044", size=24, font="regular", padding=15):
        font = self.fonts.get(font)
        text_surf, text_rect = font.render(text, fgcolor, size=size)
        if bgcolor is None:
            return text_surf, text_rect
        else:
            if padding is not None:
                if isinstance(padding, (list, tuple)):
                    padding_x, padding_y = padding
                else:
                    padding_x = padding_y = padding
                if padding_x > 0 or padding_y > 0:
                    text_rect = text_rect.inflate(padding_x, padding_y)
            box_surf = pygame.Surface(text_rect.size, pygame.SRCALPHA)
            box_rect = box_surf.get_rect()
            box_surf.fill(bgcolor)
            box_surf.blit(text_surf, text_surf.get_rect(center=box_rect.center))
            return box_surf, box_rect

    def render_channel(self, tick):
        expires, channel, title = self._display_channel
        if expires < tick:
            return

        left, top = self.get_dimension("left"), self.get_dimension("top")
        surf, rect = self.render_font(channel, size=60)
        rect.topleft = (left, top)
        self.surface.blit(surf, rect)
        top += rect.height

        surf, rect = self.render_font(title, "#FFEE00", size=24, font="italic")
        rect.topleft = (left, top)
        self.surface.blit(surf, rect)

    def render_muted(self, tick):
        expires, muted = self._display_muted
        if expires < tick:
            return

        right, top = self.get_dimension("right"), self.get_dimension("top")
        color, text = ("#F87272", "sound off") if muted else ("#36D399", "sound on")
        surf, rect = self.render_font(text, color, size=32)
        rect.topright = (right, top)
        self.surface.blit(surf, rect)

    def render_progress_bar(self, tick):
        expires = self._display_progress_bar
        if expires < tick:
            return

        if self.app.state["currentlyPlaying"] is None:
            return

        position, duration = self.app.state["position"], self.app.state["duration"]

        left, right, bottom = self.get_dimension("left"), self.get_dimension("right"), self.get_dimension("bottom")
        surf, pos_rect = self.render_font(format_duration(position, duration >= 3600), size=20)
        pos_rect.bottomleft = (left, bottom)
        self.surface.blit(surf, pos_rect)
        surf, dur_rect = self.render_font(format_duration(duration), size=22)
        dur_rect.bottomright = (right, bottom)
        self.surface.blit(surf, dur_rect)
        bar_rect = pygame.Rect((0, 0, dur_rect.left - pos_rect.right - 20 - 1, dur_rect.height - 14))
        bar_rect.center = ((dur_rect.left + pos_rect.right) // 2, dur_rect.centery)
        pygame.draw.rect(self.surface, "#FFFFFF", bar_rect)
        bar_rect.width = round(bar_rect.width * position / duration)
        pygame.draw.rect(self.surface, "#3ABFF8", bar_rect)

    def run(self):
        self.display = display = DispmanX(pixel_format="RGBA", layer=1)
        self.surface = pygame.image.frombuffer(display.buffer, display.size, display.pixel_format)
        clock = pygame.time.Clock()

        while True:
            self.surface.fill("#00000000")
            tick = pygame.time.get_ticks()
            self.render_channel(tick)
            self.render_muted(tick)
            self.render_progress_bar(tick)

            self.display.update()
            clock.tick(self.app.FPS)
