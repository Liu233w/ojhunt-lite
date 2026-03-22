"""
OJHunt Lite Web Application

FastAPI + HTMX web interface for querying Online Judge statistics.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web.http_client import close_http_client, get_http_client, init_http_client
from web.api import router as api_router
from web.pages import router as pages_router
from web.crawler_status import start_checker, stop_checker

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    init_http_client()
    client = await get_http_client()
    start_checker(client)
    yield
    await stop_checker()
    await close_http_client()


app = FastAPI(
    title="OJHunt Lite",
    description="Query Online Judge statistics across multiple platforms",
    version="0.1.0",
    lifespan=lifespan,
)

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(pages_router)
app.include_router(api_router)
