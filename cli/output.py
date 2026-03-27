"""
CLI output and validation functions for OJHunt Lite.
"""

import sys
from collections import Counter
from typing import Dict, List, Tuple

from rich.console import Console
from rich.table import Table

from cli.models import Query
from core.models import CrawlerInfo, QueryResult
from core.stats import collect_solved_problems
from crawlers import discover_crawlers


def check_duplicate_queries(queries: List[Query]) -> None:
    """Check for duplicate queries and print warning to stderr."""
    counter = Counter((q.crawler, q.username) for q in queries)
    for (crawler, username), count in counter.items():
        if count > 1:
            print(
                f"Warning: duplicate query '{username}@{crawler}' (will run {count} times)",
                file=sys.stderr,
            )


def validate_crawlers(queries: List[Query], crawlers: Dict[str, CrawlerInfo]) -> bool:
    """Validate that all queried crawlers exist."""
    unknown = set(q.crawler for q in queries if q.crawler not in crawlers)
    if unknown:
        print(
            f"Error: unknown crawler(s): {', '.join(sorted(unknown))}",
            file=sys.stderr,
        )
        print("Run 'ojhunt --list' to see available crawlers.", file=sys.stderr)
        return False
    return True


def validate_credentials(
    queries: List[Query],
    crawlers: Dict[str, CrawlerInfo],
    crawler_logins: Dict[str, Tuple[str, str]],
) -> bool:
    """
    Validate that credential requirements are met for each query.

    For requires_login crawlers (e.g., VJudge):
        - If query has password: login as that user, query that user
        - If query has no password but -l flag provided: use flag credentials
        - If neither: error

    For requires_password crawlers:
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
        requires_login = meta.requires_login
        requires_password = meta.requires_password

        if requires_login:
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

        elif requires_password:
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
    results: List[QueryResult],
    show_problems: bool,
    total_duration: float,
) -> int:
    """Print the final report and return exit code."""
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    all_solved = collect_solved_problems(results)
    total_submissions = sum(r.submissions for r in successful)

    print()
    print(f"Total: {len(all_solved)} solved / {total_submissions} submissions")
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
            print()

    return 0 if not failed else 1


def print_crawler_list() -> None:
    """Print list of available crawlers in a table format."""
    crawlers = discover_crawlers()

    if not crawlers:
        print("\nNo crawlers found. Make sure aiohttp is installed.\n")
        return

    console = Console()

    table = Table(title=f"Available crawlers ({len(crawlers)})", show_lines=True)
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("URL")
    table.add_column("Login")

    for name in sorted(crawlers.keys()):
        meta = crawlers[name].meta
        description = meta.cli_description or meta.description
        table.add_row(name, description, meta.url, meta.login_type)

    print()
    console.print(table)
    print()


def print_progress(title: str, completed: int, total: int) -> None:
    """Print progress update for a completed crawler."""
    print(f"{title} done ({completed}/{total})")
