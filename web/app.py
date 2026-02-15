"""
OJHunt Lite Web Application

FastAPI + HTMX web interface for querying Online Judge statistics.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import aiohttp
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web.api import router


class AppState:
    session: aiohttp.ClientSession


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    state = AppState()
    state.session = aiohttp.ClientSession()
    app.state.web = state
    yield
    await state.session.close()


app = FastAPI(
    title="OJHunt Lite",
    description="Query Online Judge statistics across multiple platforms",
    version="0.1.0",
    lifespan=lifespan,
)

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(router)
