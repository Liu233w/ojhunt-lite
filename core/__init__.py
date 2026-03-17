"""
Core module for OJHunt Lite.

Provides shared types and utilities used across CLI, web, and crawlers.
"""

from core.models import CrawlerInfo, CrawlerMeta, NullCrawler, QueryResult
from core.runner import run_crawler
from core.stats import collect_solved_problems

__all__ = [
    "CrawlerInfo",
    "CrawlerMeta",
    "NullCrawler",
    "QueryResult",
    "run_crawler",
    "collect_solved_problems",
]
