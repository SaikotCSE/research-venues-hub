"""Resolve the Vite build manifest into <script>/<link> tags.

Production: assets are built by ``npm run build`` into ``webapp/static/webapp/`` (committed) and served by
WhiteNoise. File names already carry a content hash, so the tags reference them directly under STATIC_URL
(not through ManifestStaticFilesStorage, which would hash them a second time and break the relative imports
between chunks).

Development: set ``VITE_DEV_SERVER_URL=http://localhost:5173`` and run ``npm run dev`` for hot reloading.
"""

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings

ENTRY = "frontend/src/main.tsx"
BUILD_DIR = Path(__file__).resolve().parent / "static" / "webapp"
MANIFEST = BUILD_DIR / ".vite" / "manifest.json"


class ViteManifestError(RuntimeError):
    pass


@lru_cache(maxsize=4)
def _load(path: str, mtime: float) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def manifest() -> dict:
    try:
        return _load(str(MANIFEST), MANIFEST.stat().st_mtime)
    except FileNotFoundError as exc:
        raise ViteManifestError(f"{MANIFEST} is missing — run `npm run build` (or set VITE_DEV_SERVER_URL).") from exc


def asset_url(file: str) -> str:
    return f"{settings.STATIC_URL.rstrip('/')}/webapp/{file}"


def entry_assets(entry: str = ENTRY, page_module: str | None = None) -> dict:
    """{"script", "styles", "preloads", "fonts"} for the entry point, plus the current page's lazily loaded chunk.

    Preloading the page chunk (and the chunks it imports) lets the browser fetch it in parallel with the
    entry instead of discovering it only after the router starts.
    """
    data = manifest()
    chunk = data[entry]
    styles, preloads, seen = [], [], set()

    def walk(name, top=False):
        if name in seen or name not in data:
            return
        seen.add(name)
        item = data[name]
        styles.extend(css for css in item.get("css", []) if css not in styles)
        if not top:
            preloads.append(item["file"])
        for child in item.get("imports", []):
            walk(child)

    walk(entry, top=True)
    if page_module:
        walk(page_module)
    fonts = [a for a in chunk.get("assets", []) if a.endswith(".woff2") and "latin-wght" in a and "ext" not in a]
    return {
        "script": asset_url(chunk["file"]),
        "styles": [asset_url(s) for s in styles],
        "preloads": [asset_url(p) for p in preloads],
        "fonts": [asset_url(f) for f in fonts],
    }


def dev_server() -> str:
    return getattr(settings, "VITE_DEV_SERVER_URL", "").rstrip("/")
