import collections
import datetime
from pathlib import Path
import os
import sys
import time

import asyncio
from aiohttp import web
from aiohttp.web import Response
from aiohttp_sse import sse_response

from omxplayer import OMXPlayer


async def hello(request):
    async with sse_response(request) as resp:
        while True:
            data = 'Server Time : {}'.format(datetime.datetime.now())
            print(data)
            await resp.send(data)
            await asyncio.sleep(1)


async def start_background_tasks(app):
    app['omxplayer'] = OMXPlayer(app)
    app['omxplayer'].start()

async def shutdown_background_tasks(app):
    for task in app['omxplayer'].tasks:
        task.cancel()
        await task


async def index(request):
    d = """
        <html>
        <body>
            <script>
                var evtSource = new EventSource("/hello");
                evtSource.onmessage = function(e) {
                    document.getElementById('response').innerText = e.data
                }
            </script>
            <h1>Response from server:</h1>
            <div id="response"></div>
        </body>
    </html>
    """
    return Response(text=d, content_type='text/html')


async def videos(request):
   return web.json_response(request.app['omxplayer'].get_videos())


app = web.Application()
app.on_startup.append(start_background_tasks)
app.on_shutdown.append(shutdown_background_tasks)
app.router.add_route('GET', '/hello', hello)
app.router.add_route('GET', '/', index)
app.router.add_route('GET', '/videos', videos)


if __name__ == '__main__':
    web.run_app(app, host="0.0.0.0", port=8080)
