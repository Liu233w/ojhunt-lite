"""
OJHunt Lite crawlers — solved and submission counts from online judges.

Every crawler is a module in this package exposing an async ``query`` function.
Import one directly, or look it up in the registry:

    from ojhunt.crawlers import crawlers

    crawlers                   # {"codeforces": CrawlerInfo(...), ...}
    crawlers["cses"]           # one crawler, by key
    crawlers.cses              # the same one, as an attribute
    help(crawlers.cses)        # what it does, login, arguments

The registry is a dict, so iteration, len() and .items() work as usual; its
entries double as attributes, which tab-complete at a prompt. It is discovered
on first use, so importing one crawler module does not pay for all the others.

Synchronous use, the simplest way in:

    from ojhunt.crawlers import query_sync
    from ojhunt.crawlers.codeforces import query

    result = query_sync(query, "tourist")
    print(result.solved, result.submissions, result.solved_list)

Asynchronous use, when you already have an event loop:

    import aiohttp
    from ojhunt.crawlers import CrawlerResult
    from ojhunt.crawlers.codeforces import query

    async with aiohttp.ClientSession() as session:
        result = CrawlerResult.from_dict(await query(session, "tourist"))

Results
    Both styles produce a CrawlerResult with solved, submissions and
    solved_list. solved_list is None when the judge does not publish which
    problems a user solved, and submissions is 0 when it publishes no
    submission count.

Errors
    ValueError means the input was wrong — empty username, no such user,
    missing credentials. RuntimeError means everything else: the request
    failed, the judge answered with an error, or its output did not parse.

Login-required crawlers
    CrawlerInfo.meta.login_type says whether credentials are needed:

        LoginType.NOT_REQUIRED    profiles are public, pass nothing
        LoginType.SHARED_ACCOUNT  any account may query any user, so pass
                                  login_user and login_password
        LoginType.OWN_ACCOUNT     the judge only shows the logged-in user's
                                  own statistics, so the credentials must
                                  belong to the user being queried

    help() on a crawler names the arguments it accepts.

Aggregators
    Crawlers whose meta.is_aggregator is True (VJudge, NIT) mirror problems
    from other judges, and their solved_list entries already carry a source
    prefix such as codeforces-1A.

Copying single crawler files
    Crawler modules are self-contained and BSD-licensed, so one file can be
    copied into another project. The exceptions are nit and uva, which share a
    problem-label cache and need the whole package.
"""

__all__ = [
    "CrawlerInfo",
    "CrawlerMeta",
    "CrawlerRegistry",
    "CrawlerResult",
    "LoginType",
    "crawlers",
    "query_sync",
]

import asyncio
import functools
import importlib
import inspect
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
from ojhunt.crawlers._help import compose_query_doc, render_crawler_doc

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

    Raises:
        ValueError: If the username or credentials are unusable
        RuntimeError: If the request fails or the response cannot be parsed

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
        return CrawlerResult.coerce(await fn(*args, **kwargs))

    # functools.wraps sets __wrapped__, which inspect.signature follows, so help()
    # would otherwise advertise the raw function's dict return type. It also
    # aliases fn's own __annotations__ dict, so replace it rather than mutate it.
    wrapped.__signature__ = inspect.signature(fn).replace(
        return_annotation=CrawlerResult
    )
    wrapped.__annotations__ = {**fn.__annotations__, "return": CrawlerResult}
    return wrapped


@cache
def _discover() -> CrawlerRegistry:
    """Import every crawler module in this package and build the registry.

    Memoized: the first attribute access to `crawlers` pays for the import of
    all crawler modules, and later ones reuse the same registry.

    Every crawler carries generated documentation, so help() on one explains
    what it queries, whether it needs a login, and which arguments it takes.
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
                doc = render_crawler_doc(module_name, meta, module.query)
                query_fn = _wrap_query(module.query)
                query_fn.__doc__ = compose_query_doc(module.query.__doc__, doc)
                crawler = CrawlerInfo(name=module_name, meta=meta, query=query_fn)
                crawler.__doc__ = doc
                crawlers[module_name] = crawler
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
