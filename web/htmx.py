"""
HTMX routes for OJHunt Lite web application.
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Form, Path as PathParam, Query
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.models import CrawlerMeta, QueryResult
from core.runner import run_crawler
from crawlers import discover_crawlers
from web.http_client import HttpClientDep

VJUDGE_USERNAME = os.environ.get("VJUDGE_USERNAME")
VJUDGE_PASSWORD = os.environ.get("VJUDGE_PASSWORD")

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
    sorted_crawlers = sorted(crawlers.items(), key=lambda x: x[0])
    template = jinja_env.get_template("index.html")
    return template.render(crawlers=sorted_crawlers)


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


@router.get(
    "/htmx/row",
    response_class=HTMLResponse,
    summary="Get pending result row(s) for HTMX",
)
async def get_row_htmx(
    q: List[str] = Query(default=[]),
    username: Optional[str] = Query(None),
    crawler: Optional[str] = Query(None),
) -> str:
    crawlers = discover_crawlers()
    rows = []

    if q:
        for item in q:
            parts = item.split("@")
            if len(parts) != 2:
                continue
            uname, cname = parts
            if cname == "*":
                for c_name, c_info in crawlers.items():
                    rows.append(_render_pending_row(c_name, uname, c_info.meta))
            elif cname in crawlers:
                rows.append(_render_pending_row(cname, uname, crawlers[cname].meta))
    elif username and crawler:
        if crawler == "*":
            for c_name, c_info in crawlers.items():
                rows.append(_render_pending_row(c_name, username, c_info.meta))
        elif crawler in crawlers:
            rows.append(_render_pending_row(crawler, username, crawlers[crawler].meta))

    return "".join(rows)


@router.get(
    "/htmx/query/{crawler_name}/{username}",
    response_class=HTMLResponse,
    summary="Query a crawler for HTMX",
)
async def query_crawler_htmx(
    client: HttpClientDep,
    crawler_name: str = PathParam(..., description="Name of the crawler to use"),
    username: str = PathParam(..., description="Username to query"),
) -> HTMLResponse:
    crawlers = discover_crawlers()

    if crawler_name not in crawlers:
        return HTMLResponse(
            _render_error_row(
                crawler_name, username, f"Unknown crawler '{crawler_name}'"
            )
        )

    crawler = crawlers[crawler_name]
    result = await run_crawler(client, crawler, username)

    if result.success:
        return HTMLResponse(_render_success_row_from_result(result))
    else:
        return HTMLResponse(
            _render_error_row(crawler_name, username, result.error or "Unknown error")
        )


@router.get(
    "/htmx/canceled/{crawler_name}/{username}",
    response_class=HTMLResponse,
    summary="Get canceled row for HTMX",
)
async def get_canceled_row(
    crawler_name: str = PathParam(..., description="Name of the crawler"),
    username: str = PathParam(..., description="Username"),
) -> str:
    crawlers = discover_crawlers()
    crawler = crawlers.get(crawler_name)
    title = crawler.meta.title if crawler else crawler_name
    return _render_canceled_row(crawler_name, title, username)


@router.post("/htmx/report", response_class=HTMLResponse)
async def calculate_report(r: List[str] = Form(default=[])) -> str:
    crawlers = discover_crawlers()
    all_solved: set = set()
    total_submissions = 0

    for entry in r:
        parts = entry.split(":", 2)
        if len(parts) < 2:
            continue
        crawler_name = parts[0]
        submissions = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        problems = parts[2] if len(parts) > 2 else ""

        crawler = crawlers.get(crawler_name)
        is_virtual = crawler.meta.is_virtual_judge if crawler else False
        for problem in problems.split(",") if problems else []:
            if problem:
                if is_virtual:
                    all_solved.add(problem)
                else:
                    all_solved.add(f"{crawler_name}-{problem}")
        total_submissions += submissions

    template = jinja_env.get_template("report.html")
    return template.render(
        total_solved=len(all_solved),
        total_submissions=total_submissions,
    )


def _generate_row_id(crawler_name: str, username: str) -> str:
    return f"query-{crawler_name}-{username}-{uuid.uuid4().hex[:8]}"


def _render_pending_row(crawler_name: str, username: str, meta: CrawlerMeta) -> str:
    title = meta.title
    row_id = _generate_row_id(crawler_name, username)
    template = jinja_env.get_template("query_pending.html")
    return template.render(
        row_id=row_id,
        crawler_name=crawler_name,
        title=title,
        username=username,
    )


def _render_success_row_from_result(result: QueryResult) -> str:
    crawler_name = result.crawler.name
    title = result.crawler.meta.title
    username = result.username
    row_id = _generate_row_id(crawler_name, username)
    template = jinja_env.get_template("query_result.html")
    solved_list = result.solved_list or []
    return template.render(
        row_id=row_id,
        crawler_name=crawler_name,
        title=title,
        username=username,
        solved=result.solved,
        submissions=result.submissions,
        duration=result.duration,
        solved_list=solved_list,
    )


def _render_error_row(
    crawler_name: str, username: str, error: str, row_id: Optional[str] = None
) -> str:
    crawlers = discover_crawlers()
    crawler = crawlers.get(crawler_name)
    title = crawler.meta.title if crawler else crawler_name
    if row_id is None:
        row_id = _generate_row_id(crawler_name, username)
    template = jinja_env.get_template("query_error.html")
    return template.render(
        row_id=row_id,
        crawler_name=crawler_name,
        title=title,
        username=username,
        error=error,
    )


def _render_canceled_row(crawler_name: str, title: str, username: str) -> str:
    row_id = _generate_row_id(crawler_name, username)
    template = jinja_env.get_template("query_canceled.html")
    return template.render(
        row_id=row_id,
        crawler_name=crawler_name,
        title=title,
        username=username,
    )
