from collections.abc import MutableMapping
from contextlib import contextmanager
import datetime
from functools import wraps
import json
import logging
import os
from pathlib import Path
import random

from watchfiles import awatch, Change as WatchFilesChange

from . import settings
from .util import SingletonBaseClass


logger = logging.getLogger(__name__)


def convert_arg_to_filename(func):
    @wraps(func)
    def wrapped(self, arg, *args, **kwargs):
        if isinstance(arg, Path):
            arg = arg.name
        elif isinstance(arg, Video):
            arg = arg.filename
        return func(self, arg, *args, **kwargs)

    return wrapped


class Video:
    def __init__(self, path, title=None, duration=0, description=None, is_r_rated=False):
        if isinstance(path, str):
            path = settings.VIDEOS_DIR / path

        if title is None:
            title = path.stem.replace("-", " ").title()

        if isinstance(duration, int):
            duration = datetime.timedelta(seconds=duration)

        self.path = path
        self.title = title
        self.description = description
        self.is_r_rated = is_r_rated
        self.duration = duration

    @property
    def filename(self):
        return self.path.name

    def as_dict(self):
        return {
            **self.__dict__,
            "path": self.filename,
            "duration": round(self.duration.total_seconds()),
        }

    def __repr__(self):
        return f"{self.__class__.__name__}(filename={self.filename!r}, title={self.title!r})"


class VideosStore(SingletonBaseClass, MutableMapping):
    TASKS = ("watch_for_videos",)
    JSON_DB_PATH = settings.VIDEOS_DIR / ".videos.json"
    JSON_DB_PATH_TMP = JSON_DB_PATH.parent / f"{JSON_DB_PATH.stem}.tmp.json"
    JSON_DATA_FILES = {JSON_DB_PATH, JSON_DB_PATH_TMP}
    EDITABLE_ATTRS = ("title", "description", "is_r_rated")

    def __init__(self, app):
        super().__init__(app)

        self._in_transaction = False
        self._videos = {}
        self._play_r_rated = True

        self.load_data()

        with self.transaction():
            for video_path in settings.VIDEOS_DIR.iterdir():
                self.create(video_path)

            # Purge videos that don't exist
            for video in list(self.values()):
                if not video.path.exists():
                    del self[video]

    @property
    def play_r_rated(self):
        return self._play_r_rated

    async def toggle_play_r_rated(self):
        self._play_r_rated = not self._play_r_rated
        self.save_data()
        await self.app.state.player.set_state(play_r_rated=self.play_r_rated)

    async def watch_for_videos(self):
        async for changes in awatch(
            settings.VIDEOS_DIR,
            watch_filter=lambda change, _: change != WatchFilesChange.modified,
        ):
            for change, path in changes:
                path = Path(path)
                if change == WatchFilesChange.added and path.is_file():
                    self.create(path)
                elif change == WatchFilesChange.deleted and path in self:
                    del self[path]
            await self.app.state.player.set_state(videos=self.as_json(), play_r_rated=self.play_r_rated)

    @contextmanager
    def transaction(self):
        self._in_transaction = True
        yield
        self._in_transaction = False
        self.save_data()

    def load_data(self):
        if self.JSON_DB_PATH.exists():
            try:
                with open(self.JSON_DB_PATH, "r") as file:
                    data = json.load(file)

                videos = (Video(**kwargs) for kwargs in data["videos"])
                self._videos = {video.filename: video for video in videos}
                self._play_r_rated = data["play_r_rated"]
            except Exception:
                logger.exception("Error deserializing videos JSON file. Ignoring.")

    def save_data(self):
        with open(self.JSON_DB_PATH_TMP, "w") as file:
            json.dump({"videos": self.as_json(), "play_r_rated": self.play_r_rated}, file, indent=2, sort_keys=True)
            file.write("\n")

        # Atomic operation (write to temp file first)
        os.rename(self.JSON_DB_PATH_TMP, self.JSON_DB_PATH)
        logger.info("Saved videos JSON")

    @convert_arg_to_filename
    def __getitem__(self, filename):
        return self._videos[filename]

    @convert_arg_to_filename
    def __setitem__(self, filename, value):
        self._videos[filename] = value
        if not self._in_transaction:
            self.save_data()

    @convert_arg_to_filename
    def __delitem__(self, filename):
        logger.info(f"Removing video: {filename}")
        del self._videos[filename]
        if not self._in_transaction:
            self.save_data()

    def __iter__(self):
        return (key for key, _ in self.items())

    def items(self):
        sorted_items = sorted(self._videos.items(), key=lambda kv: (kv[1].title.lower(), kv[0]))
        return ((filename, video) for filename, video in sorted_items)

    def values(self):
        return (value for _, value in self.items())

    def update(self, *args, **kwargs):
        with self.transaction():
            super().update(*args, **kwargs)

    @convert_arg_to_filename
    async def update_video(self, filename, **kwargs):
        updated = False
        if (video := self.get(filename)) is not None:
            for attr, value in kwargs.items():
                if getattr(video, attr) != value:
                    setattr(video, attr, value)
                    logger.info(f"Set {attr}={value} for {filename}")
                    updated = True

            if updated:
                self.save_data()
                await self.app.state.player.set_state(videos=self.as_json())

        else:
            logger.warning(f"No video {filename} to update")

    def __len__(self):
        return len(self._videos)

    def create(self, path, **kwargs):
        if path not in self and path not in self.JSON_DATA_FILES:
            logger.info(f"Creating video: {path.name}")
            self[path.name] = Video(path, **kwargs)

    def as_json(self):
        return [v.as_dict() for v in self.values()]

    def random(self):
        choices = [v for v in self._videos.values() if self.play_r_rated or not v.is_r_rated]
        if choices:
            return random.choice(choices)