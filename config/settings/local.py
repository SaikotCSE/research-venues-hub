"""Development settings: DEBUG on, console email, permissive hosts."""
from config.env import env, env_list

from .base import *  # noqa: F403
from .base import INSTALLED_APPS

DEBUG = True
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-key-0f7c2a9d4e1b8f6a3c5d7e9b1a2c4e6f8a0b2d4f6")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "0.0.0.0", "testserver"])
INSTALLED_APPS = ["whitenoise.runserver_nostatic", *INSTALLED_APPS]
