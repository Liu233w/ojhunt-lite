#!/usr/bin/env python3
"""
OJHunt Lite - Command Line Interface

A lightweight async tool for querying Online Judge statistics across multiple platforms.
"""

import asyncio
import inspect
import sys
import time

import aiohttp

from ojhunt.cli import (
    ProgressManager,
    Query,
    build_all_queries,
    check_duplicate_queries,
    parse_args,
    print_crawler_list,
    print_report,
    validate_crawlers,
    validate_credentials,
)
from ojhunt.core.models import CrawlerInfo, NullCrawler, QueryResult
from ojhunt.core.runner import run_crawler
from ojhunt.core.session import create_session
from ojhunt.crawlers import crawlers as crawler_registry


async def query_crawler(
    session: aiohttp.ClientSession,
    crawler_name: str,
    username: str,
    crawlers: dict[str, CrawlerInfo],
    progress: ProgressManager | None = None,
    progress_key: str | None = None,
    password: str | None = None,
    login_user: str | None = None,
    login_password: str | None = None,
) -> QueryResult:
    """
    Query a single crawler for user statistics.

    Args:
        session: aiohttp ClientSession
        crawler_name: Name of the crawler (e.g., 'codeforces')
        username: Username to query
        crawlers: Dictionary of available crawlers
        progress: Optional ProgressManager for live updates
        progress_key: Key for progress manager (for duplicate crawler support)
        password: Optional password (for embedded credentials in query)
        login_user: Optional login username (from -l flag)
        login_password: Optional login password (from -l flag)

    Returns:
        QueryResult with crawler results and metadata
    """
    if crawler_name not in crawlers:
        null_crawler = NullCrawler(crawler_name)
        return QueryResult(
            crawler=null_crawler,
            username=username,
            success=False,
            error=f"Unknown crawler '{crawler_name}'",
        )

    crawler = crawlers[crawler_name]

    if progress and progress_key:
        progress.start_task(progress_key)

    kwargs: dict[str, str] = {}
    if login_user is not None:
        kwargs["login_user"] = login_user
    if login_password is not None:
        kwargs["login_password"] = login_password
    if password is not None:
        kwargs["password"] = password

    sig = inspect.signature(crawler.query)
    has_login_params = "login_user" in sig.parameters
    has_password_param = "password" in sig.parameters

    if has_login_params and (login_user is None or login_password is None):
        if password is not None:
            kwargs["login_user"] = username
            kwargs["login_password"] = password
    elif not has_password_param and "password" in kwargs:
        del kwargs["password"]

    result = await run_crawler(session, crawler, username, **kwargs)

    if progress and progress_key:
        progress.complete_task(
            progress_key,
            success=result.success,
            solved=result.solved,
            duration=result.duration,
        )

    return result


async def run_queries(
    queries: list[Query],
    crawlers: dict[str, CrawlerInfo],
    crawler_logins: dict[str, tuple[str, str]],
    no_progress: bool = False,
) -> list[QueryResult]:
    """Execute all queries with live progress updates."""
    progress = ProgressManager(is_tty=not no_progress and sys.stderr.isatty())

    keys: list[str] = []
    for q in queries:
        title = crawlers[q.crawler].meta.title
        key = progress.add_task(q.crawler, title, q.username)
        keys.append(key)

    results: dict[str, QueryResult] = {}

    async with create_session() as session:
        with progress:
            tasks = []
            for q, key in zip(queries, keys):
                login_user = None
                login_password = None

                if q.crawler in crawler_logins:
                    login_user, login_password = crawler_logins[q.crawler]

                tasks.append(
                    asyncio.create_task(
                        query_crawler(
                            session,
                            q.crawler,
                            q.username,
                            crawlers,
                            progress,
                            key,
                            password=q.password,
                            login_user=login_user,
                            login_password=login_password,
                        )
                    )
                )
            for done_task in asyncio.as_completed(tasks):
                result = await done_task
                results[
                    ProgressManager._make_key(result.crawler.name, result.username)
                ] = result

    return [results[key] for key in keys]


async def _async_main() -> int:
    """Main CLI entry point."""
    args, queries, crawler_logins = parse_args()

    if args.list:
        print_crawler_list(json_output=args.json)
        return 0

    if args.all:
        queries = build_all_queries(args.default_username, crawler_registry)

    if not queries:
        print(
            "Error: no queries specified. Use -a or provide crawler names.",
            file=sys.stderr,
        )
        return 1

    check_duplicate_queries(queries)

    if not validate_crawlers(queries, crawler_registry):
        return 1

    if not validate_credentials(queries, crawler_registry, crawler_logins):
        return 1

    start_time = time.monotonic()
    results = await run_queries(
        queries, crawler_registry, crawler_logins, args.no_progress
    )
    total_duration = time.monotonic() - start_time

    return print_report(
        results, args.show_problems, total_duration, json_output=args.json
    )


def main():
    """Sync entry point for console_scripts."""
    try:
        sys.exit(asyncio.run(_async_main()))
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
