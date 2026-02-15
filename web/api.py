"""
API routes for OJHunt Lite web application.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

from crawlers import discover_crawlers

VJUDGE_USERNAME = os.environ.get("VJUDGE_USERNAME")
VJUDGE_PASSWORD = os.environ.get("VJUDGE_PASSWORD")

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
    template = jinja_env.get_template("index.html")
    return template.render()


@router.get("/api/crawlers/")
async def list_crawlers() -> Dict[str, Any]:
    crawlers = get_crawlers()
    data = {}
    for name, info in crawlers.items():
        meta = info["meta"]
        data[name] = {
            "title": meta.get("title", name),
            "description": meta.get("description", ""),
            "url": meta.get("url", ""),
        }
    return {"error": False, "data": data}


@router.get("/api/crawlers/{crawler_name}/{username}")
async def query_crawler(
    crawler_name: str, username: str, request: Request, row_id: Optional[str] = None
) -> Response:
    crawlers = get_crawlers()

    if crawler_name not in crawlers:
        error_msg = f"Unknown crawler '{crawler_name}'"
        if _is_htmx_request(request):
            return HTMLResponse(
                content=_render_error_row(crawler_name, username, error_msg, row_id)
            )
        return JSONResponse(
            content={"error": True, "message": error_msg}, status_code=400
        )

    crawler_info = crawlers[crawler_name]
    query_func = crawler_info["query"]
    meta = crawler_info["meta"]
    title = meta.get("title", crawler_name)

    session: aiohttp.ClientSession = request.app.state.web.session

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
                        content=_render_error_row(
                            crawler_name, username, error_msg, row_id
                        )
                    )
                return JSONResponse(
                    content={"error": True, "message": error_msg}, status_code=400
                )

        result = await query_func(session, username, **kwargs)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        if _is_htmx_request(request):
            return HTMLResponse(
                content=_render_success_row(
                    crawler_name, title, username, result, duration, row_id
                )
            )

        return JSONResponse(
            content={
                "error": False,
                "data": {
                    "solved": result["solved"],
                    "submissions": result["submissions"],
                    "solvedList": result.get("solved_list"),
                },
            }
        )

    except ValueError as e:
        error_msg = str(e)
        if _is_htmx_request(request):
            return HTMLResponse(
                content=_render_error_row(crawler_name, username, error_msg, row_id)
            )
        return JSONResponse(
            content={"error": True, "message": error_msg}, status_code=400
        )

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        if _is_htmx_request(request):
            return HTMLResponse(
                content=_render_error_row(crawler_name, username, error_msg, row_id)
            )
        return JSONResponse(
            content={"error": True, "message": error_msg}, status_code=400
        )


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


def _render_success_row(
    crawler_name: str,
    title: str,
    username: str,
    result: Dict[str, Any],
    duration: float,
    row_id: Optional[str] = None,
) -> str:
    if row_id is None:
        row_id = f"query-{crawler_name}-{username}"
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
        row_id = f"query-{crawler_name}-{username}"
    template = jinja_env.get_template("query_error.html")
    return template.render(
        row_id=row_id,
        crawler_name=crawler_name,
        title=title,
        username=username,
        error=error,
    )
