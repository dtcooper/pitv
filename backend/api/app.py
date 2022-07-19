import asyncio
import logging
import random
import weakref

from starlette.applications import Starlette
from starlette.endpoints import WebSocketEndpoint
from starlette.responses import RedirectResponse
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket

from . import settings
from .player import Player
from .util import camel_to_underscore, init_pkg_logger, verify_password
from .videos import VideosStore


logger = logging.getLogger(__name__)


def index(request):
    return RedirectResponse(settings.INDEX_REDIRECT_URL)


class BackendEndpoint(WebSocketEndpoint):
    PASSWORD_ACCEPTED = "PASSWORD_ACCEPTED"
    PASSWORD_DENIED = "PASSWORD_DENIED"

    authorized = False
    encoding = "text"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        app: Starlette = self.scope["app"]
        self.authorized_websockets: weakref.WeakSet = app.state.authorized_websockets
        self.player: Player = app.state.player
        self.videos: VideosStore = app.state.videos

    def command_play(self, video_request):
        self.player.request_video(video_request)

    def command_play_random(self, _):
        self.player.request_random_video()

    def command_download(self, url):
        asyncio.create_task(self.player.request_url(url))

    async def command_toggle_play_r_rated(self, _):
        await self.videos.toggle_play_r_rated()

    async def command_update(self, kwargs):
        filename = kwargs.pop("filename")
        kwargs = {camel_to_underscore(k): v for k, v in kwargs.items()}
        for key in kwargs.keys():
            if key not in VideosStore.EDITABLE_ATTRS:
                logger.error(f"Invalid key for update: {key}")
                return
        await self.videos.update_video(filename, **kwargs)

    async def command_seek(self, seconds):
        await self.player.seek(seconds)

    async def command_position(self, seconds):
        await self.player.set_position(seconds)

    async def on_receive_unauthorized(self, websocket: WebSocket, text: str):
        if verify_password(text):
            self.authorized = True
            self.encoding = "json"
            await websocket.send_text(self.PASSWORD_ACCEPTED)
            await self.player.set_state(authorize_websocket=websocket)
        else:
            await asyncio.sleep(random.uniform(0.25, 1.25))
            await websocket.send_text(self.PASSWORD_DENIED)

    async def on_receive_authorized(self, websocket: WebSocket, data: dict):
        if isinstance(data, dict):
            for command, value in data.items():
                command = camel_to_underscore(command)
                method = getattr(self, f"command_{command}", None)
                if method is not None:
                    if asyncio.iscoroutinefunction(method):
                        await method(value)
                    else:
                        method(value)
                else:
                    logger.warning(f"Invalid command: {command}")
        else:
            logger.warning(f"Invalid JSON data: {data}")

    async def on_receive(self, websocket: WebSocket, data):
        if self.authorized:
            await self.on_receive_authorized(websocket, data=data)
        else:
            await self.on_receive_unauthorized(websocket, text=data)


async def startup():
    init_pkg_logger()

    app.state.shutting_down = False
    app.state.authorized_websockets = weakref.WeakSet()
    videos = app.state.videos = VideosStore(app)
    player = app.state.player = Player(app)

    await videos.startup()
    await player.startup()


def shutdown():
    app.state.shutting_down = True
    app.state.player.kill_blocking()


routes = [
    Mount("/test", app=StaticFiles(directory=settings.PROJECT_ROOT / "static", html=True)),
    WebSocketRoute("/backend", endpoint=BackendEndpoint),
    Route("/{rest:path}", endpoint=index),
]

app = Starlette(routes=routes, on_startup=[startup], on_shutdown=[shutdown])
