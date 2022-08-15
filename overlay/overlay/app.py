from __future__ import annotations

from collections import defaultdict
import json
import threading
import time
import traceback

from dotenv import dotenv_values
import websocket

from .threads.static import StaticBackgroundThread
from .threads.ui import UIThread


class OverlayApp:
    FPS = 30
    thread_classes = (StaticBackgroundThread, UIThread)
    static: StaticBackgroundThread
    ui: UIThread
    threads: list
    threads_started: bool
    env: dict

    def __init__(self):
        self.state = {}
        self.env = dotenv_values("/.env")
        self.threads_started = False
        self._state_subscribers = defaultdict(list)
        self._notification_subscribers = defaultdict(list)
        self.overscan = {o: int(self.env.get(f"OVERSCAN_{o.upper()}", 0)) for o in ("top", "left", "right", "bottom")}

    @staticmethod
    def _create_daemon_thread(thread_obj):
        def target():
            while True:
                try:
                    thread_obj.run()
                except Exception:
                    print(f"{thread_obj.__class__.__name__} thread threw an exception. Restarting.")
                    traceback.print_exc()
                    time.sleep(0.1)
                else:
                    print(f"{thread_obj.__class__.__name__} exited. Restarting.")

        thread = threading.Thread(target=target)
        thread.daemon = True
        return thread

    def subscribe_to_state_change(self, key, callback):
        self._state_subscribers[key].append(callback)

    def subscribe_to_notification(self, key, callback):
        self._notification_subscribers[key].append(callback)

    def run(self):
        thread_objs = []
        threads = []

        # Create thread objects
        for thread_cls in self.thread_classes:
            thread_obj = thread_cls(app=self)
            print(f"Initializing {thread_obj.name} thread")
            setattr(self, thread_cls.name, thread_obj)
            thread_objs.append(thread_obj)

        # Start them
        for thread_obj in thread_objs:
            print(f"Starting {thread_obj.name} thread")
            threads.append(self._create_daemon_thread(thread_obj))

        # Subscribe to websocket
        while True:
            try:
                ws = websocket.WebSocket()
                ws.connect("ws://backend:8000/backend")

                ws.send(self.env["PASSWORD_USER"])
                if ws.recv() != "PASSWORD_ACCEPTED_USER":
                    raise Exception("Invalid password")

                # first message is always full state
                self.state = data = json.loads(ws.recv())

                # Now that we have some state, we can start the threads
                if not self.threads_started:
                    for thread in threads:
                        thread.start()
                    self.threads_started = True

                while True:
                    for key, value in data.items():
                        if key == "notify":
                            type = value.pop("type")
                            for callback in self._notification_subscribers[type]:
                                callback(value)

                        else:
                            self.state[key] = value
                            for callback in self._state_subscribers[key]:
                                callback()

                    data = json.loads(ws.recv())

            except Exception:
                print("Websocket subscriber threw exception. Retrying")
                traceback.print_exc()
                time.sleep(0.1)
