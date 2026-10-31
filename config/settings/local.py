"""Development settings: DEBUG on, console email, permissive hosts."""

from config.env import env, env_list

from .base import *  # noqa: F403
from .base import INSTALLED_APPS

DEBUG = True
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-key-0f7c2a9d4e1b8f6a3c5d7e9b1a2c4e6f8a0b2d4f6")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "0.0.0.0", "testserver"])
INSTALLED_APPS = ["whitenoise.runserver_nostatic", *INSTALLED_APPS]

# `npm run dev`: let the page load modules, styles and fonts from the Vite dev server and open its HMR socket.
from .base import CSP_DIRECTIVES, VITE_DEV_SERVER_URL  # noqa: E402

if VITE_DEV_SERVER_URL:
    _ws = VITE_DEV_SERVER_URL.replace("http", "ws", 1)
    CSP_DIRECTIVES = {
        **CSP_DIRECTIVES,
        "script-src": [*CSP_DIRECTIVES["script-src"], VITE_DEV_SERVER_URL],
        "style-src": [*CSP_DIRECTIVES["style-src"], VITE_DEV_SERVER_URL],
        "font-src": [*CSP_DIRECTIVES["font-src"], VITE_DEV_SERVER_URL],
        "img-src": [*CSP_DIRECTIVES["img-src"], VITE_DEV_SERVER_URL],
        "connect-src": [*CSP_DIRECTIVES["connect-src"], VITE_DEV_SERVER_URL, _ws],
    }
