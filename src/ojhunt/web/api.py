"""
API routes for OJHunt Lite web application.
"""

import base64
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path as PathParam
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ojhunt.web.pdf import (
    HistoryEntry,
    PdfSettings,
    PdfSnapshot,
    compute_day_key,
    extract_data,
    generate_pdf,
    merge_history,
)

from ojhunt.core.credentials import get_login_kwargs
from ojhunt.core.models import LoginType
from ojhunt.core.models import NullCrawler
from ojhunt.core.models import QueryResult as CoreQueryResult
from ojhunt.core.runner import run_crawler
from ojhunt.core.stats import get_unique_solved
from ojhunt.crawlers import discover_crawlers
from ojhunt.web.http_client import HttpClientDep


class CrawlerInfo(BaseModel):
    title: str = Field(..., description="Display name of the crawler")
    description: str = Field(..., description="Description of the platform")
    url: str = Field(..., description="URL of the platform")
    isAggregator: bool = Field(
        False,
        description="Whether this crawler aggregates problems from other platforms (e.g. VJudge, NIT)",
    )
    isVirtualJudge: bool = Field(
        False,
        description="Deprecated alias for isAggregator. Will be removed in a future version.",
    )


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
    """Used as both the query endpoint response and the input element for POST /api/merge."""

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
    "/api/crawlers",
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
            isAggregator=meta.is_aggregator,
            isVirtualJudge=meta.is_aggregator,
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
    total_submissions = sum(r.submissions for r in core_results if r.success)
    return MergeResponse(
        uniqueSolved=get_unique_solved(core_results),
        totalSubmissions=total_submissions,
    )


# ---------------------------------------------------------------------------
# PDF models
# ---------------------------------------------------------------------------


class PdfExtractRequest(BaseModel):
    pdf_b64: str = Field(..., description="Base64-encoded PDF bytes")


class PdfExtractResponse(BaseModel):
    settings: PdfSettings = Field(..., description="Saved query settings from the PDF")
    report_date: Optional[str] = Field(
        None, description="YYYY-MM-DD of the most recent history entry (for UI display)"
    )


class PdfGenerateRequest(BaseModel):
    snapshot: PdfSnapshot
    settings: PdfSettings
    previous_pdf_b64: Optional[str] = Field(
        None, description="Base64-encoded previous PDF to merge history from"
    )


class PdfGenerateResponse(BaseModel):
    pdf_b64: str = Field(..., description="Base64-encoded generated PDF")
    date: str = Field(..., description="YYYY-MM-DD day key used for this snapshot")


# ---------------------------------------------------------------------------
# PDF endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/api/pdf/extract",
    response_model=PdfExtractResponse,
    summary="Extract settings from an OJHunt PDF report",
    description=(
        "Accepts a base64-encoded OJHunt PDF and returns the embedded settings "
        "(username and per-crawler query pairs) along with the date of the most "
        "recent history entry for UI display."
    ),
)
async def extract_pdf(body: PdfExtractRequest) -> PdfExtractResponse:
    try:
        pdf_bytes = base64.b64decode(body.pdf_b64)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid base64: {exc}")
    try:
        data = extract_data(pdf_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    report_date = data.history[-1].key if data.history else None
    return PdfExtractResponse(settings=data.settings, report_date=report_date)


@router.post(
    "/api/pdf/generate",
    response_model=PdfGenerateResponse,
    summary="Generate an OJHunt PDF progress report",
    description=(
        "Generates a PDF report for the current session. The backend computes the "
        "day key from the supplied IANA timezone. If a previous PDF is provided "
        "(base64), its history is extracted and merged with the new snapshot."
    ),
)
async def generate_pdf_report(body: PdfGenerateRequest) -> PdfGenerateResponse:
    day_key = compute_day_key(body.snapshot.timezone)
    new_entry = HistoryEntry(
        key=day_key,
        date=datetime.now(timezone.utc).isoformat(),
        totalSolved=body.snapshot.totalSolved,
        totalSubmissions=body.snapshot.totalSubmissions,
        username=body.snapshot.username,
    )

    existing_history: List[HistoryEntry] = []
    if body.previous_pdf_b64:
        try:
            prev_bytes = base64.b64decode(body.previous_pdf_b64)
            existing_history = extract_data(prev_bytes).history
        except ValueError:
            pass  # Invalid base64 (binascii.Error ⊂ ValueError) or non-OJHunt PDF

    history = merge_history(existing_history, new_entry)
    pdf_bytes = generate_pdf(body.settings, history, body.snapshot)
    return PdfGenerateResponse(
        pdf_b64=base64.b64encode(pdf_bytes).decode(),
        date=day_key,
    )
