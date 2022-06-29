import asyncio
import logging
import random
import weakref

from starlette.applications import Starlette
from starlette.endpoints import WebSocketEndpoint
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket

from . import settings
from .player import Player
from .util import init_pkg_logger, verify_password


logger = logging.getLogger(__name__)


def root(request):
    return PlainTextResponse("There are 40 people in the world and five of them are hamburgers")


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

    async def on_receive_unauthorized(self, websocket: WebSocket, text: str):
        if verify_password(text):
            self.authorized = True
            self.encoding = "json"
            await websocket.send_text(self.PASSWORD_ACCEPTED)
            await websocket.send_json(self.player.state)
            self.authorized_websockets.add(websocket)
        else:
            await asyncio.sleep(random.uniform(0.25, 1.25))
            await websocket.send_text(self.PASSWORD_DENIED)

    def on_receive_authorized(self, websocket: WebSocket, data: dict):
        video_request = data.get("play")
        if video_request is not None:
            self.player.request_video(video_request)

        random_request = data.get("play_random")
        if random_request:
            self.player.request_random_video()

        url = data.get("download")
        if url:
            asyncio.create_task(self.player.request_url(url))

    async def on_receive(self, websocket: WebSocket, data):
        if self.authorized:
            self.on_receive_authorized(websocket, data=data)
        else:
            await self.on_receive_unauthorized(websocket, text=data)


async def test_task():
    while True:
        print(app.state.authorized_websockets)
        await asyncio.sleep(1)


async def startup():
    init_pkg_logger()

    app.state.shutting_down = False
    app.state.authorized_websockets = weakref.WeakSet()
    app.state.player = Player(app)

    await app.state.player.startup()


async def shutdown():
    app.state.shutting_down = True
    await app.state.player.kill()


routes = [
    Route(
        "/",
        endpoint=lambda request: PlainTextResponse("There are 40 people in the world and five of them are hamburgers"),
    ),
    Mount("/test", app=StaticFiles(directory=settings.PROJECT_ROOT / "static", html=True)),
    WebSocketRoute("/backend", endpoint=BackendEndpoint),
]

app = Starlette(routes=routes, on_startup=[startup], on_shutdown=[shutdown])
