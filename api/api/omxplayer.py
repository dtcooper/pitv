import asyncio
import atexit
import os
from pathlib import Path
import random
import shutil
import traceback
import weakref

import psutil

from util import auto_restart


class OMXPlayer:
    OMXPLAYER_CMD_NAME = os.environ.get("OMXPLAYER_CMD_NAME", "omxplayer")
    OMXPLAYER_PATH = os.environ.get("OMXPLAYER_PATH", shutil.which(OMXPLAYER_CMD_NAME))
    VIDEOS_DIR = Path(os.environ.get("VIDEOS_DIR", "/videos"))
    VIDEOS_DIR_SCAN_TIME = 15
    TASKS = ("watch_for_videos", "manage_omxplayer")

    def __init__(self, app):
        self.app = app
        self.videos = set()
        self.task = ()
        self.stop_playing_event = asyncio.Event()
        self.state = {"videos": [], "currently_playing": None}
        self.state_subscriber_queues = weakref.WeakSet()
        self.next_video_request = None
        atexit.register(self.shutdown_cleanup)

    async def kill_omxplayer(self):
        processes = [
            p for p in psutil.process_iter(("pid", "name")) if self.OMXPLAYER_CMD_NAME in p.info["name"].lower()
        ]
        for process in processes:
            print(f"Send terminate to PID {process.info['pid']}: {process.info['name']}")
            process.terminate()

        for _ in range(10):
            for process in processes:
                if not process.is_running():
                    print(f"PID {process.info['pid']} was terminated: {process.info['name']}")
                    processes.remove(process)
            if not processes:
                break
            await asyncio.sleep(0.1)
        else:
            for process in processes:
                print(f"Killed PID {process.info['pid']}: {process.info['name']}")
                process.kill()

    def shutdown_cleanup(self):
        for process in psutil.process_iter(("pid", "name")):
            if "omxplayer" in process.info["name"].lower():
                process.kill()
                print(f"Killed PID {process.info['pid']}: {process.info['name']}")

    def set_state(self, key, value):
        old_value = self.state[key]
        if old_value != value:
            self.state[key] = value
            message = {key: value}
            for queue in self.state_subscriber_queues:
                queue.put_nowait(message)

    def scan_for_videos(self):
        new_videos = set(self.VIDEOS_DIR.iterdir())
        if self.videos != new_videos:
            added = new_videos - self.videos
            removed = self.videos - new_videos
            if added:
                print(f"Added {len(added)} video(s): {', '.join(v.name for v in sorted(added))}")
            if removed:
                print(f"Removed {len(removed)} video(s): {', '.join(v.name for v in sorted(removed))}")

            self.videos = new_videos
            self.set_state("videos", sorted(v.name for v in self.videos))

    async def watch_for_videos(self):
        print("watch_for_videos: booting")
        while True:
            self.scan_for_videos()
            await asyncio.sleep(self.VIDEOS_DIR_SCAN_TIME)

    def request_video(self, filename):
        path = self.VIDEOS_DIR / filename
        if path in self.videos:
            print(f"Requesting: {path.name}")
            self.next_video_request = path
            self.stop_playing_event.set()
        else:
            print(f"Invalid video request: {filename}")

    def get_next_video(self):
        video = None

        if self.next_video_request is not None:
            video = self.next_video_request
            self.next_video_request = None

        if video is None:
            video = random.choice(list(self.videos))

        return video

    async def manage_omxplayer(self):
        while True:
            if self.videos:
                video = self.get_next_video()

                print(f"Playing {video.name}")
                omxplayer = await asyncio.subprocess.create_subprocess_exec(
                    self.OMXPLAYER_PATH,
                    "--win",
                    "67,20,670,445",
                    video,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )

                self.set_state("currently_playing", video.name)

                try:
                    done, pending = await asyncio.wait(
                        {
                            (player_task := asyncio.create_task(omxplayer.wait())),
                            (stop_playing_event_task := asyncio.create_task(self.stop_playing_event.wait())),
                        },
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    if stop_playing_event_task in done:
                        self.stop_playing_event.clear()
                    else:
                        stop_playing_event_task.cancel()
                        await stop_playing_event_task

                    if player_task in pending:
                        await self.kill_omxplayer()
                        await player_task

                except Exception as e:
                    print(f"XXX got exception: {e}")
                    traceback.print_exc()

                self.set_state("currently_playing", None)
            else:
                print("Waiting for videos")
                await asyncio.sleep(1)

    def start(self):
        self.tasks = (
            asyncio.create_task(auto_restart(self.manage_omxplayer)),
            asyncio.create_task(auto_restart(self.watch_for_videos)),
        )
