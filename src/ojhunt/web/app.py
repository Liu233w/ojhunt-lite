"""
OJHunt Lite Web Application

FastAPI + HTMX web interface for querying Online Judge statistics.
"""

import random
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler as _default_http_exception_handler,
)
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from ojhunt.web.api import router as api_router
from ojhunt.web.crawler_status import start_checker, stop_checker
from ojhunt.web.http_client import close_http_client, get_http_client, init_http_client
from ojhunt.web.pages import render_page
from ojhunt.web.pages import router as pages_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    init_http_client()
    client = await get_http_client()
    start_checker(client)
    yield
    await stop_checker()
    await close_http_client()


class LLMsDiscoverabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["Link"] = '</llms.txt>; rel="describedby"; type="text/plain"'
        return response


# Content-Security-Policy. Relaxed: 'unsafe-inline'/'unsafe-eval' are required because
# index.html uses inline Alpine.js expressions and the standard Alpine build evaluates them
# via Function(). Google Fonts is the only third-party origin; everything else is same-origin.
# Keep the list form: it is what carries the per-directive comments below.
_CSP = "; ".join(  # noqa: FLY002
    [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data:",
        # ReDoc (/redoc) renders its docs in a web worker spawned from a blob: URL;
        # without this the worker is blocked by the default-src 'self' fallback.
        "worker-src 'self' blob:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "upgrade-insecure-requests",
    ]
)

# Static security response headers applied to every response. HSTS omits `preload`
# intentionally — preloading is near-irreversible and requires submission at
# hstspreload.org. See docs/web.md.
_SECURITY_HEADERS = {
    "Content-Security-Policy": _CSP,
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response


# docs_url/redoc_url are disabled here and re-registered below with self-hosted
# assets. FastAPI's defaults load Swagger UI / ReDoc from cdn.jsdelivr.net, which the
# CSP (ADR 0010) blocks — the bundles are vendored under static/assets/ instead.
app = FastAPI(
    title="OJHunt Lite",
    description="Query Online Judge statistics across multiple platforms",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

# Versioned filenames of the vendored docs UI bundles (see static/assets/).
_SWAGGER_JS = "/assets/swagger-ui-bundle-5.32.8.js"
_SWAGGER_CSS = "/assets/swagger-ui-5.32.8.css"
_REDOC_JS = "/assets/redoc.standalone-2.5.3.js"


@app.get("/docs", include_in_schema=False)
async def swagger_ui_html() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url=_SWAGGER_JS,
        swagger_css_url=_SWAGGER_CSS,
        swagger_favicon_url="/favicon.ico",
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_html() -> HTMLResponse:
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url=_REDOC_JS,
        redoc_favicon_url="/favicon.ico",
        with_google_fonts=False,
    )


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LLMsDiscoverabilityMiddleware)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

app.include_router(pages_router, include_in_schema=False)
app.include_router(api_router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> Response:
    if exc.status_code == 404 and not request.url.path.startswith("/api"):
        image_filename = random.choice(["cat.jpg", "man.jpg", "metro.jpg"])
        return HTMLResponse(
            render_page(
                "404.html.jinja",
                request,
                canonical=False,
                image_filename=image_filename,
            ),
            status_code=404,
        )
    return await _default_http_exception_handler(request, exc)


STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")
