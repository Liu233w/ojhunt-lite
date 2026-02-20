"""
API routes for OJHunt Lite web application.
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Path as PathParam, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
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
    description="Returns a list of all available OJ crawlers with their metadata.",
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
    "/api/query/{crawler_name}/{username}",
    response_class=HTMLResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Query a crawler for user statistics",
    description="Query a specific crawler for a user's solved problems and submission count.",
)
async def query_crawler(
    request: Request,
    client: HttpClientDep,
    crawler_name: str = PathParam(..., description="Name of the crawler to use"),
    username: str = PathParam(..., description="Username to query"),
) -> Response:
    crawlers = get_crawlers()

    if crawler_name not in crawlers:
        error_msg = f"Unknown crawler '{crawler_name}'"
        if _is_htmx_request(request):
            return HTMLResponse(
                content=_render_error_row(crawler_name, username, error_msg)
            )
        return JSONResponse(
            content=ErrorResponse(error=True, message=error_msg).model_dump(),
            status_code=400,
        )

    crawler_info = crawlers[crawler_name]
    query_func = crawler_info["query"]
    meta = crawler_info["meta"]
    title = meta.get("title", crawler_name)

    try:
        start_time = datetime.now()

        kwargs: Dict[str, Any] = {}

        if meta.get("requires_login"):
            if VJUDGE_USERNAME and VJUDGE_PASSWORD:
                kwargs["login_user"] = VJUDGE_USERNAME
                kwargs["login_password"] = VJUDGE_PASSWORD
            else:
                error_msg = "VJudge credentials not configured. Set VJUDGE_USERNAME and VJUDGE_PASSWORD environment variables."
                if _is_htmx_request(request):
                    return HTMLResponse(
                        content=_render_error_row(crawler_name, username, error_msg)
                    )
                return JSONResponse(
                    content={"error": True, "message": error_msg}, status_code=400
                )

        result = await query_func(client, username, **kwargs)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        if _is_htmx_request(request):
            return HTMLResponse(
                content=_render_success_row(
                    crawler_name, title, username, result, duration
                )
            )

        return JSONResponse(
            content=QueryResponse(
                error=False,
                data=QueryResult(
                    solved=result["solved"],
                    submissions=result["submissions"],
                    solvedList=result.get("solved_list"),
                ),
            ).model_dump()
        )

    except ValueError as e:
        error_msg = str(e)
        if _is_htmx_request(request):
            return HTMLResponse(
                content=_render_error_row(crawler_name, username, error_msg)
            )
        return JSONResponse(
            content=ErrorResponse(error=True, message=error_msg).model_dump(),
            status_code=400,
        )

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        if _is_htmx_request(request):
            return HTMLResponse(
                content=_render_error_row(crawler_name, username, error_msg)
            )
        return JSONResponse(
            content=ErrorResponse(error=True, message=error_msg).model_dump(),
            status_code=400,
        )


@router.get(
    "/htmx/query/{crawler_name}/{username}",
    response_class=HTMLResponse,
    summary="Query a crawler for HTMX",
)
async def query_crawler_htmx(
    client: HttpClientDep,
    crawler_name: str = PathParam(..., description="Name of the crawler to use"),
    username: str = PathParam(..., description="Username to query"),
) -> Response:
    crawlers = get_crawlers()

    if crawler_name not in crawlers:
        error_msg = f"Unknown crawler '{crawler_name}'"
        return HTMLResponse(
            content=_render_error_row(crawler_name, username, error_msg)
        )

    crawler_info = crawlers[crawler_name]
    query_func = crawler_info["query"]
    meta = crawler_info["meta"]
    title = meta.get("title", crawler_name)

    try:
        start_time = datetime.now()

        kwargs: Dict[str, Any] = {}

        if meta.get("requires_login"):
            if VJUDGE_USERNAME and VJUDGE_PASSWORD:
                kwargs["login_user"] = VJUDGE_USERNAME
                kwargs["login_password"] = VJUDGE_PASSWORD
            else:
                error_msg = "VJudge credentials not configured."
                return HTMLResponse(
                    content=_render_error_row(crawler_name, username, error_msg)
                )

        result = await query_func(client, username, **kwargs)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        return HTMLResponse(
            content=_render_success_row(crawler_name, title, username, result, duration)
        )

    except ValueError as e:
        return HTMLResponse(content=_render_error_row(crawler_name, username, str(e)))

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        return HTMLResponse(
            content=_render_error_row(crawler_name, username, error_msg)
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
    crawlers = get_crawlers()
    meta = crawlers.get(crawler_name, {}).get("meta", {})
    title = meta.get("title", crawler_name)
    return _render_canceled_row(crawler_name, title, username)


@router.post("/api/report", response_class=HTMLResponse)
async def calculate_report(request: Request) -> str:
    body = await request.json()
    results: List[Dict[str, Any]] = body.get("results", [])
    crawlers = get_crawlers()

    all_solved: set = set()
    total_submissions = 0

    for result in results:
        if not result.get("success"):
            continue
        crawler_name = result.get("crawler", "")
        meta = crawlers.get(crawler_name, {}).get("meta", {})
        is_virtual = meta.get("is_virtual_judge", False)
        solved_list = result.get("solved_list") or []
        for problem in solved_list:
            if is_virtual:
                all_solved.add(problem)
            else:
                all_solved.add(f"{crawler_name}-{problem}")
        total_submissions += result.get("submissions", 0) or 0

    template = jinja_env.get_template("report.html")
    return template.render(
        total_solved=len(all_solved),
        total_submissions=total_submissions,
    )


def _is_htmx_request(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


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
