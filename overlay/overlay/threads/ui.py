from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from dispmanx import DispmanX
import pygame
import pygame.freetype


if TYPE_CHECKING:
    from ..app import OverlayApp


pygame.freetype.init()


class UIThread:
    name = "ui"
    BG_SEMI_TRANS = "#00000099"
    OSD_TIMEOUT = 7500

    def __init__(self, app: OverlayApp):
        self.app = app
        self.clear_all()
        app.subscribe_to_state_change("currentlyPlaying", self.change_channel)
        app.subscribe_to_state_change("muted", self.change_muted)
        app.subscribe_to_notification("keyPress", self.key_press)

        fonts_dir = Path(__file__).parent.parent.parent / "fonts"
        self.fonts = {
            "regular": pygame.freetype.Font(fonts_dir / "SpaceMono-Bold.ttf"),
            "italic": pygame.freetype.Font(fonts_dir / "SpaceMono-BoldItalic.ttf"),
        }
        for font in self.fonts.values():
            font.antialiased = True
            font.kerning = True

    def clear_all(self):
        self._display_channel = (-1, None, None)
        self._display_muted = (-1, None)

    def key_press(self, data):
        button = data["button"]
        if button == "KEY_MENUBACK":
            expires, _, _ = self._display_channel
            if expires < pygame.time.get_ticks():
                self.change_channel(self.app.state["currentlyPlaying"], 10000)
            else:
                self.clear_all()
        elif button in ("KEY_VOLUMEUP", "KEY_VOLUMEDOWN"):
            self.change_muted(self.app.state["muted"])

    def change_channel(self, currently_playing, timeout=4500):
        if currently_playing is None:
            self._display_channel = (-1, None, None)
        else:
            channel, title = "0", currently_playing
            for channel, video in enumerate(self.app.state["videos"], 1):
                if video["path"] == currently_playing:
                    title = video["title"]
                    break
            self._display_channel = (pygame.time.get_ticks() + timeout, str(channel), title)

    def change_muted(self, value, timeout=4500):
        self._display_muted = (pygame.time.get_ticks() + timeout, value)

    def render_font(self, text, fgcolor="#FFFFFFFF", bgcolor="#00000000", size=24, font="regular"):
        font = self.fonts.get(font)
        return font.render(text, fgcolor, bgcolor, size=size)

    def render_channel(self, tick):
        expires, channel, title = self._display_channel
        if expires < tick:
            return

        surf, rect = self.render_font(channel, size=60)
        bgcolor = self.BG_SEMI_TRANS
        top, _, _, left = self.app.overscan
        left = left + 20
        top = top + 20
        pad = 14
        self.surface.fill(bgcolor, (left - pad // 2, top - pad // 2, rect.width + pad, rect.height + pad))
        self.surface.blit(surf, (left, top))
        top += rect.height + pad

        surf, rect = self.render_font(title, "#FFEE00", size=24, font="italic")
        self.surface.fill(bgcolor, (left - pad // 2, top - pad // 2, rect.width + pad, rect.height + pad))
        self.surface.blit(surf, (left, top))

    def render_muted(self, tick):
        expires, muted = self._display_muted
        if expires < tick:
            return

        bgcolor = self.BG_SEMI_TRANS
        if muted:
            color, text = "#F87272", "sound off"
        else:
            color, text = "#36D399", "sound on"

        top, _, right, _ = self.app.overscan
        top = top + 20
        right = self.display.width - right - 20
        pad = 14
        surf, rect = self.render_font(text, color, size=32)
        pad_left = right - rect.width - pad - pad // 2
        pad_top = top - pad // 2
        self.surface.fill(bgcolor, (pad_left, pad_top, rect.width + pad, rect.height + pad))
        self.surface.blit(surf, (right - rect.width - pad, top))

    def run(self):
        self.display = display = DispmanX(pixel_format="RGBA", layer=1)
        self.surface = pygame.image.frombuffer(display.buffer, display.size, display.pixel_format)
        clock = pygame.time.Clock()

        while True:
            self.surface.fill("#00000000")
            tick = pygame.time.get_ticks()
            self.render_channel(tick)
            self.render_muted(tick)

            self.display.update()
            clock.tick(self.app.FPS)
