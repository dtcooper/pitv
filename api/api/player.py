import asyncio
import logging
import os
from pathlib import Path
import random
import re
import shutil

from starlette.applications import Starlette

from . import settings
from .util import auto_restart_coroutine


logger = logging.getLogger(__name__)


class Player:
    DOWNLOAD_RE = re.compile(r"^\[download\]\s*([0-9\.]+)")
    PLAYER_PROC_NAME = "omxplayer.bin"
    PLAYER_PATH = shutil.which(PLAYER_PROC_NAME)
    SLEEP_BETWEEN_KILL = 0.2
    TASKS = ["watch_for_videos", "run_player"]
    VIDEOS_DIR = settings.VIDEOS_DIR
    YT_DLP_PATH = shutil.which("yt-dlp")

    def __init__(self, app: Starlette):
        self.videos = set()
        self.app = app
        self.websockets = app.state.authorized_websockets
        self.stop_playing_event = asyncio.Event()
        self.next_video_request = None
        self.pid = None
        self.state = {
            "videos": [],
            "currently_playing": None,
            "download": False,
        }

    async def _kill(self, signal):
        proc = await asyncio.create_subprocess_exec(
            "killall",
            "-s",
            signal,
            self.PLAYER_PROC_NAME,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

    async def kill(self):
        logger.info("Killing omxplayer with SIGINT + SIGKILL")
        await self._kill("SIGINT")
        await asyncio.sleep(self.SLEEP_BETWEEN_KILL)
        await self._kill("SIGKILL")

    async def startup(self):
        await self.kill()
        for task_name in self.TASKS:
            task = getattr(self, task_name)
            asyncio.create_task(auto_restart_coroutine(task))

    async def watch_for_videos(self):
        while not self.app.state.shutting_down:
            await self.scan_for_videos()
            await asyncio.sleep(settings.VIDEOS_DIR_SCAN_TIME)

        raise asyncio.CancelledError()

    def request_video(self, filename):
        path = self.VIDEOS_DIR / filename
        if path in self.videos:
            logger.info(f"Requesting video: {path.name}")
            self.next_video_request = path
            self.stop_playing_event.set()
        else:
            logger.info(f"Invalid video request: {filename}")

    async def request_url(self, url):
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
        await self.set_state("download", False)

        played = False
        if filename is not None:
            path = Path(filename)
            if path.exists():
                self.next_video_request = path
                self.stop_playing_event.set()
                played = True

        if not played:
            logger.warning(f"An error occurred while downloading: {url}")

    def request_random_video(self):
        logger.info("Requesting random video")
        self.stop_playing_event.set()

    def get_next_video(self):
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
        old_value = self.state[key]
        if old_value != value:
            self.state[key] = value
            message = {key: value}
            for websocket in self.websockets:
                await websocket.send_json(message)

    async def run_player(self):
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = "/opt/vc/lib"

        while not self.app.state.shutting_down:
            next_video = self.get_next_video()

            if next_video:
                proc = await asyncio.create_subprocess_exec(
                    self.PLAYER_PATH, "--aspect-mode", "stretch", next_video, env=env
                )
                logger.info(f"player started: {next_video.name}")

                self.pid = proc.pid
                await self.set_state("currently_playing", next_video.name)

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
                await asyncio.sleep(1)

            else:
                logger.warning("No videos to play.")
                await self.set_state("currently_playing", None)
                await asyncio.sleep(5)

        raise asyncio.CancelledError()
