from __future__ import annotations

import queue
from typing import TYPE_CHECKING

from dispmanx import DispmanX
import numpy
import pygame


if TYPE_CHECKING:
    from ..app import OverlayApp


class StaticBackgroundThread:
    name = "static"

    def __init__(self, app: OverlayApp):
        self._app = app
        self._show_static_queue = queue.Queue()
        self._display = DispmanX(pixel_format="RGB565", buffer_type="numpy", layer=-1)
        self._max_buffer_value = numpy.iinfo(self._display.buffer.dtype).max
        self._rng = numpy.random.default_rng()

        app.subscribe_to_state_change("currentlyPlaying", self.currently_playing_changed)

    def currently_playing_changed(self):
        currently_playing = self._app.state["currentlyPlaying"]
        self._show_static_queue.put(currently_playing is None)

    def _show_static_until_message(self):
        clock = pygame.time.Clock()
        shape, dtype = self._display.buffer.shape, self._display.buffer.dtype

        while self._show_static_queue.empty():
            static = self._rng.integers(0, self._max_buffer_value, size=shape, dtype=dtype, endpoint=True)
            numpy.copyto(self._display.buffer, static)
            self._display.update()
            clock.tick(self._app.FPS)

    def run(self):
        show_static = True

        while True:
            if show_static:
                self._show_static_until_message()
            else:
                self._display.buffer[...] = 0
                self._display.update()

            show_static = self._show_static_queue.get()
