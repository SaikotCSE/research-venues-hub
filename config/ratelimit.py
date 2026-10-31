"""Small cache-backed fixed-window rate limiter.

    @ratelimit("login", methods=("POST",))
    def view(request): ...

Limits are configured in settings.RATELIMITS as "<count>/<s|m|h|d>". When a client exceeds the
limit the view is not called and a 429 response is returned (JSON for API/HTMX callers).
"""

import functools
import hashlib
import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render

PERIODS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_rate(rate: str) -> tuple[int, int]:
    count, _, period = rate.partition("/")
    return int(count), PERIODS[period.strip().lower()[0]]


def client_ip(request) -> str:
    if getattr(settings, "RATELIMIT_USE_X_FORWARDED_FOR", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def default_key(request) -> str:
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return f"user:{user.pk}"
    return f"ip:{client_ip(request)}"


def hit(group: str, key: str, rate: str) -> tuple[bool, int, int, int]:
    """Count one request. Returns (allowed, limit, remaining, reset_seconds)."""
    limit, period = parse_rate(rate)
    window = int(time.time() // period)
    digest = hashlib.sha256(key.encode()).hexdigest()[:32]
    cache_key = f"rl:{group}:{digest}:{window}"
    if cache.add(cache_key, 1, timeout=period + 1):
        count = 1
    else:
        try:
            count = cache.incr(cache_key)
        except ValueError:  # expired between add() and incr()
            cache.set(cache_key, 1, timeout=period + 1)
            count = 1
    reset = period - int(time.time() % period)
    return count <= limit, limit, max(limit - count, 0), reset


def ratelimit(group: str, *, methods=("POST",), key=default_key):
    def decorator(view):
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            if not settings.RATELIMIT_ENABLED or request.method not in methods:
                return view(request, *args, **kwargs)
            allowed, limit, remaining, reset = hit(group, key(request), settings.RATELIMITS[group])
            if not allowed:
                return too_many_requests(request, reset)
            response = view(request, *args, **kwargs)
            response["X-RateLimit-Limit"] = str(limit)
            response["X-RateLimit-Remaining"] = str(remaining)
            response["X-RateLimit-Reset"] = str(reset)
            return response

        return wrapper

    return decorator


def too_many_requests(request, retry_after: int):
    wants_json = request.path.startswith("/api/") or request.headers.get("HX-Request") == "true"
    if wants_json:
        response = JsonResponse({"error": "Too many requests. Please slow down.", "retry_after": retry_after}, status=429)
    else:
        response = render(request, "429.html", {"retry_after": retry_after}, status=429)
    response["Retry-After"] = str(retry_after)
    return response
