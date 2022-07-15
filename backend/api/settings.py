import os
from pathlib import Path

from starlette.config import Config
from starlette.datastructures import Secret


ENVFILE = os.environ.get("ENVFILE", "/.env")
conf = Config(ENVFILE)

DEBUG = conf("DEBUG", cast=bool, default=False)
INDEX_REDIRECT_URL = conf("REDIRECT_URL", default="https://jew.pizza/")
PASSWORD = conf("PASSWORD", cast=Secret)
PLAYER_BETWEEN_VIDEO_SLEEP = conf("PLAYER_BETWEEN_VIDEO_SLEEP", cast=float, default=5.0)
PLAYER_ERROR_TIMEOUT = conf("PLAYER_ERROR_TIMEOUT", cast=float, default=2.0)
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
VIDEOS_DIR = Path(conf("VIDEOS_DIR_OVERRIDE", default="/videos"))
