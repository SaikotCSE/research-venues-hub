"""Tiny environment helpers (no third-party dependency) and a minimal ``.env`` loader."""

import os
from pathlib import Path


def load_dotenv(path: Path) -> None:
    """Load KEY=VALUE lines from ``path`` into os.environ without overriding real env vars."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        os.environ.setdefault(key, value)


def env(key: str, default: str = "") -> str:
    """The variable's value; unset *or empty* falls back to ``default`` (CI matrices often pass ``VAR=''``)."""
    value = os.environ.get(key)
    return default if value is None or value == "" else value


def env_bool(key: str, default: bool = False) -> bool:
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def env_list(key: str, default: list[str] | None = None) -> list[str]:
    value = os.environ.get(key)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]
