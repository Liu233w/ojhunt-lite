"""
HTML page routes for OJHunt Lite web application.
"""

import os
import secrets
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from crawlers import discover_crawlers
from web.crawler_status import get_all_status, CrawlerAvailability, CheckStatus

BUILD_TIME = os.environ.get("BUILD_TIME")
GIT_COMMIT_SHA = os.environ.get("GIT_COMMIT_SHA")
STATIC_VERSION = GIT_COMMIT_SHA or BUILD_TIME or secrets.token_hex(8)

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
    return template.render(crawlers=crawler_data, static_version=STATIC_VERSION)


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


@router.get("/llms.txt", response_class=PlainTextResponse)
async def llms_txt(request: Request) -> str:
    base = str(request.base_url).rstrip("/")
    crawlers = discover_crawlers()
    crawler_names = sorted(crawlers.keys())
    template = jinja_env.get_template("llms.txt")
    return template.render(
        base=base,
        crawler_count=len(crawler_names),
        crawler_names=", ".join(crawler_names),
    )


@router.get("/crawlers", response_class=HTMLResponse)
async def crawlers_page() -> str:
    crawlers = discover_crawlers()
    availability = get_all_status()
    crawler_list = []
    for name, info in sorted(crawlers.items()):
        crawler_list.append(
            {
                "name": name,
                "title": info.meta.title,
                "description": info.meta.description,
                "url": info.meta.url,
                "availability": availability.get(
                    name, CrawlerAvailability(CheckStatus.WAITING)
                ),
            }
        )
    template = jinja_env.get_template("crawlers.html")
    return template.render(crawlers=crawler_list)
