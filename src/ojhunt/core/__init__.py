"""
Core module for OJHunt Lite.

Provides shared types and utilities used across CLI, web, and crawlers.
"""

from ojhunt.core.models import (
    CrawlerInfo,
    CrawlerMeta,
    CrawlerRegistry,
    CrawlerResult,
    LoginType,
    NullCrawler,
    QueryResult,
)
from ojhunt.core.runner import run_crawler
from ojhunt.core.stats import collect_solved_problems

__all__ = [
    "CrawlerInfo",
    "CrawlerMeta",
    "CrawlerRegistry",
    "CrawlerResult",
    "LoginType",
    "NullCrawler",
    "QueryResult",
    "collect_solved_problems",
    "run_crawler",
]
