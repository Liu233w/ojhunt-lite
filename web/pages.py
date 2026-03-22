"""
HTML page routes for OJHunt Lite web application.
"""

import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from crawlers import discover_crawlers

BUILD_TIME = os.environ.get("BUILD_TIME")
GIT_COMMIT_SHA = os.environ.get("GIT_COMMIT_SHA")

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


@router.get("/", response_class=HTMLResponse)
async def index() -> str:
    crawlers = discover_crawlers()
    crawler_data = {
        name: {
            "title": info.meta.title,
            "description": info.meta.description,
            "isVirtualJudge": info.meta.is_virtual_judge,
        }
        for name, info in sorted(crawlers.items())
    }
    template = jinja_env.get_template("index.html")
    return template.render(crawlers=crawler_data)


@router.get("/about", response_class=HTMLResponse)
async def about() -> str:
    template = jinja_env.get_template("about.html")
    build_time_str = None
    if BUILD_TIME:
        try:
            ts = int(BUILD_TIME)
            build_time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            build_time_str = BUILD_TIME
    return template.render(
        build_time=build_time_str,
        git_commit_sha=GIT_COMMIT_SHA,
    )
