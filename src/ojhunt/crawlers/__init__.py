"""
OJHunt Lite Crawlers Package

This package contains async crawlers for various Online Judge platforms.
Each crawler follows a consistent interface: an async query function that
returns a dict with keys solved, submissions, solved_list.
"""

import asyncio
import functools
import importlib
import pkgutil
from functools import cache
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict

import aiohttp

from ojhunt.core.models import CrawlerInfo, CrawlerMeta, CrawlerResult, LoginType


def query_sync(
    query_fn: Callable[..., Awaitable[dict]],
    username: str,
    **kwargs: Any,
) -> CrawlerResult:
    """
    Synchronous wrapper around an async crawler query function.

    Args:
        query_fn: The crawler's async query function (e.g. codeforces.query)
        username: Username to query
        **kwargs: Additional arguments forwarded to the query function
                  (e.g. password, login_user, login_password for login-required crawlers)

    Returns:
        CrawlerResult with solved, submissions, solved_list fields

    Example:
        from ojhunt.crawlers.codeforces import query
        from ojhunt.crawlers import query_sync
        result = query_sync(query, "tourist")
        print(result.solved, result.submissions)
    """

    async def _run() -> CrawlerResult:
        async with aiohttp.ClientSession() as session:
            return CrawlerResult.from_dict(await query_fn(session, username, **kwargs))

    return asyncio.run(_run())


__all__ = ["CrawlerResult", "discover_crawlers", "query_sync"]


def _wrap_query(fn: Callable) -> Callable[..., Awaitable[CrawlerResult]]:
    """Wrap a raw dict-returning query function to return CrawlerResult."""

    @functools.wraps(fn)
    async def wrapped(*args: Any, **kwargs: Any) -> CrawlerResult:
        return CrawlerResult.from_dict(await fn(*args, **kwargs))

    return wrapped


@cache
def discover_crawlers() -> Dict[str, CrawlerInfo]:
    """
    Auto-discover all crawlers in the package.

    Returns:
        Dictionary mapping crawler names to CrawlerInfo objects.
    """
    crawlers: Dict[str, CrawlerInfo] = {}
    package_dir = Path(__file__).parent

    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        if (
            module_name.startswith("test_")
            or module_name.endswith("_test")
            or module_name.startswith("_")
            or module_name == "conftest"
        ):
            continue

        try:
            module = importlib.import_module(
                f".{module_name}", package="ojhunt.crawlers"
            )

            if hasattr(module, "query") and hasattr(module, "__crawler_meta__"):
                meta_dict = module.__crawler_meta__
                meta = CrawlerMeta(
                    title=meta_dict.get("title", module_name),
                    description=meta_dict.get("description", ""),
                    cli_description=meta_dict.get("cli_description", ""),
                    url=meta_dict.get("url", ""),
                    is_aggregator=meta_dict.get("is_aggregator", False),
                    login_type=LoginType.from_meta(meta_dict.get("login_type")),
                    test_username=meta_dict.get("test_username", ""),
                )
                crawlers[module_name] = CrawlerInfo(
                    name=module_name,
                    meta=meta,
                    query=_wrap_query(module.query),
                )
        except (ImportError, AttributeError) as e:
            print(f"Warning: Could not load crawler '{module_name}': {e}")
            continue

    return crawlers
