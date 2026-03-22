"""
API routes for OJHunt Lite web application.
"""

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Path as PathParam
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.runner import run_crawler
from crawlers import discover_crawlers
from web.http_client import HttpClientDep

VJUDGE_USERNAME = os.environ.get("VJUDGE_USERNAME")
VJUDGE_PASSWORD = os.environ.get("VJUDGE_PASSWORD")


class CrawlerInfo(BaseModel):
    title: str = Field(..., description="Display name of the crawler")
    description: str = Field(..., description="Description of the platform")
    url: str = Field(..., description="URL of the platform")
    isVirtualJudge: bool = Field(False, description="Whether this is a virtual judge")


class CrawlersListResponse(BaseModel):
    error: bool = Field(False, description="Always false for success")
    data: Dict[str, CrawlerInfo] = Field(..., description="Map of crawler name to info")


class QueryResult(BaseModel):
    solved: int = Field(..., description="Number of accepted problems")
    submissions: int = Field(..., description="Total number of submissions")
    solvedList: Optional[List[str]] = Field(
        None, description="List of solved problem IDs"
    )
    duration: float = Field(0, description="Query duration in seconds")


class QueryResponse(BaseModel):
    error: bool = Field(False, description="Always false for success")
    data: QueryResult = Field(..., description="Query result")


class ErrorResponse(BaseModel):
    error: bool = Field(True, description="Always true for error")
    message: str = Field(..., description="Error message")


router = APIRouter()


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
            isVirtualJudge=meta.is_virtual_judge,
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
    client: HttpClientDep,
    crawler_name: str = PathParam(..., description="Name of the crawler to use"),
    username: str = PathParam(..., description="Username to query"),
) -> JSONResponse:
    crawlers = discover_crawlers()

    if crawler_name not in crawlers:
        error_msg = f"Unknown crawler '{crawler_name}'"
        return JSONResponse(
            content=ErrorResponse(error=True, message=error_msg).model_dump(),
            status_code=400,
        )

    crawler = crawlers[crawler_name]

    kwargs: Dict[str, str] = {}

    if crawler.meta.requires_login:
        if VJUDGE_USERNAME and VJUDGE_PASSWORD:
            kwargs["login_user"] = VJUDGE_USERNAME
            kwargs["login_password"] = VJUDGE_PASSWORD
        else:
            error_msg = "VJudge credentials not configured. Set VJUDGE_USERNAME and VJUDGE_PASSWORD environment variables."
            return JSONResponse(
                content={"error": True, "message": error_msg}, status_code=400
            )

    result = await run_crawler(client, crawler, username, **kwargs)

    if not result.success:
        error_msg = result.error or "Unknown error"
        return JSONResponse(
            content=ErrorResponse(error=True, message=error_msg).model_dump(),
            status_code=400,
        )

    return JSONResponse(
        content=QueryResponse(
            error=False,
            data=QueryResult(
                solved=result.solved,
                submissions=result.submissions,
                solvedList=result.solved_list,
                duration=result.duration,
            ),
        ).model_dump()
    )
