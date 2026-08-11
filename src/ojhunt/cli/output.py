"""
CLI output and validation functions for OJHunt Lite.
"""

import json
import sys
from collections import Counter

from rich.console import Console
from rich.table import Table

from ojhunt.cli.models import Query
from ojhunt.core.models import CrawlerInfo, LoginType, QueryResult
from ojhunt.core.stats import get_unique_solved
from ojhunt.crawlers import crawlers as crawler_registry


def check_duplicate_queries(queries: list[Query]) -> None:
    """Check for duplicate queries and print warning to stderr."""
    counter = Counter((q.crawler, q.username) for q in queries)
    for (crawler, username), count in counter.items():
        if count > 1:
            print(
                f"Warning: duplicate query '{username}@{crawler}' (will run {count} times)",
                file=sys.stderr,
            )


def validate_crawlers(queries: list[Query], crawlers: dict[str, CrawlerInfo]) -> bool:
    """Validate that all queried crawlers exist."""
    unknown = {q.crawler for q in queries if q.crawler not in crawlers}
    if unknown:
        print(
            f"Error: unknown crawler(s): {', '.join(sorted(unknown))}",
            file=sys.stderr,
        )
        print("Run 'ojhunt --list' to see available crawlers.", file=sys.stderr)
        return False
    return True


def validate_credentials(
    queries: list[Query],
    crawlers: dict[str, CrawlerInfo],
    crawler_logins: dict[str, tuple[str, str]],
) -> bool:
    """
    Validate that credential requirements are met for each query.

    For shared_account crawlers (e.g., VJudge):
        - If query has password: login as that user, query that user
        - If query has no password but -l flag provided: use flag credentials
        - If neither: error

    For own_account crawlers:
        - Password must be provided in query

    Args:
        queries: List of Query objects
        crawlers: Dictionary of CrawlerInfo objects
        crawler_logins: Login credentials from -l flag, keyed by crawler name

    Returns:
        True if all validations pass, False otherwise
    """
    for q in queries:
        meta = crawlers[q.crawler].meta

        if meta.login_type == LoginType.SHARED_ACCOUNT:
            has_query_creds = q.password is not None
            has_flag_creds = q.crawler in crawler_logins

            if has_query_creds and has_flag_creds:
                print(
                    f"Error: duplicate credentials for '{q.crawler}'. "
                    f"Use either user:pass@{q.crawler} or -l user:pass@{q.crawler}, not both.",
                    file=sys.stderr,
                )
                return False

            if not has_query_creds and not has_flag_creds:
                print(
                    f"Error: crawler '{q.crawler}' requires login credentials. "
                    f"Use user:pass@{q.crawler} or -l user:pass@{q.crawler}",
                    file=sys.stderr,
                )
                return False

        elif meta.login_type == LoginType.OWN_ACCOUNT:
            if q.password is None:
                print(
                    f"Error: crawler '{q.crawler}' requires a password. "
                    f"Use username:password@{q.crawler}",
                    file=sys.stderr,
                )
                return False

        else:
            if q.password is not None:
                print(
                    f"Error: crawler '{q.crawler}' does not require credentials",
                    file=sys.stderr,
                )
                return False

    return True


def print_report(
    results: list[QueryResult],
    show_problems: bool,
    total_duration: float,
    json_output: bool = False,
) -> int:
    """Print the final report and return exit code."""
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    unique_solved = get_unique_solved(results)
    total_submissions = sum(r.submissions for r in successful)

    if json_output:
        result_list = []
        for r in results:
            entry: dict = {
                "crawler": r.crawler.name,
                "title": r.crawler.meta.title,
                "username": r.username,
                "success": r.success,
            }
            if r.success:
                entry["solved"] = r.solved
                entry["submissions"] = r.submissions
                entry["solved_list"] = r.solved_list
                entry["duration"] = r.duration
            else:
                entry["error"] = r.error
                entry["duration"] = r.duration
            result_list.append(entry)

        output = {
            "results": result_list,
            "summary": {
                "unique_solved": unique_solved,
                "total_submissions": total_submissions,
                "ok": len(successful),
                "failed": len(failed),
                "duration": total_duration,
            },
        }
        print(json.dumps(output, indent=2))
        return 0 if not failed else 1

    print()
    print(f"Total: {unique_solved} solved / {total_submissions} submissions")
    print()

    console = Console()

    table = Table()
    table.add_column("Crawler")
    table.add_column("Username")
    table.add_column("Solved", justify="right", no_wrap=True)
    table.add_column("Submissions", justify="right", no_wrap=True)
    table.add_column("Status")

    for result in results:
        if result.success:
            table.add_row(
                result.crawler.meta.title,
                result.username,
                str(result.solved),
                str(result.submissions),
                f"OK ({result.duration:.2f}s)",
            )
        else:
            table.add_row(
                result.crawler.meta.title,
                result.username,
                "N/A",
                "N/A",
                f"ERROR: {result.error}",
            )

    console.print(table)
    print(
        f"Completed: {len(successful)} OK, {len(failed)} failed ({total_duration:.2f}s total)"
    )
    print()

    if show_problems and successful:
        print("--- Detailed Report ---")
        for result in successful:
            title = result.crawler.meta.title
            username = result.username
            solved_list = result.solved_list
            if solved_list:
                problems_str = ", ".join(sorted(solved_list))
                print(f"{title} ({username}): {problems_str}")
            elif solved_list is None:
                print(
                    f"{title} ({username}): (list not available — {result.solved} solved)"
                )
            print()

    return 0 if not failed else 1


def print_crawler_list(json_output: bool = False) -> None:
    """Print list of available crawlers in a table format."""
    if not crawler_registry:
        msg = "\nNo crawlers found. Make sure aiohttp is installed.\n"
        if json_output:
            print(msg, file=sys.stderr)
        else:
            print(msg)
        return

    if json_output:
        result = {}
        for name in sorted(crawler_registry.keys()):
            meta = crawler_registry[name].meta
            result[name] = {
                "title": meta.title,
                "description": meta.description,
                "url": meta.url,
                "login_type": meta.login_type.value,
                "is_aggregator": meta.is_aggregator,
            }
        print(json.dumps(result, indent=2))
        return

    console = Console()

    table = Table(
        title=f"Available crawlers ({len(crawler_registry)})", show_lines=True
    )
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("URL")
    table.add_column("Login")

    for name in sorted(crawler_registry.keys()):
        meta = crawler_registry[name].meta
        description = meta.cli_description or meta.description
        table.add_row(name, description, meta.url, meta.login_type.label)

    print()
    console.print(table)
    print()


def print_progress(title: str, completed: int, total: int) -> None:
    """Print progress update for a completed crawler."""
    print(f"{title} done ({completed}/{total})")
