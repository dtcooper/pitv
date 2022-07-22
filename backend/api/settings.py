import os
from pathlib import Path

from starlette.config import Config
from starlette.datastructures import Secret


ENVFILE = os.environ.get("ENVFILE", "/.env")
conf = Config(ENVFILE)

DEBUG = conf("DEBUG", cast=bool, default=False)
ALSA_DEVICE = conf("ALSA_DEVICE", default="HDMI")
INDEX_REDIRECT_URL = conf("REDIRECT_URL", default="https://jew.pizza/")
PASSWORD_ADMIN = conf("PASSWORD_ADMIN", cast=Secret)
PASSWORD_USER = conf("PASSWORD_USER", cast=Secret)
PLAYER_ERROR_TIMEOUT = conf("PLAYER_ERROR_TIMEOUT", cast=float, default=2.0)
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
TITLE = conf("TITLE", default="Raspberry Pi Video Player")
VIDEOS_DIR = Path(conf("VIDEOS_DIR_OVERRIDE", default="/videos"))
