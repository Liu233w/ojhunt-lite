"""
Crawler execution logic.
"""

from datetime import datetime
from typing import Any

import aiohttp

from ojhunt.core.models import CrawlerInfo, QueryResult


async def run_crawler(
    client: aiohttp.ClientSession, crawler: CrawlerInfo, username: str, **kwargs: Any
) -> QueryResult:
    """
    Execute a crawler and return typed QueryResult.

    Args:
        client: aiohttp ClientSession
        crawler: CrawlerInfo for the crawler to run
        username: Username to query
        **kwargs: Additional arguments passed to the crawler (e.g., login credentials)

    Returns:
        QueryResult with success status and data or error
    """
    start_time = datetime.now()
    try:
        result = await crawler.query(client, username, **kwargs)
        duration = (datetime.now() - start_time).total_seconds()
        return QueryResult(
            crawler=crawler,
            username=username,
            success=True,
            solved=result.solved,
            submissions=result.submissions,
            solved_list=result.solved_list,
            duration=duration,
        )
    except ValueError as e:
        return QueryResult(
            crawler=crawler,
            username=username,
            success=False,
            error=str(e),
        )
    except Exception as e:
        return QueryResult(
            crawler=crawler,
            username=username,
            success=False,
            error=f"{type(e).__name__}: {str(e)}",
        )
