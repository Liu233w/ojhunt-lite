"""
Core models for OJHunt Lite.

These types are used across CLI, web, and crawler modules.
"""

from dataclasses import dataclass
from typing import Awaitable, Callable, List, Optional

import aiohttp


@dataclass
class CrawlerMeta:
    """Metadata for a crawler."""

    title: str
    description: str = ""
    url: str = ""
    is_virtual_judge: bool = False
    requires_login: bool = False
    requires_password: bool = False
    test_username: str = ""


@dataclass
class CrawlerInfo:
    """A crawler with metadata and query function."""

    name: str
    meta: CrawlerMeta
    query: Callable[..., Awaitable[dict]]


@dataclass
class QueryResult:
    """Result of querying a crawler."""

    crawler: CrawlerInfo
    username: str
    success: bool
    solved: int = 0
    submissions: int = 0
    solved_list: Optional[List[str]] = None
    duration: float = 0.0
    error: Optional[str] = None


class NullCrawler(CrawlerInfo):
    """A null crawler for unknown crawler names."""

    def __init__(self, name: str):
        super().__init__(
            name=name,
            meta=CrawlerMeta(title=name),
            query=self._null_query,
        )

    async def _null_query(self, session: aiohttp.ClientSession, username: str) -> dict:
        raise RuntimeError("NullCrawler cannot execute queries")
