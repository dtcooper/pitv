import asyncio
import logging
from pathlib import Path
import random
import re
import shutil
import subprocess
import time

from dbus_next import Message as DBusMessage
from dbus_next import MessageType as DBusMessageType
from dbus_next.aio import MessageBus as DBusMessageBus
from starlette.applications import Starlette

from . import settings
from .util import auto_restart_coroutine


logger = logging.getLogger(__name__)


class Player:
    DBUS_BUS_ADDRESS_FILE = Path("/tmp/omxplayerdbus.root")
    DOWNLOAD_RE = re.compile(r"^\[download\]\s*([0-9\.]+)")
    PLAYER_PATH = shutil.which("omxplayer")
    PLAYER_PROC_NAMES = ["omxplayer", "omxplayer.bin"]
    DBUS_PROC_NAME = "dbus-daemon"
    SLEEP_BETWEEN_KILL = 0.2
    TASKS = ["watch_for_videos", "run_player", "push_progress"]
    VIDEOS_DIR = settings.VIDEOS_DIR
    YT_DLP_PATH = shutil.which("yt-dlp")

    def __init__(self, app: Starlette):
        self._dbus_message_bus = None
        self.videos = set()
        self.app = app
        self.websockets = app.state.authorized_websockets
        self.stop_playing_event = asyncio.Event()
        self.next_video_request = None
        self.pid = None
        self._state = {
            "videos": [],
            "currently_playing": None,
            "download": None,
            "position": None,
            "duration": None,
            "playing": False,
        }

    async def _kill(self, signal: int):
        proc = await asyncio.create_subprocess_exec(
            "killall",
            "-s",
            signal,
            *self.PLAYER_PROC_NAMES,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        await proc.wait()

    def _kill_blocking(self, signal: int):
        proc_names = list(self.PLAYER_PROC_NAMES)
        if settings.DEBUG:
            proc_names.append(self.DBUS_PROC_NAME)
        subprocess.run(
            ["killall", "-s", signal] + proc_names,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _app_running(self):
        if self.app.state.shutting_down:
            raise asyncio.CancelledError()
        return True

    async def kill(self):
        logger.info("Killing omxplayer with SIGINT + SIGKILL")
        await self._kill("SIGINT")
        await asyncio.sleep(self.SLEEP_BETWEEN_KILL)
        await self._kill("SIGKILL")

    def kill_blocking(self):
        logger.info("Killing omxplayer with SIGINT + SIGKILL (blocking)")
        self._kill_blocking("SIGINT")
        time.sleep(self.SLEEP_BETWEEN_KILL)
        self._kill_blocking("SIGKILL")

    async def startup(self):
        await self.kill()
        for task_name in self.TASKS:
            task = getattr(self, task_name)
            asyncio.create_task(auto_restart_coroutine(task))

    async def watch_for_videos(self):
        while self._app_running():
            await self.scan_for_videos()
            await asyncio.sleep(settings.VIDEOS_DIR_SCAN_TIME)

    def request_video(self, filename):
        path = self.VIDEOS_DIR / filename
        if path in self.videos:
            logger.info(f"Requesting video: {path.name}")
            self.next_video_request = path
            self.stop_playing_event.set()
        else:
            logger.info(f"Invalid video request: {filename}")

    async def request_url(self, url):
        if self.get_state("download") is not None:
            logger.warning("Refusing to download as one is already in progress")
            return

        logger.info(f"Requesting URL: {url}")
        await self.set_state("download", 0)

        proc = await asyncio.create_subprocess_exec(
            self.YT_DLP_PATH,
            "--newline",
            "--no-playlist",
            "--no-continue",
            "-f",
            "b",
            "--exec",
            "echo {}",
            "--output",
            "/tmp/downloaded-url.%(ext)s",
            url,
            stdout=asyncio.subprocess.PIPE,
        )

        filename = None
        while not proc.stdout.at_eof():
            if line := (await proc.stdout.readline()).decode("utf-8").strip():
                match = self.DOWNLOAD_RE.search(line)
                if match:
                    percent = round(float(match.group(1)), 1)
                    await self.set_state("download", percent)
                filename = line
        await proc.wait()

        played = False
        if filename is not None:
            path = Path(filename)
            if path.exists():
                self.next_video_request = path
                self.stop_playing_event.set()
                played = True

        if not played:
            logger.warning(f"An error occurred while downloading: {url}")

        await self.set_state("download", None)

    def request_random_video(self):
        logger.info("Requesting random video")
        self.stop_playing_event.set()

    def get_next_video_path(self):
        next_video = None

        if self.next_video_request:
            next_video = self.next_video_request
            self.next_video_request = None

        elif self.videos:
            next_video = random.choice(list(self.videos))

        return next_video

    async def scan_for_videos(self):
        new_videos = set(self.VIDEOS_DIR.iterdir())
        if self.videos != new_videos:
            added = new_videos - self.videos
            removed = self.videos - new_videos
            if added:
                logger.info(f"Added {len(added)} video(s): {', '.join(v.name for v in sorted(added))}")
            if removed:
                logger.info(f"Removed {len(removed)} video(s): {', '.join(v.name for v in sorted(removed))}")

            self.videos = new_videos
            await self.set_state("videos", sorted(v.name for v in self.videos))

    async def set_state(self, key, value):
        await self.set_state_multiple({key: value})

    async def set_state_multiple(self, data):
        message = {}
        for key, value in data.items():
            old_value = self._state[key]
            if old_value != value:
                self._state[key] = message[key] = value
        if message:
            for websocket in self.websockets:
                await websocket.send_json(message)

    def get_state(self, key=None):
        return self._state if key is None else self._state[key]

    async def get_dbus_message_bus(self):
        if self._dbus_message_bus is None:
            while self._dbus_message_bus is None:
                while not self.DBUS_BUS_ADDRESS_FILE.exists():
                    logger.info("waiting for dbus address file")
                    await asyncio.sleep(0.5)

                with open(self.DBUS_BUS_ADDRESS_FILE, "r") as file:
                    bus_address = file.read().strip()

                try:
                    self._dbus_message_bus = await DBusMessageBus(bus_address).connect()
                except ConnectionRefusedError:
                    logger.warning("dbus connection refused")
                    await asyncio.sleep(0.5)

        return self._dbus_message_bus

    async def seek(self, seconds):
        bus = await self.get_dbus_message_bus()
        message = DBusMessage(
            destination="org.mpris.MediaPlayer2.omxplayer",
            path="/org/mpris/MediaPlayer2",
            interface="org.mpris.MediaPlayer2.Player",
            member="Seek",
            signature="x",
            body=[round(seconds * 1000000)],
        )
        await bus.call(message)

    async def push_progress(self):
        bus = await self.get_dbus_message_bus()

        while self._app_running():
            state = {}
            error = False

            for member in ("Position", "Duration", "PlaybackStatus"):
                message = DBusMessage(
                    destination="org.mpris.MediaPlayer2.omxplayer",
                    path="/org/mpris/MediaPlayer2",
                    interface="org.freedesktop.DBus.Properties",
                    member="Get",
                    signature="ss",
                    body=["org.mpris.MediaPlayer2.Player", member],
                )
                reply = await bus.call(message)
                if reply.message_type == DBusMessageType.METHOD_RETURN:
                    if member == "PlaybackStatus":
                        state["playing"] = reply.body[0] == "Playing"
                    else:
                        state[member.lower()] = round(reply.body[0] / 1000000)
                else:
                    error = True

            if error or not state["playing"]:
                state = {"position": None, "duration": None, "playing": False}

            await self.set_state_multiple(state)
            await asyncio.sleep(0.25)

    async def run_player(self):
        while self._app_running():
            video_path = self.get_next_video_path()

            if video_path is not None:
                proc = await asyncio.create_subprocess_exec(
                    self.PLAYER_PATH,
                    "-s",
                    "--aspect-mode",
                    "stretch",
                    video_path,
                    stdout=subprocess.DEVNULL,
                )
                logger.info(f"player started: {video_path.name}")

                self.pid = proc.pid
                await self.set_state("currently_playing", video_path.name)

                wait_tasks = {
                    (proc_wait_task := asyncio.create_task(proc.wait())),
                    (stop_playing_wait_task := asyncio.create_task(self.stop_playing_event.wait())),
                }
                _, pending = await asyncio.wait(wait_tasks, return_when=asyncio.FIRST_COMPLETED)

                if stop_playing_wait_task in pending:
                    # Rather than cancel the task (doesn't seem to work), manually trigger it being done
                    self.stop_playing_event.set()
                else:
                    logger.info("Got stop playing event")

                self.stop_playing_event.clear()
                await stop_playing_wait_task

                if proc_wait_task in pending:
                    await self.kill()
                    await proc_wait_task

                self.pid = None
                logger.info("Player exited. Restarting")
                await self.set_state("currently_playing", None)

            else:
                logger.warning("No videos to play.")
                await self.set_state("currently_playing", None)

            await asyncio.sleep(5)
