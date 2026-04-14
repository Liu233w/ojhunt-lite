"""
Core module for OJHunt Lite.

Provides shared types and utilities used across CLI, web, and crawlers.
"""

from ojhunt.core.models import (
    CrawlerInfo,
    CrawlerMeta,
    CrawlerResult,
    NullCrawler,
    QueryResult,
)
from ojhunt.core.runner import run_crawler
from ojhunt.core.stats import collect_solved_problems

__all__ = [
    "CrawlerInfo",
    "CrawlerMeta",
    "CrawlerResult",
    "NullCrawler",
    "QueryResult",
    "run_crawler",
    "collect_solved_problems",
]
