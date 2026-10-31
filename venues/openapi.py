"""Hand-maintained OpenAPI 3.1 description of the public and token-authenticated JSON API."""

from django.http import JsonResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

FILTER_PARAMS = [
    ("q", "string", "Full-text search over name, acronym, description, domain, publisher and tags."),
    ("type", "string", "Venue type (repeatable): Conference, Journal, Workshop/Symposium."),
    ("domain", "string", "Primary research domain (repeatable)."),
    ("tag", "string", "Subfield tag slug (repeatable), e.g. computer-vision."),
    ("core", "string", "CORE rank (repeatable): A*, A, B, C, Unranked."),
    ("ccf", "string", "CCF rank (repeatable): A, B, C, Unranked."),
    ("quartile", "string", "Journal quartile (repeatable): Q1–Q4."),
    ("min_if", "number", "Minimum journal impact factor."),
    ("country", "string", "Host country (repeatable)."),
    ("continent", "string", "Continent (repeatable)."),
    ("review", "string", "Review model (repeatable): Double-Blind, Single-Blind, Open Peer Review."),
    ("oa", "boolean", "Open-access venues only (1)."),
    ("status", "string", "Deadline status: upcoming, open, rolling, past."),
    ("within", "integer", "Only venues whose next paper deadline is within N days."),
    ("sort", "string", "deadline, impact_factor, acceptance_rate, h5_index, rank or name."),
    ("dir", "string", "asc or desc (defaults depend on the sort key)."),
]


# Shown on the API documentation page (method, path, description), grouped by audience.
API_ENDPOINTS = [
    (
        "Catalogue (public)",
        [
            ("GET", "/api/venues/", "Paginated, filterable list of venues"),
            ("GET", "/api/venues/{slug}/", "One venue with every deadline cycle"),
            ("GET", "/api/tags/", "Subfield tags with venue counts"),
            ("GET", "/api/insights/", "Aggregates behind the Insights page"),
            ("GET", "/api/stats/", "Catalogue totals and server time"),
            ("GET", "/api/suggest/?q=", "Autocomplete (up to 8 venues)"),
            ("GET", "/api/openapi.json", "OpenAPI 3.1 description of this API"),
        ],
    ),
    (
        "Your account (bearer token)",
        [
            ("GET", "/api/v1/me/", "Your profile"),
            ("GET", "/api/v1/me/targets/", "Your starred venues"),
            ("POST", "/api/v1/me/targets/", 'Star a venue — body {"slug": "cvpr"}'),
            ("DELETE", "/api/v1/me/targets/{slug}/", "Unstar a venue"),
            ("GET", "/api/v1/me/submissions/", "Your tracked submissions"),
        ],
    ),
    (
        "Feeds & exports (public)",
        [
            ("GET", "/calendar.ics?…", "iCalendar feed of every upcoming milestone matching the filters"),
            ("GET", "/feed/deadlines.atom?…", "Atom feed of the next 50 deadlines"),
            ("GET", "/export/csv/?…", "CSV export (spreadsheet friendly)"),
            ("GET", "/export/json/?…", "JSON export including all cycles (re-importable with import_venues)"),
        ],
    ),
]


def _param(name, typ, desc, where="query"):
    return {"name": name, "in": where, "required": where == "path", "description": desc, "schema": {"type": typ}}


def build_schema(server_url: str) -> dict:
    venue_ref = {"$ref": "#/components/schemas/Venue"}
    error = {"description": "Error", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}}
    filters = [_param(*p) for p in FILTER_PARAMS]
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "VenuePulse API",
            "version": "1.0.0",
            "description": "Research venues, ranks and deadlines. Public endpoints need no authentication; "
            "`/api/v1/me/*` endpoints require `Authorization: Bearer <token>` (see your profile).",
        },
        "servers": [{"url": server_url}],
        "components": {
            "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}},
            "schemas": {
                "Error": {"type": "object", "properties": {"error": {"type": "string"}}, "required": ["error"]},
                "Deadline": {
                    "type": ["object", "null"],
                    "properties": {"kind": {"type": "string", "enum": ["Abstract", "Paper"]}, "at": {"type": "string", "format": "date-time"}},
                },
                "Cycle": {
                    "type": "object",
                    "properties": {
                        k: {"type": ["string", "null"], "format": "date-time"}
                        for k in ("submission_open_date", "abstract_deadline", "submission_deadline", "notification_date", "camera_ready_date")
                    }
                    | {
                        "year": {"type": "integer"},
                        "label": {"type": "string"},
                        "timezone": {"type": "string", "enum": ["AoE", "UTC"]},
                        "is_projected": {"type": "boolean"},
                        "event_start_date": {"type": ["string", "null"], "format": "date"},
                        "event_end_date": {"type": ["string", "null"], "format": "date"},
                    },
                },
                "Venue": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "acronym": {"type": "string"},
                        "slug": {"type": "string"},
                        "venue_type": {"type": "string"},
                        "primary_domain": {"type": "string"},
                        "subfields": {"type": "array", "items": {"type": "string"}},
                        "core_rank": {"type": "string"},
                        "ccf_rank": {"type": "string"},
                        "h5_index": {"type": ["integer", "null"]},
                        "h5_median": {"type": ["integer", "null"]},
                        "impact_factor": {"type": ["number", "null"]},
                        "quartile": {"type": "string"},
                        "citescore": {"type": ["number", "null"]},
                        "sjr": {"type": ["number", "null"]},
                        "issn": {"type": "string"},
                        "is_rolling_submission": {"type": "boolean"},
                        "city": {"type": "string"},
                        "country": {"type": "string"},
                        "continent": {"type": "string"},
                        "country_flag_emoji": {"type": "string"},
                        "attendance_mode": {"type": "string"},
                        "page_limit": {"type": "string"},
                        "formatting_style": {"type": "string"},
                        "template_url": {"type": "string"},
                        "review_process": {"type": "string"},
                        "is_open_access": {"type": "boolean"},
                        "apc_cost_usd": {"type": ["integer", "null"]},
                        "acceptance_rate": {"type": ["number", "null"]},
                        "publisher": {"type": "string"},
                        "official_website": {"type": "string"},
                        "submission_portal_url": {"type": "string"},
                        "deadline_status": {"type": "string", "enum": ["open", "upcoming", "rolling", "past"]},
                        "next_deadline": {"$ref": "#/components/schemas/Deadline"},
                        "url": {"type": "string", "description": "Canonical web page"},
                        "cycles": {"type": "array", "items": {"$ref": "#/components/schemas/Cycle"}, "description": "Detail responses only"},
                    },
                },
                "VenuePage": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"},
                        "page": {"type": "integer"},
                        "num_pages": {"type": "integer"},
                        "next": {"type": ["string", "null"]},
                        "previous": {"type": ["string", "null"]},
                        "results": {"type": "array", "items": venue_ref},
                    },
                },
            },
        },
        "paths": {
            "/api/venues/": {
                "get": {
                    "summary": "List venues",
                    "tags": ["Venues"],
                    "parameters": filters + [_param("page", "integer", "Page number."), _param("page_size", "integer", "1–200, default 25.")],
                    "responses": {
                        "200": {"description": "A page of venues", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/VenuePage"}}}},
                        "304": {"description": "Not modified (ETag match)"},
                    },
                }
            },
            "/api/venues/{slug}/": {
                "get": {
                    "summary": "Venue detail with every deadline cycle",
                    "tags": ["Venues"],
                    "parameters": [_param("slug", "string", "Venue slug, e.g. neurips", "path")],
                    "responses": {"200": {"description": "Venue", "content": {"application/json": {"schema": venue_ref}}}, "404": error},
                }
            },
            "/api/tags/": {"get": {"summary": "Subfield tags with venue counts", "tags": ["Venues"], "responses": {"200": {"description": "Tags"}}}},
            "/api/stats/": {"get": {"summary": "Catalogue totals", "tags": ["Venues"], "responses": {"200": {"description": "Totals"}}}},
            "/api/insights/": {
                "get": {"summary": "Aggregates behind the Insights page", "tags": ["Venues"], "responses": {"200": {"description": "Aggregates"}}}
            },
            "/api/suggest/": {
                "get": {
                    "summary": "Autocomplete venues",
                    "tags": ["Venues"],
                    "parameters": [_param("q", "string", "Prefix or substring")],
                    "responses": {"200": {"description": "Up to 8 matches"}},
                }
            },
            "/api/v1/me/": {
                "get": {
                    "summary": "Your profile",
                    "tags": ["Me"],
                    "security": [{"bearerAuth": []}],
                    "responses": {"200": {"description": "Profile"}, "401": error},
                }
            },
            "/api/v1/me/targets/": {
                "get": {
                    "summary": "Your starred venues",
                    "tags": ["Me"],
                    "security": [{"bearerAuth": []}],
                    "responses": {"200": {"description": "Starred venues"}, "401": error},
                },
                "post": {
                    "summary": "Star a venue",
                    "tags": ["Me"],
                    "security": [{"bearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}}},
                    },
                    "responses": {
                        "201": {"description": "Starred", "content": {"application/json": {"schema": venue_ref}}},
                        "400": error,
                        "401": error,
                        "404": error,
                    },
                },
            },
            "/api/v1/me/targets/{slug}/": {
                "delete": {
                    "summary": "Unstar a venue",
                    "tags": ["Me"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [_param("slug", "string", "Venue slug", "path")],
                    "responses": {"200": {"description": "Removed"}, "401": error, "404": error},
                }
            },
            "/api/v1/me/submissions/": {
                "get": {
                    "summary": "Your tracked submissions",
                    "tags": ["Me"],
                    "security": [{"bearerAuth": []}],
                    "responses": {"200": {"description": "Submissions"}, "401": error},
                }
            },
        },
    }


@require_GET
@cache_control(max_age=3600, public=True)
def openapi_schema(request):
    response = JsonResponse(build_schema(request.build_absolute_uri("/").rstrip("/")), json_dumps_params={"indent": 2})
    response["Access-Control-Allow-Origin"] = "*"
    return response
