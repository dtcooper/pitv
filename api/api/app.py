import asyncio
import json

from aiohttp import web
from aiohttp.web import Response
from aiohttp_sse import sse_response

from omxplayer import OMXPlayer


async def sse(request):
    omxplayer = request.app["omxplayer"]

    async with sse_response(request) as resp:
        await resp.send(json.dumps(omxplayer.state))

        queue = asyncio.Queue()
        omxplayer.state_subscriber_queues.add(queue)
        while True:
            message = await queue.get()
            await resp.send(json.dumps(message))


async def start_background_tasks(app):
    app["omxplayer"] = OMXPlayer(app)
    app["omxplayer"].start()


async def shutdown_background_tasks(app):
    for task in app["omxplayer"].tasks:
        task.cancel()
        await task


async def index(request):
    d = """
        <html>
        <body>
            <script>
                const evtSource = new EventSource("/sse");
                evtSource.onmessage = function(e) {
                    const responseElem = document.getElementById('response')
                    const mesg = `==== ${new Date} ====\\n${JSON.stringify(JSON.parse(e.data), null, 2)}`
                    responseElem.innerText = `${mesg}\\n${responseElem.innerText}`
                }
            </script>
            <h1>Response from server:</h1>
            <pre id="response"></pre>
        </body>
    </html>
    """
    return Response(text=d, content_type="text/html")


async def videos(request):
    omxplayer = request.app["omxplayer"]
    d = """
        <html>
        <body>
            <h1>Play video</h1>
        """

    if request.method == "POST":
        post = await request.post()
        video = post.get("video", "davids-bar-mitzvah.mp4")
        omxplayer.request_video(video)
        d += f"<h2>Requested: {video}</h2>"

    d += """
            <form method="POST" action="/videos">
                Movie:
                <select name="video">
        """

    for option in omxplayer.state["videos"]:
        d += f'<option value="{option}">{option}</option>'

    d += """
                </select>
                <button type="submit">Request</button>
            </form>
        </body>
        </html>
        """

    return Response(text=d, content_type="text/html")


app = web.Application()
app.on_startup.append(start_background_tasks)
app.on_shutdown.append(shutdown_background_tasks)
app.router.add_route("GET", "/sse", sse)
app.router.add_route("GET", "/", index)
app.router.add_route("GET", "/videos", videos)
app.router.add_route("POST", "/videos", videos)


if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8080)
