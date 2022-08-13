import asyncio
import logging

from .player import Player
from .util import SingletonBaseClass
from .videos import VideosStore


logger = logging.getLogger(__name__)


class Remote(SingletonBaseClass):
    TASKS = ("listen_to_lirc",)
    reader: asyncio.StreamReader

    def __init__(self, app):
        super().__init__(app)

        self.player: Player = app.state.player
        self.videos: VideosStore = app.state.videos

    async def readline(self) -> str:
        line = await self.reader.readline()
        if not line:
            raise Exception("readline() for lirc socket returned empty results")
        return line.decode("utf-8").strip()

    async def read_lirc_line(self) -> str:
        while True:
            line = await self.readline()

            if line == "BEGIN":
                while (await self.readline()) != "END":
                    pass

            _, repeats, button, _ = line.split()
            if int(repeats) > 0:
                continue

            logger.info(f"{button} pressed")
            return button

    async def listen_to_lirc(self):
        self.reader, _ = await asyncio.open_connection("lirc", 8765)
        logger.info("Connected to lirc:8765")

        while True:
            button = await self.read_lirc_line()

            if button == "KEY_RIGHT":
                await self.player.seek(15)
            elif button == "KEY_LEFT":
                await self.player.seek(-15)
            elif button == "KEY_BACK":
                await self.player.set_position(0)
            elif button == "KEY_VOLUMEUP":
                await self.videos.toggle_mute(value=False)
            elif button == "KEY_VOLUMEDOWN":
                await self.videos.toggle_mute(value=True)
            elif button in ("KEY_UP", "KEY_DOWN"):
                direction = 1 if button == "KEY_UP" else -1
                self.player.change_channel(direction)
            elif button == "KEY_OK":
                self.player.request_random_video()

            await self.player.notify("keyPress", button=button)
