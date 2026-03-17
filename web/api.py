"""
API routes for OJHunt Lite web application.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Path as PathParam, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field

from core.runner import run_crawler
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

TEMPLATES_DIR = Path(__file__).parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


@router.get("/", response_class=HTMLResponse)
async def index() -> str:
    template = jinja_env.get_template("index.html")
    return template.render()


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
    crawlers = discover_crawlers()
    data = {}
    for name, info in crawlers.items():
        meta = info.meta
        data[name] = CrawlerInfo(
            title=meta.title,
            description=meta.description,
            url=meta.url,
        )
    return CrawlersListResponse(error=False, data=data).model_dump()


@router.get(
    "/api/crawlers/{crawler_name}/{username}",
    response_model=QueryResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Query a crawler for user statistics",
    description="Query a specific crawler for a user's solved problems and submission count.",
)
async def query_crawler(
    request: Request,
    client: HttpClientDep,
    crawler_name: str = PathParam(..., description="Name of the crawler to use"),
    username: str = PathParam(..., description="Username to query"),
    row_id: Optional[str] = Query(None, description="Row ID for HTMX responses"),
) -> Response:
    crawlers = discover_crawlers()

    if crawler_name not in crawlers:
        error_msg = f"Unknown crawler '{crawler_name}'"
        if _is_htmx_request(request):
            return HTMLResponse(
                content=_render_error_row(crawler_name, username, error_msg, row_id)
            )
        return JSONResponse(
            content=ErrorResponse(error=True, message=error_msg).model_dump(),
            status_code=400,
        )

    crawler = crawlers[crawler_name]
    title = crawler.meta.title

    kwargs: Dict[str, str] = {}

    if crawler.meta.requires_login:
        if VJUDGE_USERNAME and VJUDGE_PASSWORD:
            kwargs["login_user"] = VJUDGE_USERNAME
            kwargs["login_password"] = VJUDGE_PASSWORD
        else:
            error_msg = "VJudge credentials not configured. Set VJUDGE_USERNAME and VJUDGE_PASSWORD environment variables."
            if _is_htmx_request(request):
                return HTMLResponse(
                    content=_render_error_row(crawler_name, username, error_msg, row_id)
                )
            return JSONResponse(
                content={"error": True, "message": error_msg}, status_code=400
            )

    result = await run_crawler(client, crawler, username, **kwargs)

    if not result.success:
        error_msg = result.error or "Unknown error"
        if _is_htmx_request(request):
            return HTMLResponse(
                content=_render_error_row(crawler_name, username, error_msg, row_id)
            )
        return JSONResponse(
            content=ErrorResponse(error=True, message=error_msg).model_dump(),
            status_code=400,
        )

    if _is_htmx_request(request):
        return HTMLResponse(
            content=_render_success_row(
                crawler_name, title, username, result, result.duration, row_id
            )
        )

    return JSONResponse(
        content=QueryResponse(
            error=False,
            data=QueryResult(
                solved=result.solved,
                submissions=result.submissions,
                solvedList=result.solved_list,
            ),
        ).model_dump()
    )


@router.post("/api/report", response_class=HTMLResponse)
async def calculate_report(request: Request) -> str:
    body = await request.json()
    results: List[Dict[str, Any]] = body.get("results", [])
    crawlers = discover_crawlers()

    all_solved: set = set()
    total_submissions = 0

    for result in results:
        if not result.get("success"):
            continue
        crawler_name = result.get("crawler", "")
        crawler = crawlers.get(crawler_name)
        is_virtual = crawler.meta.is_virtual_judge if crawler else False
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


def _render_success_row(
    crawler_name: str,
    title: str,
    username: str,
    result: Any,
    duration: float,
    row_id: Optional[str] = None,
) -> str:
    if row_id is None:
        row_id = f"query-{crawler_name}-{username}"
    template = jinja_env.get_template("query_result.html")
    solved_list = result.solved_list or []
    return template.render(
        row_id=row_id,
        crawler_name=crawler_name,
        title=title,
        username=username,
        solved=result.solved,
        submissions=result.submissions,
        duration=duration,
        solved_list=solved_list,
    )


def _render_error_row(
    crawler_name: str, username: str, error: str, row_id: Optional[str] = None
) -> str:
    crawlers = discover_crawlers()
    crawler = crawlers.get(crawler_name)
    title = crawler.meta.title if crawler else crawler_name
    if row_id is None:
        row_id = f"query-{crawler_name}-{username}"
    template = jinja_env.get_template("query_error.html")
    return template.render(
        row_id=row_id,
        crawler_name=crawler_name,
        title=title,
        username=username,
        error=error,
    )
