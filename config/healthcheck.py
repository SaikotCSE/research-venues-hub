"""Container health probe: ``python -m config.healthcheck`` exits 0 when /healthz reports OK.

Sends a Host header from DJANGO_ALLOWED_HOSTS so the request passes host validation.
"""
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    host = (os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(",")[0] or "localhost").strip().lstrip(".")
    port = os.environ.get("PORT", "8000")
    request = urllib.request.Request(f"http://127.0.0.1:{port}/healthz", headers={"Host": host, "X-Forwarded-Proto": "https"})
    try:
        with urllib.request.urlopen(request, timeout=4) as response:  # noqa: S310 - fixed local URL
            return 0 if response.status == 200 else 1
    except (urllib.error.URLError, OSError):
        return 1


if __name__ == "__main__":
    sys.exit(main())
