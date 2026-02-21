"""
API routes for OJHunt Lite web application.
"""

import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Form, Path as PathParam, Query
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field

from crawlers import discover_crawlers
from web.http_client import HttpClientDep

VJUDGE_USERNAME = os.environ.get("VJUDGE_USERNAME")
VJUDGE_PASSWORD = os.environ.get("VJUDGE_PASSWORD")

BUILD_TIME = os.environ.get("BUILD_TIME")
GIT_COMMIT_SHA = os.environ.get("GIT_COMMIT_SHA")


class CrawlerInfo(BaseModel):
    title: str = Field(..., description="Display name of the crawler")
    description: str = Field(..., description="Description of the platform")
    url: str = Field(..., description="URL of the platform")


class CrawlersListResponse(BaseModel):
    error: bool = Field(False, description="Always false for success")
    data: Dict[str, CrawlerInfo] = Field(..., description="Map of crawler name to info")


class QueryResult(BaseModel):
    solved: int = Field(..., description="Number of accepted problems")
    submissions: int = Field(..., description="Total number of submissions")
    solvedList: Optional[List[str]] = Field(
        None, description="List of solved problem IDs"
    )


class QueryResponse(BaseModel):
    error: bool = Field(False, description="Always false for success")
    data: QueryResult = Field(..., description="Query result")


class ErrorResponse(BaseModel):
    error: bool = Field(True, description="Always true for error")
    message: str = Field(..., description="Error message")


@dataclass
class QuerySuccess:
    result: Dict[str, Any]
    duration: float
    title: str


router = APIRouter()

CRAWLERS_CACHE: Dict[str, Dict[str, Any]] = {}

TEMPLATES_DIR = Path(__file__).parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def get_crawlers() -> Dict[str, Dict[str, Any]]:
    global CRAWLERS_CACHE
    if not CRAWLERS_CACHE:
        CRAWLERS_CACHE = discover_crawlers()
    return CRAWLERS_CACHE


async def _execute_query(
    client: HttpClientDep, crawler_name: str, username: str
) -> QuerySuccess:
    crawlers = get_crawlers()

    if crawler_name not in crawlers:
        raise ValueError(f"Unknown crawler '{crawler_name}'")

    crawler_info = crawlers[crawler_name]
    query_func = crawler_info["query"]
    meta = crawler_info["meta"]
    title = meta.get("title", crawler_name)

    kwargs: Dict[str, Any] = {}

    if meta.get("requires_login"):
        if VJUDGE_USERNAME and VJUDGE_PASSWORD:
            kwargs["login_user"] = VJUDGE_USERNAME
            kwargs["login_password"] = VJUDGE_PASSWORD
        else:
            raise ValueError("VJudge credentials not configured.")

    start_time = datetime.now()
    result = await query_func(client, username, **kwargs)
    duration = (datetime.now() - start_time).total_seconds()

    return QuerySuccess(result=result, duration=duration, title=title)


@router.get("/", response_class=HTMLResponse)
async def index() -> str:
    crawlers = get_crawlers()
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
    "/api/crawlers/",
    response_model=CrawlersListResponse,
    summary="List all available crawlers",
)
async def list_crawlers() -> Dict[str, Any]:
    crawlers = get_crawlers()
    data = {}
    for name, info in crawlers.items():
        meta = info["meta"]
        data[name] = CrawlerInfo(
            title=meta.get("title", name),
            description=meta.get("description", ""),
            url=meta.get("url", ""),
        )
    return CrawlersListResponse(error=False, data=data).model_dump()


@router.get(
    "/api/query/{crawler_name}/{username}",
    response_model=QueryResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Query a crawler for user statistics (JSON)",
)
async def query_crawler(
    client: HttpClientDep,
    crawler_name: str = PathParam(..., description="Name of the crawler to use"),
    username: str = PathParam(..., description="Username to query"),
) -> JSONResponse:
    try:
        qs = await _execute_query(client, crawler_name, username)
        return JSONResponse(
            QueryResponse(
                error=False,
                data=QueryResult(
                    solved=qs.result["solved"],
                    submissions=qs.result["submissions"],
                    solvedList=qs.result.get("solved_list"),
                ),
            ).model_dump()
        )
    except ValueError as e:
        return JSONResponse(
            ErrorResponse(error=True, message=str(e)).model_dump(),
            status_code=400,
        )
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        return JSONResponse(
            ErrorResponse(error=True, message=error_msg).model_dump(),
            status_code=400,
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
    crawlers = get_crawlers()
    rows = []

    if q:
        for item in q:
            parts = item.split("@")
            if len(parts) != 2:
                continue
            uname, cname = parts
            if cname == "*":
                for c_name, c_info in crawlers.items():
                    rows.append(_render_pending_row(c_name, uname, c_info["meta"]))
            elif cname in crawlers:
                rows.append(_render_pending_row(cname, uname, crawlers[cname]["meta"]))
    elif username and crawler:
        if crawler == "*":
            for c_name, c_info in crawlers.items():
                rows.append(_render_pending_row(c_name, username, c_info["meta"]))
        elif crawler in crawlers:
            rows.append(
                _render_pending_row(crawler, username, crawlers[crawler]["meta"])
            )

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
    try:
        qs = await _execute_query(client, crawler_name, username)
        return HTMLResponse(
            _render_success_row(
                crawler_name, qs.title, username, qs.result, qs.duration
            )
        )
    except ValueError as e:
        return HTMLResponse(_render_error_row(crawler_name, username, str(e)))
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        return HTMLResponse(_render_error_row(crawler_name, username, error_msg))


@router.get(
    "/htmx/canceled/{crawler_name}/{username}",
    response_class=HTMLResponse,
    summary="Get canceled row for HTMX",
)
async def get_canceled_row(
    crawler_name: str = PathParam(..., description="Name of the crawler"),
    username: str = PathParam(..., description="Username"),
) -> str:
    crawlers = get_crawlers()
    meta = crawlers.get(crawler_name, {}).get("meta", {})
    title = meta.get("title", crawler_name)
    return _render_canceled_row(crawler_name, title, username)


@router.post("/htmx/report", response_class=HTMLResponse)
async def calculate_report(r: List[str] = Form(default=[])) -> str:
    crawlers = get_crawlers()
    all_solved: set = set()
    total_submissions = 0

    for entry in r:
        parts = entry.split(":", 2)
        if len(parts) < 2:
            continue
        crawler_name = parts[0]
        submissions = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        problems = parts[2] if len(parts) > 2 else ""

        meta = crawlers.get(crawler_name, {}).get("meta", {})
        is_virtual = meta.get("is_virtual_judge", False)
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


def _render_pending_row(crawler_name: str, username: str, meta: Dict[str, Any]) -> str:
    title = meta.get("title", crawler_name)
    row_id = _generate_row_id(crawler_name, username)
    template = jinja_env.get_template("query_pending.html")
    return template.render(
        row_id=row_id,
        crawler_name=crawler_name,
        title=title,
        username=username,
    )


def _render_success_row(
    crawler_name: str,
    title: str,
    username: str,
    result: Dict[str, Any],
    duration: float,
    row_id: Optional[str] = None,
) -> str:
    if row_id is None:
        row_id = _generate_row_id(crawler_name, username)
    template = jinja_env.get_template("query_result.html")
    solved_list = result.get("solved_list") or []
    return template.render(
        row_id=row_id,
        crawler_name=crawler_name,
        title=title,
        username=username,
        solved=result["solved"],
        submissions=result["submissions"],
        duration=duration,
        solved_list=solved_list,
    )


def _render_error_row(
    crawler_name: str, username: str, error: str, row_id: Optional[str] = None
) -> str:
    crawlers = get_crawlers()
    title = crawlers.get(crawler_name, {}).get("meta", {}).get("title", crawler_name)
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
