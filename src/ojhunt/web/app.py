"""
OJHunt Lite Web Application

FastAPI + HTMX web interface for querying Online Judge statistics.
"""

import random
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler as _default_http_exception_handler,
)
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from ojhunt.web.http_client import close_http_client, get_http_client, init_http_client
from ojhunt.web.api import router as api_router
from ojhunt.web.pages import router as pages_router, jinja_env
from ojhunt.web.crawler_status import start_checker, stop_checker

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


app = FastAPI(
    title="OJHunt Lite",
    description="Query Online Judge statistics across multiple platforms",
    version="0.1.0",
    lifespan=lifespan,
)

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
        template = jinja_env.get_template("404.html.jinja")
        return HTMLResponse(
            template.render(image_filename=image_filename),
            status_code=404,
        )
    return await _default_http_exception_handler(request, exc)


STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")
