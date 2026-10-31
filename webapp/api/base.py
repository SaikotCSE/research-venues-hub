"""Plumbing shared by every ``/api/app/`` endpoint.

The React app talks to Django through these JSON endpoints using the session cookie. Conventions:

* Request bodies are JSON objects; CSRF is enforced through the ``X-CSRFToken`` header.
* Success responses are JSON objects (never bare lists) and are marked ``Cache-Control: private, no-store``.
* Errors are ``{"error": "<message>", "fields": {"<field>": ["<message>", ...]}}`` with a 4xx status.
"""

import functools
import json

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, JsonResponse
from django.utils.cache import patch_cache_control

UNSAFE = ("POST", "PUT", "PATCH", "DELETE")


class ApiError(Exception):
    def __init__(self, message, status=400, fields=None):
        super().__init__(message)
        self.message, self.status, self.fields = message, status, fields


def error_response(message, status=400, fields=None):
    body = {"error": message}
    if fields:
        body["fields"] = fields
    return JsonResponse(body, status=status)


def form_error(form):
    """Raise an :class:`ApiError` carrying a bound form's errors."""
    data = form.errors.get_json_data()
    fields = {name: [e["message"] for e in errs] for name, errs in data.items() if name != "__all__"}
    general = [e["message"] for e in data.get("__all__", [])]
    raise ApiError(general[0] if general else "Please correct the highlighted fields.", 400, fields)


def _parse_body(request):
    if not request.body:
        return {}
    data = json.loads(request.body)
    if not isinstance(data, dict):
        raise ValueError("expected an object")
    return data


def endpoint(*methods, login=False):
    """Decorate a view returning a dict (or an HttpResponse) as a JSON endpoint.

    ``methods`` defaults to GET; ``login=True`` answers 401 to anonymous callers.
    The parsed JSON body is available as ``request.data``.
    """
    allowed = methods or ("GET",)

    def decorator(view):
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method not in allowed:
                response = error_response(f"Method {request.method} not allowed.", 405)
                response["Allow"] = ", ".join(allowed)
                return response
            if login and not request.user.is_authenticated:
                return error_response("Please log in to continue.", 401)
            request.data = {}
            if request.method in UNSAFE:
                try:
                    request.data = _parse_body(request)
                except ValueError:
                    return error_response("The request body must be a JSON object.", 400)
            try:
                result = view(request, *args, **kwargs)
            except Http404 as exc:
                return error_response(str(exc) or "Not found.", 404)
            except PermissionDenied as exc:
                return error_response(str(exc) or "You do not have permission to do that.", 403)
            except ApiError as exc:
                return error_response(exc.message, exc.status, exc.fields)
            response = result if isinstance(result, HttpResponse) else JsonResponse(result)
            patch_cache_control(response, private=True, no_store=True)
            return response

        return wrapper

    return decorator


def text(data, key, limit=None):
    value = data.get(key, "")
    value = value.strip() if isinstance(value, str) else ""
    return value[:limit] if limit else value
