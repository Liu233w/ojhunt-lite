"""
CLI argument parser for OJHunt Lite.
"""

import argparse
import sys
from typing import Dict, List, Optional, Tuple

from cli.models import Query
from core.models import CrawlerInfo


def parse_crawler_login(values: Optional[List[str]]) -> Dict[str, Tuple[str, str]]:
    """
    Parse -l user:pass@crawler arguments.

    Args:
        values: List of login strings like ["user:pass@vjudge", "user2:pass2@other"]

    Returns:
        Dictionary mapping crawler names to (username, password) tuples.

    Raises:
        ValueError: If format is invalid.
    """
    result: Dict[str, Tuple[str, str]] = {}
    if not values:
        return result

    for value in values:
        if "@" not in value:
            raise ValueError(
                f"Invalid login format: {value}. Expected user:pass@crawler"
            )

        last_at = value.rfind("@")
        crawler = value[last_at + 1 :]
        credentials = value[:last_at]

        if not crawler:
            raise ValueError(f"Empty crawler name in login: {value}")
        if not credentials:
            raise ValueError(f"Empty credentials in login: {value}")

        if ":" not in credentials:
            raise ValueError(
                f"Missing password in login: {value}. Expected user:pass@crawler"
            )

        first_colon = credentials.find(":")
        username = credentials[:first_colon]
        password = credentials[first_colon + 1 :]

        if not username:
            raise ValueError(f"Empty username in login: {value}")

        if crawler in result:
            raise ValueError(f"Duplicate login for crawler '{crawler}'")

        result[crawler] = (username, password)

    return result


def build_all_queries(
    default_username: str, crawlers: Dict[str, CrawlerInfo]
) -> List[Query]:
    """Build queries for all crawlers using default username."""
    return [Query(crawler=name, username=default_username) for name in crawlers.keys()]


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog="ojhunt",
        description="Query Online Judge statistics across multiple platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query all crawlers with default username
  %(prog)s -d tourist -a

  # Query specific crawlers with default username
  %(prog)s -d tourist -- codeforces poj hdu

  # Query with @ syntax (no default needed)
  %(prog)s -- tourist@codeforces vjudge5@poj

  # Mixed: some with @ syntax, some with default
  %(prog)s -d default_user -- user1@codeforces poj hdu

  # User with @ in username (last @ is separator)
  %(prog)s -- user@domain@codeforces

  # Query yourself on VJudge (login and query same user)
  %(prog)s -- myuser:mypass@vjudge

  # Query someone else on VJudge (login as you, query them)
  %(prog)s -l myuser:mypass@vjudge -- target_user@vjudge

  # Multiple login-required crawlers
  %(prog)s -l user1:pass1@vjudge -l user2:pass2@otheroj -- target1@vjudge target2@otheroj

  # List available crawlers
  %(prog)s --list
        """,
    )

    parser.add_argument(
        "-d",
        "--default-username",
        metavar="USER",
        help="Default username for crawlers without @ syntax",
    )

    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Query all available crawlers (requires -d)",
    )

    parser.add_argument(
        "-l",
        "--crawler-login",
        action="append",
        metavar="USER:PASS@CRAWLER",
        help="Login credentials for crawlers that require authentication (can be used multiple times)",
    )

    parser.add_argument(
        "--list", action="store_true", help="List all available crawlers"
    )

    parser.add_argument(
        "--show-problems",
        action="store_true",
        help="Show list of solved problems in output",
    )

    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress display (useful for CI/logs)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON to stdout (progress still on stderr)",
    )

    parser.add_argument(
        "queries",
        nargs="*",
        help="Queries in format: user@crawler or user:pass@crawler or crawler (uses default username)",
    )

    return parser


def parse_positional(args: List[str], default_username: Optional[str]) -> List[Query]:
    """
    Parse positional arguments like: tourist@codeforces user:pass@vjudge poj

    Parsing rules:
    - Last @ separates credentials from crawler name
    - First : in credentials separates username from password
    - "user:pass@vjudge" -> username="user", password="pass", crawler="vjudge"
    - "user:p@ss@vjudge" -> username="user", password="p@ss", crawler="vjudge"
    - "user@codeforces" -> username="user", password=None, crawler="codeforces"
    - "user@domain@codeforces" -> username="user@domain", password=None, crawler="codeforces"
    - "codeforces" -> username=default_username, password=None, crawler="codeforces"

    Args:
        args: List of positional query strings
        default_username: Default username to use when @ not present

    Returns:
        List of Query objects

    Raises:
        ValueError: If no username available (no @ and no default)
    """
    queries = []
    for arg in args:
        if "@" in arg:
            last_at = arg.rfind("@")
            credentials = arg[:last_at]
            crawler = arg[last_at + 1 :]

            if not credentials:
                raise ValueError(f"Empty username in query: {arg}")
            if not crawler:
                raise ValueError(f"Empty crawler name in query: {arg}")

            if ":" in credentials:
                first_colon = credentials.find(":")
                username = credentials[:first_colon]
                password = credentials[first_colon + 1 :]
            else:
                username = credentials
                password = None

            queries.append(Query(crawler=crawler, username=username, password=password))
        else:
            if not default_username:
                raise ValueError(
                    f"No username specified for '{arg}' and no default username provided. "
                    f"Use -d USER or user@crawler syntax."
                )
            queries.append(Query(crawler=arg, username=default_username, password=None))
    return queries


def parse_args(
    argv: Optional[List[str]] = None,
) -> Tuple[argparse.Namespace, List[Query], Dict[str, Tuple[str, str]]]:
    """
    Parse command line arguments and build query list.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Tuple of (parsed namespace, list of Query objects, crawler_logins dict)

    Raises:
        SystemExit: On --help, --list, or validation errors
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    queries: List[Query] = []
    crawler_logins: Dict[str, Tuple[str, str]] = {}

    if args.list:
        return args, queries, crawler_logins

    if args.all:
        if not args.default_username:
            print("Error: -a/--all requires -d/--default-username", file=sys.stderr)
            sys.exit(1)

    if not args.all and not args.queries:
        parser.print_help()
        sys.exit(1)

    if args.crawler_login:
        try:
            crawler_logins = parse_crawler_login(args.crawler_login)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    if args.queries:
        try:
            queries = parse_positional(args.queries, args.default_username)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    return args, queries, crawler_logins
