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
    EDITABLE_ATTRS = ('title', 'description', 'is_r_rated')

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
    DATA_FILENAMES = {JSON_DB_PATH.name, JSON_DB_PATH_TMP.name}

    def __init__(self, app):
        super().__init__(app)

        self._in_transaction = False
        self._videos = {}

        if self.JSON_DB_PATH.exists():
            try:
                with open(self.JSON_DB_PATH, "r") as file:
                    videos = json.load(file)

                videos = (Video(**kwargs) for kwargs in videos)
                self._videos = {video.filename: video for video in videos}
            except Exception:
                logger.exception("Error deserializing videos JSON file. Ignoring.")

        with self.transaction():
            for video_path in settings.VIDEOS_DIR.iterdir():
                self.create(video_path)

            # Purge videos that don't exist
            for video in list(self.values()):
                if not video.path.exists():
                    del self[video]

    async def watch_for_videos(self):
        async for changes in awatch(
            settings.VIDEOS_DIR,
            watch_filter=lambda change, _: change != WatchFilesChange.modified,
        ):
            for change, path in changes:
                path = Path(path)
                if path not in self.DATA_FILENAMES:
                    if change == WatchFilesChange.added and path.is_file():
                        self.create(path)
                    elif change == WatchFilesChange.deleted and path in self:
                        del self[path]
            await self.app.state.player.set_state(videos=self.as_json())

    @contextmanager
    def transaction(self):
        self._in_transaction = True
        yield
        self._in_transaction = False
        self.save()

    def save(self):
        with open(self.JSON_DB_PATH_TMP, "w") as file:
            json.dump(self.as_json(), file, indent=2, sort_keys=True)
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
            self.save()

    @convert_arg_to_filename
    def __delitem__(self, filename):
        logger.info(f"Removing video: {filename}")
        del self._videos[filename]
        if not self._in_transaction:
            self.save()

    def __iter__(self):
        return iter(sorted(self._videos.keys()))

    def items(self):
        return ((filename, video) for filename, video in sorted(self._videos.items()))

    def values(self):
        return (value for _, value in self.items())

    def update(self, *args, **kwargs):
        with self.transaction():
            super().update(*args, **kwargs)

    @convert_arg_to_filename
    def update_video(self, filename, **kwargs):
        updated = False
        if (video := self.get(filename)) is not None:
            for attr, value in kwargs.items():
                if attr in Video.EDITABLE_ATTRS and getattr(video, attr) != value:
                    setattr(video, attr, value)
                    logger.info(f"Set {attr}={value} for {filename}")
                    updated = True

            if updated:
                self.save()

        else:
            logger.warning(f"No video {filename} to update")
        return updated

    def __len__(self):
        return len(self._videos)

    def create(self, path, **kwargs):
        if path not in self and path.name not in self.DATA_FILENAMES:
            logger.info(f"Creating video: {path.name}")
            self[path.name] = Video(path, **kwargs)

    def as_json(self):
        return [v.as_dict() for v in self.values()]

    def random(self):
        choices = list(self._videos.values())
        if choices:
            return random.choice(choices)
