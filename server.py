#!/usr/bin/env python3
"""Read-only projection of the Solo Empire free SaaS catalog.

``data/free-saas-master-catalog-2026.json`` stays the
canonical generated catalog; this service pages and filters it for the Solo
Web ``/saas`` module.  It never activates a provider, reads credentials, or
claims a free tier is current: rows that the catalog marks for verification
stay marked as such.

Run locally from the repository root with::

    python3 server.py

Set ``SAAS_CATALOG_API_CATALOG_PATH`` to use another catalog file and
the ``SAAS_CATALOG_API_AUTH_*`` policy before exposing the service outside local development.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import RLock
from typing import Any, Mapping
from urllib.parse import parse_qs, urlsplit

from service_auth import AuthError, AuthPolicy, check_read_auth, is_loopback, readiness

from _sentry import capture, init_sentry

init_sentry()


SERVICE_NAME = "solo-empire-saas-catalog-api"
SCHEMA_VERSION = "solo-empire.saas-catalog.v1"
CATALOG_CONTRACT = "solo-empire.free-saas-catalog.v1"
DEFAULT_LIMIT = 30
MAX_LIMIT = 100
MAX_OFFSET = 5_000
MAX_QUERY_LENGTH = 80
MAX_FILTER_LENGTH = 60
CARD_BUCKETS = ("no_card", "card_required", "verify")
COMMERCIAL_BUCKETS = ("yes", "verify")
TEXT_FIELDS = (
    "service",
    "category",
    "subcategory",
    "free_tier_summary",
    "free_limits",
    "credit_card_required",
    "commercial_use",
    "sleeps_pauses",
    "bandwidth",
    "storage",
    "requests_compute",
    "regions",
    "custom_domain",
    "api",
    "open_standard_portability",
    "vendor_lock_in_risk",
    "overage_paid_entry",
    "free_forever",
    "self_host_alternative",
    "best_use_case",
    "replaces",
    "notes",
    "last_verified",
)


class ApiError(Exception):
    """An expected client or service error with a safe public message."""

    def __init__(
        self, status: int, message: str, *, code: str = "request_error"
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code


@dataclass(frozen=True)
class Response:
    status: int
    payload: dict[str, Any]


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def repository_root() -> Path:
    return Path(__file__).resolve().parent


def default_catalog_path() -> Path:
    configured = os.environ.get("SAAS_CATALOG_API_CATALOG_PATH")
    return (
        Path(configured).expanduser()
        if configured
        else repository_root() / "data" / "free-saas-master-catalog-2026.json"
    )


def query_value(query: Mapping[str, list[str]], field: str, max_length: int) -> str:
    value = (query.get(field) or [""])[0].strip()
    if len(value) > max_length:
        raise ApiError(400, f"{field} is too long", code="invalid_field")
    return value


def bounded_int(
    query: Mapping[str, list[str]], field: str, default: int, low: int, high: int
) -> int:
    raw = (query.get(field) or [""])[0]
    if raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ApiError(
            400, f"{field} must be an integer", code=f"invalid_{field}"
        ) from exc
    if not low <= value <= high:
        raise ApiError(
            400, f"{field} must be between {low} and {high}", code=f"invalid_{field}"
        )
    return value


def counts(values: Any) -> list[dict[str, Any]]:
    return [
        {"value": key, "count": count}
        for key, count in sorted(
            Counter(values).items(), key=lambda item: (-item[1], item[0])
        )
    ]


def card_bucket(value: str | None) -> str:
    """Collapse the catalog's free-text card column into three honest buckets."""
    text = (value or "").strip().lower()
    if text == "no":
        return "no_card"
    if text.startswith("yes") or text.startswith("billing"):
        return "card_required"
    return "verify"


def commercial_bucket(value: str | None) -> str:
    return "yes" if (value or "").strip().lower() == "yes" else "verify"


def project_service(row: Mapping[str, Any]) -> dict[str, Any]:
    service = {"id": str(row["id"])[:80]}
    for field in TEXT_FIELDS:
        value = row.get(field)
        service[field] = None if value in (None, "") else str(value)[:400]
    url = str(row.get("official_url") or "")
    service["official_url"] = url[:300] if url.startswith("https://") else None
    service["card_bucket"] = card_bucket(service["credit_card_required"])
    service["commercial_bucket"] = commercial_bucket(service["commercial_use"])
    return service


class CatalogStore:
    """Reload the catalog only when its modification time changes."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_catalog_path()
        self._lock = RLock()
        self._mtime: float | None = None
        self._snapshot: (
            tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]] | None
        ) = None

    def snapshot(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
        with self._lock:
            mtime = self.path.stat().st_mtime
            if self._snapshot is None or mtime != self._mtime:
                source_text = self.path.read_text(encoding="utf-8")
                raw = json.loads(source_text)
                if not isinstance(raw, dict) or raw.get("contract") != CATALOG_CONTRACT:
                    raise ValueError("unexpected catalog contract")
                services = [
                    project_service(row)
                    for row in raw.get("services") or []
                    if row.get("id")
                ]
                if len({service["id"] for service in services}) != len(services):
                    raise ValueError("duplicate catalog id")
                stacks = [
                    {
                        key: (
                            None
                            if row.get(key) in (None, "", "—")
                            else str(row.get(key))[:300]
                        )
                        for key in (
                            "use_case",
                            "layer",
                            "primary_free_option",
                            "fallback_1",
                            "fallback_2",
                            "why",
                        )
                    }
                    for row in raw.get("starter_stacks") or []
                ]
                source = raw.get("source") or {}
                workbook = (raw.get("summary") or {}).get("workbook") or {}
                metadata = {
                    "path": "data/free-saas-master-catalog-2026.json",
                    "revision": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
                    "snapshot_date": source.get("snapshot_date"),
                    "catalog_date": workbook.get("catalog_date"),
                    "rows_requiring_current_limit_verification": workbook.get(
                        "rows_requiring_current_limit_verification"
                    ),
                    "modified_at": datetime.fromtimestamp(mtime, timezone.utc)
                    .replace(microsecond=0)
                    .isoformat()
                    .replace("+00:00", "Z"),
                }
                self._snapshot = (services, stacks, metadata)
                self._mtime = mtime
            return self._snapshot


class SaasCatalogApi:
    """Transport-independent, read-only handler used by HTTP and tests."""

    def __init__(
        self,
        catalog_path: str | Path | None = None,
        *,
        token: str | None = None,
        environment: str | None = None,
        allowed_origins: tuple[str, ...] | None = None,
        auth_policy: AuthPolicy | None = None,
    ) -> None:
        self.store = CatalogStore(catalog_path)
        self.token = (
            token
            if token is not None
            else os.environ.get("SAAS_CATALOG_API_TOKEN", "").strip()
        )
        self.environment = (
            (environment or os.environ.get("SAAS_CATALOG_API_ENV", "development"))
            .strip()
            .lower()
        )
        self.auth_policy = auth_policy or AuthPolicy.from_env(
            "SAAS_CATALOG_API_", "saas-catalog-api", "saas:read"
        )
        configured_origins = os.environ.get(
            "SAAS_CATALOG_API_CORS_ORIGINS",
            "http://127.0.0.1:3600,http://localhost:3600",
        )
        self.allowed_origins = allowed_origins or tuple(
            item.strip() for item in configured_origins.split(",") if item.strip()
        )

    def _check_read_auth(self, headers: Mapping[str, str]) -> None:
        try:
            check_read_auth(
                self.auth_policy,
                headers,
                environment=self.environment,
                token=self.token,
            )
        except AuthError as exc:
            raise ApiError(exc.status, exc.message, code=exc.code) from None

    def _ready(self) -> Response:
        status, payload = readiness(self.auth_policy, self.environment, self.store)
        return Response(status, payload)

    def _overview(self, query: Mapping[str, list[str]]) -> Response:
        category = query_value(query, "category", MAX_FILTER_LENGTH)
        card = query_value(query, "card", MAX_FILTER_LENGTH)
        commercial = query_value(query, "commercial", MAX_FILTER_LENGTH)
        q = query_value(query, "q", MAX_QUERY_LENGTH).casefold()
        if card and card not in CARD_BUCKETS:
            raise ApiError(
                400,
                f"card must be one of {', '.join(CARD_BUCKETS)}",
                code="invalid_field",
            )
        if commercial and commercial not in COMMERCIAL_BUCKETS:
            raise ApiError(
                400,
                f"commercial must be one of {', '.join(COMMERCIAL_BUCKETS)}",
                code="invalid_field",
            )
        limit = bounded_int(query, "limit", DEFAULT_LIMIT, 1, MAX_LIMIT)
        offset = bounded_int(query, "offset", 0, 0, MAX_OFFSET)
        services, stacks, metadata = self.store.snapshot()
        matched = [
            service
            for service in services
            if (not category or service["category"] == category)
            and (not card or service["card_bucket"] == card)
            and (not commercial or service["commercial_bucket"] == commercial)
            and (
                not q
                or any(
                    q in str(service[field] or "").casefold()
                    for field in (
                        "id",
                        "service",
                        "subcategory",
                        "best_use_case",
                        "replaces",
                    )
                )
            )
        ]
        return Response(
            200,
            {
                "schema_version": SCHEMA_VERSION,
                "generated_at": utc_now(),
                "source": metadata,
                "summary": {
                    "services_total": len(services),
                    "services_matched": len(matched),
                    "categories": len({service["category"] for service in services}),
                    "no_card": sum(
                        1 for service in services if service["card_bucket"] == "no_card"
                    ),
                    "commercial_yes": sum(
                        1
                        for service in services
                        if service["commercial_bucket"] == "yes"
                    ),
                    "needs_verification": sum(
                        1 for service in services if service["card_bucket"] == "verify"
                    ),
                },
                "signals": {
                    "categories": counts(service["category"] for service in services),
                    "card": [
                        {
                            "value": key,
                            "count": sum(
                                1
                                for service in services
                                if service["card_bucket"] == key
                            ),
                        }
                        for key in CARD_BUCKETS
                    ],
                    "commercial": [
                        {
                            "value": key,
                            "count": sum(
                                1
                                for service in services
                                if service["commercial_bucket"] == key
                            ),
                        }
                        for key in COMMERCIAL_BUCKETS
                    ],
                    "lock_in": counts(
                        service["vendor_lock_in_risk"] or "unknown"
                        for service in services
                    ),
                },
                "filters": {
                    "category": category,
                    "card": card,
                    "commercial": commercial,
                    "q": q,
                    "limit": limit,
                    "offset": offset,
                },
                "starter_stacks": stacks,
                "services": matched[offset : offset + limit],
                "boundary": "catalog snapshot only; verify current limits and terms before activating any provider",
            },
        )

    def handle(
        self, method: str, target: str, *, headers: Mapping[str, str] | None = None
    ) -> Response:
        request_headers = {
            str(key).lower(): str(value) for key, value in (headers or {}).items()
        }
        parsed = urlsplit(target)
        path = parsed.path.rstrip("/") or "/"
        try:
            if method == "OPTIONS":
                return Response(204, {})
            if method == "GET" and path == "/ready":
                return self._ready()
            if method == "GET" and path == "/health":
                return Response(
                    200,
                    {
                        "status": "ok",
                        "service": SERVICE_NAME,
                        "schema_version": SCHEMA_VERSION,
                        "timestamp": utc_now(),
                    },
                )
            if path == "/api/v1/saas":
                self._check_read_auth(request_headers)
                if method != "GET":
                    raise ApiError(
                        405, "SaaS catalog is read-only", code="method_not_allowed"
                    )
                return self._overview(parse_qs(parsed.query))
            raise ApiError(404, "route not found", code="not_found")
        except ApiError as exc:
            return Response(
                exc.status, {"error": {"code": exc.code, "message": exc.message}}
            )
        except (OSError, ValueError, TypeError, KeyError):
            return Response(
                503,
                {
                    "error": {
                        "code": "catalog_unavailable",
                        "message": "SaaS catalog could not be read",
                    }
                },
            )
        except Exception as exc:
            capture(exc)  # no-op unless SENTRY_DSN is set
            return Response(
                500,
                {
                    "error": {
                        "code": "internal_error",
                        "message": "SaaS catalog service could not complete the request",
                    }
                },
            )


class SaasCatalogRequestHandler(BaseHTTPRequestHandler):
    api = SaasCatalogApi()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def _dispatch(self) -> None:
        origin = self.headers.get("Origin")
        if origin and origin not in self.api.allowed_origins:
            self._write(
                Response(
                    403,
                    {
                        "error": {
                            "code": "origin_not_allowed",
                            "message": "origin is not allowed",
                        }
                    },
                ),
                origin=None,
            )
            return
        self._write(
            self.api.handle(
                self.command, self.path, headers=dict(self.headers.items())
            ),
            origin=origin,
        )

    def _write(self, response: Response, *, origin: str | None) -> None:
        encoded = (
            b""
            if response.status == HTTPStatus.NO_CONTENT
            else json.dumps(
                response.payload, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
        )
        self.send_response(response.status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(encoded)))
        if origin and origin in self.api.allowed_origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        if self.command == "OPTIONS":
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Accept, Authorization")
        self.end_headers()
        if response.status != HTTPStatus.NO_CONTENT:
            self.wfile.write(encoded)

    do_GET = _dispatch
    do_OPTIONS = _dispatch
    do_POST = _dispatch
    do_PUT = _dispatch
    do_PATCH = _dispatch
    do_DELETE = _dispatch


def main() -> None:
    parser = argparse.ArgumentParser(description="Solo Empire free SaaS catalog API")
    parser.add_argument(
        "--host", default=os.environ.get("SAAS_CATALOG_API_HOST", "127.0.0.1")
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(
            os.environ.get("SAAS_CATALOG_API_PORT", os.environ.get("PORT", "3490"))
        ),
    )
    parser.add_argument(
        "--catalog",
        default=None,
        help="catalog JSON; defaults to SAAS_CATALOG_API_CATALOG_PATH or data/free-saas-master-catalog-2026.json",
    )
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if args.catalog:
        SaasCatalogRequestHandler.api = SaasCatalogApi(args.catalog)
    if not is_loopback(args.host):
        SaasCatalogRequestHandler.api.environment = "production"
        if not SaasCatalogRequestHandler.api.auth_policy.ready:
            parser.error(
                "a non-loopback --host requires valid SAAS_CATALOG_API_AUTH_* configuration"
            )
    server = ThreadingHTTPServer((args.host, args.port), SaasCatalogRequestHandler)
    print(f"{SERVICE_NAME} running on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
