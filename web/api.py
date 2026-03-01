"""
API routes for OJHunt Lite web application.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Path as PathParam
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.runner import run_crawler
from crawlers import discover_crawlers
from web.http_client import HttpClientDep

router = APIRouter()


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


@router.get(
    "/api/crawlers/",
    response_model=CrawlersListResponse,
    summary="List all available crawlers",
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
    crawlers = discover_crawlers()

    if crawler_name not in crawlers:
        return JSONResponse(
            ErrorResponse(
                error=True, message=f"Unknown crawler '{crawler_name}'"
            ).model_dump(),
            status_code=400,
        )

    crawler = crawlers[crawler_name]
    result = await run_crawler(client, crawler, username)

    if not result.success:
        return JSONResponse(
            ErrorResponse(
                error=True, message=result.error or "Unknown error"
            ).model_dump(),
            status_code=400,
        )

    return JSONResponse(
        QueryResponse(
            error=False,
            data=QueryResult(
                solved=result.solved,
                submissions=result.submissions,
                solvedList=result.solved_list,
            ),
        ).model_dump()
    )
