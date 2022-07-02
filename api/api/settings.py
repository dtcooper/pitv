import os
from pathlib import Path

from starlette.config import Config
from starlette.datastructures import Secret


ENVFILE = os.environ.get("ENVFILE", "/.env")
conf = Config(ENVFILE)

DEBUG = conf("DEBUG", cast=bool, default=False)
PASSWORD = conf("PASSWORD", cast=Secret)
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
VIDEOS_DIR = Path(conf("VIDEOS_DIR_OVERRIDE", default="/videos"))
INDEX_REDIRECT_URL = conf("REDIRECT_URL", default="https://jew.pizza/")
