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

    from ojhunt.crawlers import crawlers

    result = crawlers.codeforces.query_sync("tourist")
    print(result.solved, result.submissions, result.solved_list)

    # query_sync() is also a function, taking a crawler or a query function
    from ojhunt.crawlers import query_sync
    from ojhunt.crawlers.codeforces import query

    query_sync(crawlers.codeforces, "tourist")
    query_sync(query, "tourist")

Asynchronous use, when you already have an event loop:

    from ojhunt.core.session import create_session
    from ojhunt.crawlers import CrawlerResult
    from ojhunt.crawlers.codeforces import query

    async with create_session() as session:
        result = CrawlerResult.from_dict(await query(session, "tourist"))

create_session() is a plain aiohttp.ClientSession carrying headers that tell each
judge who is querying it and how to opt out; prefer it over building your own.

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

    A copied query returns a plain dict, so the file works on its own:

        import asyncio
        import aiohttp
        from codeforces import query          # the copied file

        async def main():
            async with aiohttp.ClientSession() as session:
                print(await query(session, "tourist"))

        asyncio.run(main())

    For the blocking, typed form, copy query_sync() and CrawlerResult as well,
    with aiohttp.ClientSession() in place of create_session():

        result = query_sync(query, "tourist")
        print(result.solved, result.submissions, result.solved_list)

    A copied crawler carries no OJHunt branding by design, so identify your own
    project in the session headers.
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
from typing import TYPE_CHECKING, Any, Awaitable, Callable, List, Union

from ojhunt.core.session import create_session
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
    crawler: "Union[CrawlerInfo, Callable[..., Awaitable[Any]]]",
    username: str,
    **kwargs: Any,
) -> CrawlerResult:
    """
    Query a crawler synchronously, opening and closing a session for you.

    Takes either a crawler from the registry or a crawler module's own async
    query function, so it works just as well beside a single copied crawler
    file — swap create_session() for aiohttp.ClientSession() when copying, and
    CrawlerResult is then the only other piece needed.

    Runs its own event loop, so it cannot be called from inside a running one
    (a notebook, or any async function) — await the query function there instead.

    Args:
        crawler: A CrawlerInfo (e.g. crawlers.codeforces), or an async query
                 function (e.g. codeforces.query)
        username: Username to query
        **kwargs: Additional arguments forwarded to the query function
                  (e.g. password, login_user, login_password for login-required crawlers)

    Returns:
        CrawlerResult with solved, submissions, solved_list fields

    Raises:
        ValueError: If the username or credentials are unusable
        RuntimeError: If the request fails or the response cannot be parsed

    Example:
        from ojhunt.crawlers import crawlers, query_sync
        result = query_sync(crawlers.codeforces, "tourist")
        print(result.solved, result.submissions)

        from ojhunt.crawlers.codeforces import query
        result = query_sync(query, "tourist")
    """
    # Duck-typed and string-annotated so a copy of this function beside one
    # crawler file runs without CrawlerInfo, CrawlerMeta and LoginType.
    query_fn = getattr(crawler, "query", crawler)
    if not callable(query_fn):
        raise TypeError(
            f"expected a crawler or an async query function, got {crawler!r}; "
            'a crawler name needs a lookup first — query_sync(crawlers["cses"], ...)'
        )

    async def _run() -> CrawlerResult:
        # create_session(), not a bare ClientSession: every request OJHunt makes
        # identifies itself to the judge (ADR 0012), library calls included.
        async with create_session() as session:
            return CrawlerResult.coerce(await query_fn(session, username, **kwargs))

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
