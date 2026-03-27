"""
API routes for OJHunt Lite web application.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Path as PathParam
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.credentials import get_login_kwargs
from core.models import LoginType
from core.models import NullCrawler
from core.models import QueryResult as CoreQueryResult
from core.runner import run_crawler
from core.stats import collect_solved_problems
from crawlers import discover_crawlers
from web.http_client import HttpClientDep


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


class CrawlerResult(BaseModel):
    """
    Result of querying a single crawler. Used as both the query endpoint response
    and the input element for POST /api/merge.

    crawler and username are always present. On success, error=false and data is
    populated. On failure, error=true and message describes the error.
    """

    crawler: str = Field(..., description="Crawler name (e.g. 'codeforces')")
    username: str = Field(..., description="Username that was queried")
    error: bool = Field(..., description="True if the query failed")
    data: Optional[QueryResult] = Field(
        None, description="Query data (present on success)"
    )
    message: Optional[str] = Field(
        None, description="Error message (present on failure)"
    )

    @classmethod
    def from_model(cls, result: CoreQueryResult) -> "CrawlerResult":
        return cls(
            crawler=result.crawler.name,
            username=result.username,
            error=not result.success,
            data=QueryResult(
                solved=result.solved,
                submissions=result.submissions,
                solvedList=result.solved_list,
                duration=result.duration,
            )
            if result.success
            else None,
            message=result.error if not result.success else None,
        )

    def to_model(self) -> CoreQueryResult:
        crawlers = discover_crawlers()
        crawler_info = crawlers.get(self.crawler) or NullCrawler(self.crawler)
        if self.error or not self.data:
            return CoreQueryResult(
                crawler=crawler_info,
                username=self.username,
                success=False,
                error=self.message or "Unknown error",
            )
        return CoreQueryResult(
            crawler=crawler_info,
            username=self.username,
            success=True,
            solved=self.data.solved,
            submissions=self.data.submissions,
            solved_list=self.data.solvedList,
            duration=self.data.duration,
        )


router = APIRouter()


@router.get(
    "/api/crawlers/",
    response_model=CrawlersListResponse,
    summary="List all available crawlers",
    description="Returns a list of all available OJ crawlers with their metadata.",
)
async def list_crawlers() -> CrawlersListResponse:
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
    return CrawlersListResponse(error=False, data=data)


@router.get(
    "/api/crawlers/{crawler_name}/{username}",
    response_model=CrawlerResult,
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
        return JSONResponse(
            content=CrawlerResult(
                crawler=crawler_name,
                username=username,
                error=True,
                message=f"Unknown crawler '{crawler_name}'",
            ).model_dump(),
            status_code=400,
        )

    crawler = crawlers[crawler_name]

    kwargs: Dict[str, str] = {}

    if crawler.meta.login_type == LoginType.SHARED_ACCOUNT:
        login_kwargs = get_login_kwargs(crawler_name)
        if login_kwargs:
            kwargs.update(login_kwargs)
        else:
            upper = crawler_name.upper()
            return JSONResponse(
                content=CrawlerResult(
                    crawler=crawler_name,
                    username=username,
                    error=True,
                    message=(
                        f"Login credentials not configured for '{crawler_name}'. "
                        f"Set LOGIN_USERNAME__{upper} and LOGIN_PASSWORD__{upper} "
                        f"environment variables."
                    ),
                ).model_dump(),
                status_code=400,
            )

    result = await run_crawler(client, crawler, username, **kwargs)
    status_code = 200 if result.success else 400
    return JSONResponse(
        content=CrawlerResult.from_model(result).model_dump(),
        status_code=status_code,
    )


class MergeResponse(BaseModel):
    uniqueSolved: int = Field(
        ..., description="Number of unique solved problems across all crawlers"
    )
    totalSubmissions: int = Field(
        ..., description="Total submissions across all crawlers"
    )


@router.post(
    "/api/merge",
    response_model=MergeResponse,
    summary="Merge crawler results with deduplication",
    description=(
        "Accepts a list of CrawlerResult objects (verbatim responses from "
        "GET /api/crawlers/{crawler}/{username}) and returns deduplicated totals. "
        "Error results are skipped. VJudge problems are cross-referenced against "
        "other crawlers to avoid double-counting."
    ),
)
async def merge_results(results: List[CrawlerResult]) -> MergeResponse:
    core_results = [item.to_model() for item in results]
    solved_set = collect_solved_problems(core_results)
    total_submissions = sum(r.submissions for r in core_results if r.success)
    return MergeResponse(
        uniqueSolved=len(solved_set),
        totalSubmissions=total_submissions,
    )
