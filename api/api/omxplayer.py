import asyncio
from collections import namedtuple
import os
from pathlib import Path
import random
import shutil

from utils import auto_restart


Video = namedtuple("Video", "name path size length")


class OMXPlayer:
    OMXPLAYER_PATH = os.environ.get("OMXPLAYER_PATH", shutil.which("omxplayer"))
    VIDEOS_DIR = Path(os.environ.get("VIDEOS_DIR", "/videos"))
    VIDEOS_DIR_SCAN_TIME = 15
    TASKS = ("watch_for_videos", "manage_omxplayer")

    def __init__(self, app):
        self.app = app
        self.videos = {}
        self.task = ()

    def get_videos(self):
        return sorted(self.videos.keys())

    def scan_for_videos(self):
        # TODO refresh when size updates as well (to support downloading)
        videos = list(self.VIDEOS_DIR.iterdir())
        before = set(self.videos.keys())
        after = {v.stem for v in videos}
        if before != after:
            added = after - before
            removed = before - after
            if added:
                print(f"Added {len(added)} video(s): {', '.join(v for v in sorted(added))}")
            if removed:
                print(f"Removed {len(removed)} video(s): {', '.join(v for v in sorted(removed))}")

            self.videos = {v.stem: v for v in videos}

    async def watch_for_videos(self):
        print("watch_for_videos: booting")
        while True:
            self.scan_for_videos()
            await asyncio.sleep(self.VIDEOS_DIR_SCAN_TIME)

    async def manage_omxplayer(self):
        while True:
            if self.videos:
                video = random.choice(list(self.videos.values()))
                print(f"Playing {video.stem}")
                command = await asyncio.subprocess.create_subprocess_exec(
                    self.OMXPLAYER_PATH, "--win", "67,20,670,445", video
                )
                await command.wait()
            else:
                print("Waiting for videos")
                await asyncio.sleep(1)

    def start(self):
        self.tasks = (
            asyncio.create_task(auto_restart(self.manage_omxplayer)),
            asyncio.create_task(auto_restart(self.watch_for_videos)),
        )
