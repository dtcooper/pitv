import asyncio
from functools import wraps
import hmac
import logging
import re
import sys
import time
import typing

import imdb
from uvicorn.logging import ColourizedFormatter

from . import settings


AUTO_RESTART_SLEEP_TIME = 2.5
AUTO_RESTART_MIN_TRIES = 5
AUTO_RESTART_AVERAGE_COROUTINE_FAIL_TIME_BEFORE_EXIT = 15
IMDB_INVALID_IMAGES = {"https://m.media-amazon.png"}
UPPERCASE_RE = re.compile(r"(?<!^)(?=[A-Z])")
_BACKGROUND_TASKS = set()


logger = logging.getLogger(__name__)


def run_in_background(coro):
    task = asyncio.create_task(coro)
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)


def cancel_all_background_tasks():
    for task in _BACKGROUND_TASKS:
        task.cancel()


class SingletonBaseClass:
    TASKS = ()

    def __init__(self, app):
        self.app = app
        self._tasks = []

    async def startup(self):
        for task_name in self.TASKS:
            task = getattr(self, task_name)
            run_in_background(auto_restart_coroutine(task))


async def auto_restart_coroutine(coro: typing.Coroutine, *args, **kwargs):
    @wraps(coro)
    async def auto_restart_coro():
        failures = []

        while True:
            logger.info(f"Starting coroutine {coro.__name__} in auto-restart mode")
            start_time = time.monotonic()
            try:
                await coro(*args, **kwargs)
            except asyncio.CancelledError:
                return

            except Exception:
                failure_time = time.monotonic() - start_time
                failures.append(failure_time)
                failures = failures[-AUTO_RESTART_MIN_TRIES:]

                if len(failures) >= AUTO_RESTART_MIN_TRIES:
                    average_failure_time = (
                        sum((cur - prev) for cur, prev in zip(failures[1:], failures[:-1])) / AUTO_RESTART_MIN_TRIES
                    )
                    if average_failure_time <= AUTO_RESTART_AVERAGE_COROUTINE_FAIL_TIME_BEFORE_EXIT:
                        logger.exception(
                            f"Coroutine failed {AUTO_RESTART_MIN_TRIES} on average less than"
                            f" {AUTO_RESTART_AVERAGE_COROUTINE_FAIL_TIME_BEFORE_EXIT} seconds (average"
                            f" {average_failure_time:.6f}s). Exiting."
                        )
                        sys.exit(1)

                logger.exception(f"Coroutine failed, restarting in {AUTO_RESTART_SLEEP_TIME}s: {coro.__name__}(...)")
                await asyncio.sleep(AUTO_RESTART_SLEEP_TIME)

    return await auto_restart_coro()


def verify_password(password: str):
    password_bytes = password.encode("utf-8")
    return (
        hmac.compare_digest(password_bytes, str(settings.PASSWORD_USER).encode("utf-8")),
        hmac.compare_digest(password_bytes, str(settings.PASSWORD_ADMIN).encode("utf-8")),
    )


def underscore_to_camel(s):
    return "".join(w.capitalize() if n > 0 else w for n, w in enumerate(s.split("_")))


def camel_to_underscore(s):
    return UPPERCASE_RE.sub("_", s).lower()


def convert_obj_to_camel(obj):
    if isinstance(obj, dict):
        return {underscore_to_camel(k): convert_obj_to_camel(v) for k, v in obj.items()}
    elif isinstance(obj, (tuple, list)):
        return list(map(convert_obj_to_camel, obj))
    else:
        return obj


def search_imdb_blocking(title):
    api = imdb.Cinemagoer()
    results = []
    for movie in api.search_movie_advanced(title, adult=True):
        if (title := movie.get("title")) is not None:
            for image_key in ("full-size cover url", "cover url"):
                image = movie.get(image_key)
                if image is not None and image not in IMDB_INVALID_IMAGES:
                    break
                image = None

            results.append(
                {
                    "title": title,
                    "year": movie.get("year"),
                    "description": movie.get("plot"),
                    "image": image,
                }
            )
    return results


async def search_imdb(title):
    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(None, search_imdb_blocking, title)
    return results


def init_pkg_logger():
    pkg_logger = logging.getLogger(__package__)
    handler = logging.StreamHandler()
    formatter = ColourizedFormatter(
        "{levelprefix:<8} {asctime} {name}:{lineno}:{funcName}: {message}", style="{", use_colors=True
    )
    handler.setFormatter(formatter)
    pkg_logger.setLevel("INFO")
    pkg_logger.addHandler(handler)
