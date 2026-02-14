#!/usr/bin/env python3
"""
OJHunt Lite - Command Line Interface

A lightweight async tool for querying Online Judge statistics across multiple platforms.
"""

import asyncio
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

import aiohttp

from cli import (
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
from crawlers import discover_crawlers


async def query_crawler(
    session: aiohttp.ClientSession,
    crawler_name: str,
    username: str,
    crawlers: Dict[str, Dict[str, Any]],
    progress: Optional[ProgressManager] = None,
    progress_key: Optional[str] = None,
    password: Optional[str] = None,
    login_user: Optional[str] = None,
    login_password: Optional[str] = None,
) -> Dict[str, Any]:
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
        Dictionary with crawler results and metadata
    """
    if crawler_name not in crawlers:
        return {
            "crawler": crawler_name,
            "username": username,
            "error": f"Unknown crawler '{crawler_name}'",
            "success": False,
        }

    title = crawlers[crawler_name]["meta"].get("title", crawler_name)

    if progress and progress_key:
        progress.start_task(progress_key)

    try:
        query_func = crawlers[crawler_name]["query"]
        start_time = datetime.now()

        import inspect

        sig = inspect.signature(query_func)
        has_login_params = "login_user" in sig.parameters
        has_password_param = "password" in sig.parameters

        if has_login_params:
            result = await query_func(
                session,
                username,
                password=password,
                login_user=login_user,
                login_password=login_password,
            )
        elif has_password_param:
            result = await query_func(session, username, password=password)
        else:
            result = await query_func(session, username)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        if progress and progress_key:
            progress.complete_task(
                progress_key,
                success=True,
                solved=result["solved"],
                submissions=result["submissions"],
                duration=duration,
            )

        return {
            "crawler": crawler_name,
            "username": username,
            "title": title,
            "solved": result["solved"],
            "submissions": result["submissions"],
            "solved_list": result["solved_list"],
            "duration": duration,
            "success": True,
        }
    except ValueError as e:
        if progress and progress_key:
            progress.complete_task(progress_key, success=False, error=str(e))
        return {
            "crawler": crawler_name,
            "username": username,
            "title": title,
            "error": str(e),
            "success": False,
        }
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        if progress and progress_key:
            progress.complete_task(progress_key, success=False, error=error_msg)
        return {
            "crawler": crawler_name,
            "username": username,
            "title": title,
            "error": error_msg,
            "success": False,
        }


async def run_queries(
    queries: List[Query],
    crawlers: Dict[str, Dict[str, Any]],
    crawler_logins: Dict[str, Tuple[str, str]],
    no_progress: bool = False,
) -> List[Dict[str, Any]]:
    """Execute all queries with live progress updates."""
    progress = ProgressManager(is_tty=not no_progress and sys.stdout.isatty())

    keys: List[str] = []
    for q in queries:
        title = crawlers[q.crawler]["meta"].get("title", q.crawler)
        key = progress.add_task(q.crawler, title, q.username)
        keys.append(key)

    results: Dict[str, Dict[str, Any]] = {}

    async with aiohttp.ClientSession() as session:
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
                    ProgressManager._make_key(result["crawler"], result["username"])
                ] = result

    return [results[key] for key in keys]


async def main() -> int:
    """Main CLI entry point."""
    args, queries, crawler_logins = parse_args()

    if args.list:
        print_crawler_list()
        return 0

    crawlers = discover_crawlers()

    if args.all:
        queries = build_all_queries(args.default_username, crawlers)

    if not queries:
        print(
            "Error: no queries specified. Use -a or provide crawler names.",
            file=sys.stderr,
        )
        return 1

    check_duplicate_queries(queries)

    if not validate_crawlers(queries, crawlers):
        return 1

    if not validate_credentials(queries, crawlers, crawler_logins):
        return 1

    start_time = datetime.now()
    results = await run_queries(queries, crawlers, crawler_logins, args.no_progress)
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()

    return print_report(results, crawlers, args.show_problems, total_duration)


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
