import asyncio
import logging
import random
import weakref

from starlette.applications import Starlette
from starlette.endpoints import WebSocketEndpoint
from starlette.responses import RedirectResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket

from . import settings
from .player import Player
from .remote import Remote
from .util import (
    camel_to_underscore,
    cancel_all_background_tasks,
    convert_obj_to_camel,
    init_pkg_logger,
    run_in_background,
    search_imdb,
    verify_password,
)
from .videos import VideosStore


logger = logging.getLogger(__name__)


def index(request):
    return RedirectResponse(settings.INDEX_REDIRECT_URL)


def admins_only_command(method):
    method._admin_only = True
    return method


def wants_websocket_command(method):
    method._wants_websocket = True
    return method


class BackendEndpoint(WebSocketEndpoint):
    PASSWORD_ACCEPTED_USER = "PASSWORD_ACCEPTED_USER"
    PASSWORD_ACCEPTED_ADMIN = "PASSWORD_ACCEPTED_ADMIN"
    PASSWORD_DENIED = "PASSWORD_DENIED"

    authorized = False
    is_admin = False
    encoding = "text"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        app: Starlette = self.scope["app"]
        self.player: Player = app.state.player
        self.videos: VideosStore = app.state.videos

    def command_play(self, video_request):
        self.player.request_video(video_request)

    def command_play_random(self, _):
        self.player.request_random_video()

    def command_download(self, url):
        run_in_background(self.player.request_url(url))

    async def command_toggle_play_r_rated(self, _):
        await self.videos.toggle_play_r_rated()

    async def command_toggle_mute(self, _):
        await self.videos.toggle_mute()

    async def command_play_pause(self, _):
        await self.player.play_pause()

    @admins_only_command
    async def command_update(self, kwargs):
        filename = kwargs.pop("filename")
        kwargs = {camel_to_underscore(k): v for k, v in kwargs.items()}
        for key in kwargs.keys():
            if key not in VideosStore.EDITABLE_ATTRS:
                logger.error(f"Invalid key for update: {key}")
                return
        await self.videos.update_video(filename, **kwargs)

    @admins_only_command
    @wants_websocket_command
    async def command_search_imdb(self, websocket: WebSocket, path_title):
        path, title = path_title
        results = await search_imdb(title)
        response = {"imdb": {"path": path, "results": results, "working": False}}
        if not results:
            await self.player.notify(
                single_websocket=websocket, type="alert", message="No results on IMDB found!", level="error"
            )
        await websocket.send_json(convert_obj_to_camel(response))

    async def command_seek(self, seconds):
        await self.player.seek(seconds)

    async def command_position(self, seconds):
        await self.player.set_position(seconds)

    async def on_receive_unauthorized(self, websocket: WebSocket, text: str):
        is_user, self.is_admin = verify_password(text)
        if is_user or self.is_admin:
            self.encoding = "json"
            await websocket.send_text(self.PASSWORD_ACCEPTED_ADMIN if self.is_admin else self.PASSWORD_ACCEPTED_USER)
            await self.player.set_state(authorize_websocket=websocket)
            self.authorized = True

        else:
            await asyncio.sleep(random.uniform(0.5, 2.0))
            await websocket.send_text(self.PASSWORD_DENIED)

    async def on_receive_authorized(self, websocket: WebSocket, data: dict):
        if isinstance(data, dict):
            for command, value in data.items():
                command = camel_to_underscore(command)
                method = getattr(self, f"command_{command}", None)
                if method is not None and (not getattr(method, "_admin_only", False) or self.is_admin):
                    args = (websocket, value) if getattr(method, "_wants_websocket", False) else (value,)
                    if asyncio.iscoroutinefunction(method):
                        await method(*args)
                    else:
                        method(*args)
                else:
                    logger.warning(f"Invalid command (admin={self.is_admin}): {command}")
        else:
            logger.warning(f"Invalid JSON data: {data}")

    async def on_receive(self, websocket: WebSocket, data):
        if self.authorized:
            await self.on_receive_authorized(websocket, data=data)
        else:
            await self.on_receive_unauthorized(websocket, text=data)


async def startup():
    init_pkg_logger()

    app.state.authorized_websockets = weakref.WeakSet()
    videos = app.state.videos = VideosStore(app)
    player = app.state.player = Player(app)
    remote = app.state.remote = Remote(app)

    await videos.startup()
    await player.startup()
    await remote.startup()


def shutdown():
    app.state.player.kill_blocking()
    cancel_all_background_tasks()


routes = [
    WebSocketRoute("/backend", endpoint=BackendEndpoint),
    Route("/{rest:path}", endpoint=index),
]

app = Starlette(routes=routes, on_startup=[startup], on_shutdown=[shutdown])
