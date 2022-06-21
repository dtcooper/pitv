from collections import namedtuple
import datetime
from pathlib import Path
import os
import sys
import time

import asyncio
from aiohttp import web
from aiohttp.web import Response
from aiohttp_sse import sse_response

from .utils import auto_restart


Video = namedtuple('Video', 'name path size length')


class OMXPlayer:
    VIDEOS_DIR = Path(os.environ.get('VIDEOS_DIR', '/videos'))
    VIDEOS_DIR_SCAN_TIME = 15
    TASKS = ('watch_for_videos', 'manage_omxplayer')

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
            print(f"manage_omxplayer: {datetime.datetime.now()}")
            await asyncio.sleep(1)

    def start(self):
        self.tasks = (
            asyncio.create_task(auto_restart(self.manage_omxplayer)),
            asyncio.create_task(auto_restart(self.watch_for_videos)),
        )
