"""Generate a PDF progress report for a user from the legacy ACM Statistics database.

Requires legacy.db to exist (run import_legacy.py first).

Usage:
    uv run python scripts/export_legacy.py <username> [--output FILE]
    uv run python scripts/export_legacy.py <username> --list-matches   # show all matches

Example:
    uv run python scripts/export_legacy.py tourist
    uv run python scripts/export_legacy.py tourist --output tourist_history.pdf
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Make src/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ojhunt.web.legacy_db import (
    build_history,
    build_settings,
    build_snapshot,
    find_user,
    get_iana_timezone,
)
from ojhunt.web.pdf import generate_pdf

DB_PATH = Path("legacy.db")


def export_user(user_id: int, main_username: str, output_path: Path) -> None:
    con = sqlite3.connect(DB_PATH)
    try:
        iana_tz = get_iana_timezone(con, user_id)
        settings = build_settings(con, user_id, main_username)
        history = build_history(con, user_id, iana_tz, main_username)
        snapshot = build_snapshot(con, user_id, main_username, iana_tz)
    finally:
        con.close()

    print(f"  Timezone:   {iana_tz}")
    print(f"  History:    {len(history)} daily entries")
    print(f"  Queries:    {len(settings.queries)} crawlers configured")
    print(
        f"  Latest:     {snapshot.totalSolved} solved / {snapshot.totalSubmissions} submissions"
    )

    pdf_bytes = generate_pdf(settings, history, snapshot)
    output_path.write_bytes(pdf_bytes)
    print(f"  Saved to:   {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export legacy ACM Statistics data as PDF"
    )
    parser.add_argument(
        "username", help="ABP site login username to look up"
    )
    parser.add_argument(
        "--output", "-o", help="Output PDF path (default: <username>_legacy.pdf)"
    )
    parser.add_argument(
        "--list-matches",
        action="store_true",
        help="List all matching users without generating a PDF",
    )
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(
            f"ERROR: {DB_PATH} not found. Run import_legacy.py first.", file=sys.stderr
        )
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    matches = find_user(con, args.username)
    con.close()

    if not matches:
        print(f"No user found for '{args.username}'.", file=sys.stderr)
        sys.exit(1)

    if args.list_matches or len(matches) > 1:
        print(f"Found {len(matches)} match(es) for '{args.username}':")
        for i, m in enumerate(matches):
            print(f"  [{i}] user_id={m['user_id']}  abp={m['abp_username']!r}")
        if args.list_matches:
            return
        print(
            "\nUsing first match. Use --list-matches to inspect all.", file=sys.stderr
        )

    match = matches[0]
    user_id = match["user_id"]
    abp_username = match["abp_username"]

    con2 = sqlite3.connect(DB_PATH)
    try:
        row = con2.execute(
            "SELECT main_username FROM query_histories"
            " WHERE user_id = ? AND main_username <> ''"
            " ORDER BY creation_time DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    finally:
        con2.close()
    display_username = (row[0] if row else None) or abp_username or args.username

    output_path = (
        Path(args.output) if args.output else Path(f"{display_username}_legacy.pdf")
    )

    print(f"Exporting: user_id={user_id}  username={display_username!r}")
    export_user(user_id, display_username, output_path)


if __name__ == "__main__":
    main()
