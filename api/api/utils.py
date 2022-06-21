import asyncio
from functools import wraps
import sys
import time
import traceback


AUTO_RESTART_TIME = 2.5
AUTO_RESTART_MIN_TRIES = 5
AUTO_RESTART_AVERAGE_COROUTINE_FAIL_TIME_BEFORE_EXIT = 15


async def auto_restart(coro, *args, **kwargs):
    @wraps(coro)
    async def auto_restart_coro():
        failures = []

        while True:
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
                        print(
                            f"Coroutine failed {AUTO_RESTART_MIN_TRIES} on average less than"
                            f" {AUTO_RESTART_AVERAGE_COROUTINE_FAIL_TIME_BEFORE_EXIT} seconds (average"
                            f" {average_failure_time:.6f}s). Exiting."
                        )
                        traceback.print_exc()
                        sys.exit(1)

                print(f"Coroutine failed, restarting in {AUTO_RESTART_TIME}s: {coro.__name__}(...)")
                traceback.print_exc()
                await asyncio.sleep(AUTO_RESTART_TIME)

    return await auto_restart_coro()
