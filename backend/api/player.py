import asyncio
import datetime
import logging
from pathlib import Path
import random
import re
import shutil
import subprocess
import time

from dbus_next import Message as DBusMessage, MessageType as DBusMessageType
from dbus_next.aio import MessageBus as DBusMessageBus

from . import settings
from .util import convert_obj_to_camel, SingletonBaseClass
from .videos import VideosStore


logger = logging.getLogger(__name__)


class Player(SingletonBaseClass):
    DBUS_BUS_ADDRESS_PATH = Path("/tmp/omxplayerdbus.root")
    DBUS_PROC_NAME = "dbus-daemon"
    DBUS_LOADING_SLEEP_TIME = 0.5
    DOWNLOAD_RE = re.compile(r"^\[download\]\s*([0-9\.]+)")
    PLAYER_PATH = shutil.which("omxplayer")
    PLAYER_PROC_NAMES = ["omxplayer", "omxplayer.bin"]
    PUSH_PROGRESS_SLEEP_TIME = 0.25
    BETWEEN_VIDEOS_SLEEP_TIME_RANGE = (0.75, 4.0)
    KILL_SLEEP_TIME = 0.2
    TASKS = ("run_player", "push_progress")
    VIDEOS_DIR = settings.VIDEOS_DIR
    YT_DLP_PATH = shutil.which("yt-dlp")

    def __init__(self, app):
        super().__init__(app)

        self._dbus_message_bus = None
        self.videos: VideosStore = self.app.state.videos
        self.websockets = app.state.authorized_websockets
        self.stop_playing_event = asyncio.Event()
        self.next_video_request = None
        self._state = {
            # JS object style keys
            "videos": self.videos.as_json(),
            "currently_playing": None,
            "download": None,
            "position": None,
            "duration": None,
            "playing": False,
            "play_r_rated": self.videos._play_r_rated,
            "paused": False,
            "muted": self.videos._muted,
        }

    async def _kill(self, signal: int):
        proc = await asyncio.create_subprocess_exec(
            "killall",
            "-s",
            signal,
            *self.PLAYER_PROC_NAMES,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
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

    async def kill(self):
        logger.info("Killing omxplayer with SIGINT + SIGKILL")
        await self._kill("SIGINT")
        await asyncio.sleep(self.KILL_SLEEP_TIME)
        await self._kill("SIGKILL")

    def kill_blocking(self):
        logger.info("Killing omxplayer with SIGINT + SIGKILL (blocking)")
        self._kill_blocking("SIGINT")
        time.sleep(self.KILL_SLEEP_TIME)
        self._kill_blocking("SIGKILL")

    async def startup(self):
        await self.kill()
        await super().startup()

    def request_video(self, filename):
        video = self.videos.get(filename)
        if video is not None:
            logger.info(f"Requesting video: {video.filename}")
            self.next_video_request = video
            self.stop_playing_event.set()
        else:
            logger.info(f"Invalid video request: {filename}")

    async def request_url(self, url):
        raise Exception("Broken!")

        if self.get_state("download") is not None:
            logger.warning("Refusing to download as one is already in progress")
            return

        logger.info(f"Requesting URL: {url}")
        await self.set_state(download=0)

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
                    await self.set_state(download=percent)
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

        await self.set_state(download=None)

    def request_random_video(self):
        logger.info("Requesting random video")
        self.stop_playing_event.set()

    def get_state(self, key=None):
        return self._state if key is None else self._state[key]

    async def set_state(self, authorize_websocket=None, **kwargs):
        if authorize_websocket is None:
            message = {}
            for key, value in kwargs.items():
                if key in self._state:
                    old_value = self._state[key]
                    if old_value != value:
                        self._state[key] = message[key] = value
                else:
                    logger.error(f"Invalid player state key: {key}")
            websockets = self.websockets

        else:
            websockets = (authorize_websocket,)
            # On first message, send extras (title)
            message = {'title': settings.TITLE, **self._state}

        if message:
            message = convert_obj_to_camel(message)
            for websocket in websockets:
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.exception("Couldn't write to websocket")

        if authorize_websocket is not None:
            self.websockets.add(websocket)

    async def get_dbus_message_bus(self):
        if self._dbus_message_bus is None:
            while self._dbus_message_bus is None:
                while not self.DBUS_BUS_ADDRESS_PATH.exists():
                    logger.info("waiting for dbus address file")
                    await asyncio.sleep(self.DBUS_LOADING_SLEEP_TIME)

                with open(self.DBUS_BUS_ADDRESS_PATH, "r") as file:
                    bus_address = file.read().strip()

                try:
                    self._dbus_message_bus = await DBusMessageBus(bus_address).connect()
                except ConnectionRefusedError:
                    logger.warning("dbus connection refused")
                    await asyncio.sleep(self.DBUS_LOADING_SLEEP_TIME)
                else:
                    logger.info("dbus connection succeeded")

        return self._dbus_message_bus

    async def _dbus_helper(self, member, signature="", body=None):
        bus = await self.get_dbus_message_bus()
        return await bus.call(
            DBusMessage(
                destination="org.mpris.MediaPlayer2.omxplayer",
                path="/org/mpris/MediaPlayer2",
                interface="org.freedesktop.DBus.Properties" if member == "Get" else "org.mpris.MediaPlayer2.Player",
                member=member,
                signature=signature,
                body=body or [],
            )
        )

    async def seek(self, seconds):
        await self._dbus_helper("Seek", "x", [round(seconds * 1000000)])

    async def set_position(self, seconds):
        await self._dbus_helper("SetPosition", "ox", ["/not/used", round(seconds * 1000000)])

    async def play_pause(self):
        await self._dbus_helper("PlayPause")

    async def push_progress(self):
        while self._app_running():
            state = {}
            error = False

            for member in ("Position", "Duration", "PlaybackStatus"):
                reply = await self._dbus_helper("Get", "ss", ["org.mpris.MediaPlayer2.Player", member])

                if reply.message_type == DBusMessageType.METHOD_RETURN:
                    if member == "PlaybackStatus":
                        state.update(
                            {
                                "playing": True,
                                "paused": reply.body[0] == "Paused",
                            }
                        )
                    else:
                        state[member.lower()] = round(reply.body[0] / 1000000)
                else:
                    error = True

            if error:
                state = {"position": None, "duration": None, "playing": False, "paused": False}
            else:
                currently_playing = self.get_state("currently_playing")
                duration = datetime.timedelta(seconds=state["duration"])
                await self.videos.update_video(currently_playing, duration=duration)

            await self.set_state(**state)
            await asyncio.sleep(self.PUSH_PROGRESS_SLEEP_TIME)

    async def run_player(self):
        while self._app_running():
            if self.next_video_request is None:
                video = self.videos.random()
            else:
                video = self.next_video_request
                self.next_video_request = None

            if video is not None:
                proc = await asyncio.create_subprocess_exec(
                    self.PLAYER_PATH,
                    "--no-osd",
                    "--adev",
                    "alsa",
                    "--aspect-mode",
                    "stretch",
                    video.path,
                    stdout=asyncio.subprocess.DEVNULL,
                )
                proc_start_time = time.time()
                logger.info(f"player started: {video.filename}")
                await self.set_state(currently_playing=video.filename)

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

                elif proc.returncode != 0:
                    proc_end_time = time.time()
                    if proc_end_time - proc_start_time <= settings.PLAYER_ERROR_TIMEOUT:
                        logger.error(
                            f"Player exited in under {settings.PLAYER_ERROR_TIMEOUT:.2f}s with code"
                            f" {proc.returncode} for: {video.filename}."
                        )
                        logger.warning(f"Removing unplayable {video.filename} from videos list")
                        if video in self.videos:
                            del self.videos[video]
                            await self.set_state(videos=self.videos.as_json())

                logger.info("Player exited. Restarting")
                await self.set_state(currently_playing=None)

            else:
                logger.warning("No videos to play.")
                await self.set_state(currently_playing=None)

            # Have fun with it, show Windows 95 screen from fbi between movies
            await asyncio.sleep(random.uniform(*self.BETWEEN_VIDEOS_SLEEP_TIME_RANGE))
