import asyncio
from functools import wraps
import hmac
import logging
import re
import sys
import time
import typing

from uvicorn.logging import ColourizedFormatter

from . import settings


AUTO_RESTART_SLEEP_TIME = 2.5
AUTO_RESTART_MIN_TRIES = 5
AUTO_RESTART_AVERAGE_COROUTINE_FAIL_TIME_BEFORE_EXIT = 15
UPPERCASE_RE = re.compile(r"(?<!^)(?=[A-Z])")


logger = logging.getLogger(__name__)


class SingletonBaseClass:
    TASKS = ()

    def __init__(self, app):
        self.app = app

    async def startup(self):
        for task_name in self.TASKS:
            task = getattr(self, task_name)
            asyncio.create_task(auto_restart_coroutine(task))

    def _app_running(self):
        if self.app.state.shutting_down:
            raise asyncio.CancelledError()
        return True


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
    return hmac.compare_digest(
        password.encode("utf-8"),
        str(settings.PASSWORD).encode("utf-8"),
    )


def underscore_to_camel(s):
    return "".join(w.capitalize() if n > 0 else w for n, w in enumerate(s.split("_")))


def camel_to_underscore(s):
    return UPPERCASE_RE.sub("_", s).lower()


def convert_to_camel(obj):
    if isinstance(obj, dict):
        return {underscore_to_camel(k): convert_to_camel(v) for k, v in obj.items()}
    elif isinstance(obj, (tuple, list)):
        return list(map(convert_to_camel, obj))
    else:
        return obj


def init_pkg_logger():
    pkg_logger = logging.getLogger(__package__)
    handler = logging.StreamHandler()
    formatter = ColourizedFormatter(
        "{levelprefix:<8} {asctime} {name}:{lineno}:{funcName}: {message}", style="{", use_colors=True
    )
    handler.setFormatter(formatter)
    pkg_logger.setLevel("INFO")
    pkg_logger.addHandler(handler)
