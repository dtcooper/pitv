import asyncio
import logging

from .util import SingletonBaseClass
from .player import Player


logger = logging.getLogger(__name__)


class Remote(SingletonBaseClass):
    TASKS = ("listen_to_lirc",)

    def __init__(self, app):
        super().__init__(app)

        self.player: Player = app.state.player

    async def listen_to_lirc(self):
        reader, _ = await asyncio.open_connection("lirc", 8765)
        logger.info("Connected to lirc:8765")

        async def readline():
            line = await reader.readline()
            if not line:
                raise Exception("Got no data from lirc")
            return line.decode("utf-8").strip()

        ignore = False

        while line := await readline():
            # Deal with internal messages
            if line == "BEGIN":
                while (await readline()) != "END":
                    pass
                continue

            code, repeat_count, button_name, remote = line.split()
            logger.info(f"Got {button_name} - {repeat_count} repeat(s)")

            if button_name == "KEY_RIGHT":
                await self.player.seek(15)
            elif button_name == "KEY_LEFT":
                await self.player.seek(-15)
