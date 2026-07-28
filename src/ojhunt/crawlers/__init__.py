"""
OJHunt Lite Crawlers Package

This package contains async crawlers for various Online Judge platforms.
Each crawler follows a consistent interface: an async query function that
returns a dict with keys solved, submissions, solved_list.

Every crawler is also registered, so it can be looked up by name:

    from ojhunt.crawlers import crawlers

    crawlers["cses"]           # one crawler, by key
    crawlers.cses              # the same one, as an attribute

The registry is a dict, so iteration, len() and .items() work as usual. It is
discovered on first use, so importing one crawler module does not pay for the
other 32.
"""

__all__ = ["CrawlerRegistry", "CrawlerResult", "crawlers", "query_sync"]

import asyncio
import functools
import importlib
import pkgutil
import sys
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable, List

import aiohttp

from ojhunt.core.models import (
    CrawlerInfo,
    CrawlerMeta,
    CrawlerRegistry,
    CrawlerResult,
    LoginType,
)

if TYPE_CHECKING:
    # Load-bearing: names `crawlers` for ruff (F822 on __all__) and type checkers,
    # which cannot see through __getattr__. No runtime binding, so discovery stays
    # lazy — see ADR 0013.
    crawlers: CrawlerRegistry


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


def _wrap_query(fn: Callable) -> Callable[..., Awaitable[CrawlerResult]]:
    """Wrap a raw dict-returning query function to return CrawlerResult."""

    @functools.wraps(fn)
    async def wrapped(*args: Any, **kwargs: Any) -> CrawlerResult:
        return CrawlerResult.from_dict(await fn(*args, **kwargs))

    return wrapped


@cache
def _discover() -> CrawlerRegistry:
    """Import every crawler module in this package and build the registry.

    Memoized: the first attribute access to `crawlers` pays for the import of
    all crawler modules, and later ones reuse the same registry.
    """
    crawlers = CrawlerRegistry()
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
        except Exception as e:
            # Every consumer resolves the registry at import time, so one
            # unloadable crawler must not take down the CLI or the web app —
            # skip it and keep the rest (ADR 0013). Broad on purpose:
            # bad metadata raises ValueError, not just ImportError.
            print(
                f"Warning: Could not load crawler '{module_name}': "
                f"{type(e).__name__}: {e}",
                file=sys.stderr,
            )
            continue

    return crawlers


def __getattr__(name: str) -> Any:
    """Resolve `crawlers` on first access (PEP 562)."""
    if name == "crawlers":
        return _discover()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> List[str]:
    return sorted([*globals(), "crawlers"])
