"""Legacy database helpers for exporting acm-statistics history as OJHunt PDFs.

Reads from legacy.db (SQLite, produced by scripts/import_legacy.py).
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ojhunt.web.pdf import (
    HistoryEntry,
    PdfCrawlerResult,
    PdfQueryItem,
    PdfSettings,
    PdfSnapshot,
    generate_pdf,
    merge_history,
)

# Windows timezone name → IANA timezone name.
# Only names that appear in the legacy DB are listed here.
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


def find_user(con: sqlite3.Connection, username: str) -> List[dict]:
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

    queries: List[PdfQueryItem] = []
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
) -> List[HistoryEntry]:
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

    history: List[HistoryEntry] = []
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


def export_user_pdf(username: str) -> bytes:
    """Generate a PDF for the given username from legacy.db in the current working directory.

    Raises:
        FileNotFoundError: if legacy.db does not exist.
        ValueError: if the username is not found.
    """
    db_path = Path("legacy.db")
    if not db_path.exists():
        raise FileNotFoundError("legacy.db not found")

    con = sqlite3.connect(db_path)
    try:
        matches = find_user(con, username)
        if not matches:
            raise ValueError(f"Username '{username}' not found in legacy data")

        match = matches[0]
        user_id = match["user_id"]
        main_username = match["main_username"] or match["abp_username"] or username

        iana_tz = get_iana_timezone(con, user_id)
        settings = build_settings(con, user_id, main_username)
        history = build_history(con, user_id, iana_tz, main_username)
        snapshot = build_snapshot(con, user_id, main_username, iana_tz)
    finally:
        con.close()

    return generate_pdf(settings, history, snapshot)
