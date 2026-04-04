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
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Make src/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ojhunt.web.pdf import (
    HistoryEntry,
    PdfCrawlerResult,
    PdfQueryItem,
    PdfSettings,
    PdfSnapshot,
    generate_pdf,
    merge_history,
)

DB_PATH = Path("legacy.db")

# Windows timezone name → IANA timezone name
# Only names that appear in the legacy DB are listed here; extend as needed.
WINDOWS_TO_IANA: dict[str, str] = {
    "Afghanistan Standard Time": "Asia/Kabul",
    "AUS Eastern Standard Time": "Australia/Sydney",
    "Bangladesh Standard Time": "Asia/Dhaka",
    "Canada Central Standard Time": "America/Regina",
    "Central Asia Standard Time": "Asia/Almaty",
    "Central Europe Standard Time": "Europe/Budapest",
    "Central European Standard Time": "Europe/Warsaw",
    "China Standard Time": "Asia/Shanghai",
    "E. Africa Standard Time": "Africa/Nairobi",
    "E. Asia Standard Time": "Asia/Hong_Kong",
    "E. Europe Standard Time": "Asia/Nicosia",
    "Eastern Standard Time": "America/New_York",
    "GMT Standard Time": "Europe/London",
    "India Standard Time": "Asia/Kolkata",
    "Japan Standard Time": "Asia/Tokyo",
    "Jordan Standard Time": "Asia/Amman",
    "Korea Standard Time": "Asia/Seoul",
    "Middle East Standard Time": "Asia/Beirut",
    "Mountain Standard Time": "America/Denver",
    "N. Central Asia Standard Time": "Asia/Novosibirsk",
    "Pacific SA Standard Time": "America/Santiago",
    "Pacific Standard Time": "America/Los_Angeles",
    "Romance Standard Time": "Europe/Paris",
    "Russia Time Zone 11": "Asia/Kamchatka",
    "SE Asia Standard Time": "Asia/Bangkok",
    "Singapore Standard Time": "Asia/Singapore",
    "South Africa Standard Time": "Africa/Johannesburg",
    "Sri Lanka Standard Time": "Asia/Colombo",
    "Taipei Standard Time": "Asia/Taipei",
    "Tokyo Standard Time": "Asia/Tokyo",
    "Turkey Standard Time": "Europe/Istanbul",
    "UTC": "UTC",
    "US Eastern Standard Time": "America/Indianapolis",
    "W. Australia Standard Time": "Australia/Perth",
    "W. Europe Standard Time": "Europe/Berlin",
}


def windows_to_iana(win_tz: str) -> str:
    """Convert a Windows timezone name to IANA. Falls back to UTC."""
    return WINDOWS_TO_IANA.get(win_tz, "UTC")


def _day_key_from_utc(utc_dt_str: str, iana_tz: str) -> str:
    """Convert a UTC datetime string to a YYYY-MM-DD day key in the user's timezone."""
    try:
        dt = datetime.fromisoformat(utc_dt_str).replace(tzinfo=timezone.utc)
    except ValueError:
        return utc_dt_str[:10]
    try:
        tz = ZoneInfo(iana_tz)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
    return dt.astimezone(tz).strftime("%Y-%m-%d")


def find_user(con: sqlite3.Connection, username: str) -> list[dict]:
    """Find matching users by main_username or ABP username (case-insensitive).

    Returns list of {user_id, main_username, abp_username, match_type} dicts.
    """
    matches = []
    lower = username.lower()

    # 1. Match by main_username in query_histories
    rows = con.execute(
        """
        SELECT DISTINCT qh.user_id, qh.main_username, u.username
        FROM query_histories qh
        LEFT JOIN users u ON u.id = qh.user_id
        WHERE LOWER(qh.main_username) = ?
        """,
        (lower,),
    ).fetchall()
    for user_id, main_username, abp_username in rows:
        matches.append(
            {
                "user_id": user_id,
                "main_username": main_username,
                "abp_username": abp_username,
                "match_type": "main_username",
            }
        )

    # 2. Match by ABP username (if not already found)
    found_ids = {m["user_id"] for m in matches}
    rows = con.execute(
        "SELECT id, username FROM users WHERE LOWER(username) = ?",
        (lower,),
    ).fetchall()
    for user_id, abp_username in rows:
        if user_id not in found_ids:
            # Get main_username from their most recent query
            row = con.execute(
                """
                SELECT main_username FROM query_histories
                WHERE user_id = ? AND main_username <> ''
                ORDER BY creation_time DESC LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            main_username = row[0] if row else abp_username
            matches.append(
                {
                    "user_id": user_id,
                    "main_username": main_username,
                    "abp_username": abp_username,
                    "match_type": "abp_username",
                }
            )

    return matches


def get_iana_timezone(con: sqlite3.Connection, user_id: int) -> str:
    row = con.execute(
        "SELECT value FROM user_settings WHERE user_id = ? AND name = 'Abp.Timing.TimeZone'",
        (user_id,),
    ).fetchone()
    if row and row[0]:
        return windows_to_iana(row[0])
    return "UTC"


def build_settings(
    con: sqlite3.Connection, user_id: int, main_username: str
) -> PdfSettings:
    """Build PdfSettings from the user's saved default queries."""
    row = con.execute(
        "SELECT usernames_in_crawlers FROM default_queries WHERE user_id = ? AND is_deleted = 0 ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()

    queries: list[PdfQueryItem] = []
    if row:
        try:
            data: dict = json.loads(row[0])
            for crawler, usernames in data.items():
                if usernames and usernames[0]:
                    queries.append(PdfQueryItem(crawler=crawler, username=usernames[0]))
        except (json.JSONDecodeError, IndexError):
            pass

    # Fallback: derive from username_in_crawler for the most recent summary
    if not queries:
        rows = con.execute(
            """
            SELECT cs.crawler, uic.username
            FROM query_histories qh
            JOIN query_summaries qs ON qs.history_id = qh.id
            JOIN crawler_summaries cs ON cs.summary_id = qs.id
            JOIN username_in_crawler uic ON uic.crawler_summary_id = cs.id
            WHERE qh.user_id = ? AND uic.from_crawler IS NULL AND uic.username <> ''
            ORDER BY qs.generate_time DESC
            LIMIT 50
            """,
            (user_id,),
        ).fetchall()
        seen = set()
        for crawler, username in rows:
            if crawler not in seen:
                queries.append(PdfQueryItem(crawler=crawler, username=username))
                seen.add(crawler)

    return PdfSettings(username=main_username, queries=queries)


def build_history(
    con: sqlite3.Connection, user_id: int, iana_tz: str, main_username: str
) -> list[HistoryEntry]:
    """Build history entries from all query summaries, deduped per day."""
    rows = con.execute(
        """
        SELECT qs.generate_time, qs.solved, qs.submission
        FROM query_histories qh
        JOIN query_summaries qs ON qs.history_id = qh.id
        WHERE qh.user_id = ?
        ORDER BY qs.generate_time
        """,
        (user_id,),
    ).fetchall()

    history: list[HistoryEntry] = []
    for generate_time, solved, submission in rows:
        day_key = _day_key_from_utc(generate_time, iana_tz)
        entry = HistoryEntry(
            key=day_key,
            date=generate_time,
            totalSolved=solved,
            totalSubmissions=submission,
            username=main_username,
        )
        history = merge_history(history, entry)

    return history


def build_snapshot(
    con: sqlite3.Connection, user_id: int, main_username: str, iana_tz: str
) -> PdfSnapshot:
    """Build PdfSnapshot from the most recent query summary."""
    row = con.execute(
        """
        SELECT qs.id, qs.solved, qs.submission
        FROM query_histories qh
        JOIN query_summaries qs ON qs.history_id = qh.id
        WHERE qh.user_id = ?
        ORDER BY qs.generate_time DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()

    if not row:
        return PdfSnapshot(
            totalSolved=0,
            totalSubmissions=0,
            username=main_username,
            timezone=iana_tz,
            results=[],
        )

    summary_id, total_solved, total_submission = row

    # Per-crawler breakdown with username
    rows = con.execute(
        """
        SELECT cs.crawler, cs.solved, cs.submission, uic.username
        FROM crawler_summaries cs
        LEFT JOIN username_in_crawler uic
            ON uic.crawler_summary_id = cs.id AND uic.from_crawler IS NULL
        WHERE cs.summary_id = ?
        ORDER BY cs.solved DESC
        """,
        (summary_id,),
    ).fetchall()

    results = [
        PdfCrawlerResult(
            crawler=crawler,
            username=username or main_username,
            solved=solved,
            submissions=submission,
        )
        for crawler, solved, submission, username in rows
        if solved > 0 or submission > 0
    ]

    return PdfSnapshot(
        totalSolved=total_solved,
        totalSubmissions=total_submission,
        username=main_username,
        timezone=iana_tz,
        results=results,
    )


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
        "username", help="Username to look up (main OJ username or site login)"
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
            print(
                f"  [{i}] user_id={m['user_id']}  main={m['main_username']!r}"
                f"  abp={m['abp_username']!r}  ({m['match_type']})"
            )
        if args.list_matches:
            return
        print(
            "\nUsing first match. Use --list-matches to inspect all.", file=sys.stderr
        )

    match = matches[0]
    user_id = match["user_id"]
    main_username = match["main_username"] or match["abp_username"] or args.username

    output_path = (
        Path(args.output) if args.output else Path(f"{main_username}_legacy.pdf")
    )

    print(f"Exporting: user_id={user_id}  username={main_username!r}")
    export_user(user_id, main_username, output_path)


if __name__ == "__main__":
    main()
