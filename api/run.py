#!/usr/bin/env python

from aiohttp import web
from api.app import app


web.run_app(app, host="0.0.0.0", port=8080)
