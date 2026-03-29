"""
BSD 2-Clause License

Copyright (c) 2026, OJHunt Lite Contributors
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import asyncio
import sqlite3
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional

import aiohttp

_DB_PATH = Path(__file__).parent.parent / "problem_labels.db"

_CONCURRENT_REQUESTS = 20


def _get_connection() -> sqlite3.Connection:
    return sqlite3.connect(str(_DB_PATH))


def _init_db() -> None:
    if _DB_PATH.exists():
        return

    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS problem_label_mappings (
                online_judge TEXT NOT NULL,
                problem_id INTEGER NOT NULL,
                problem_label TEXT,
                PRIMARY KEY (online_judge, problem_id)
            )
        """)
        conn.commit()
    finally:
        conn.close()


def _get_cached_labels(
    oj_name: str, problem_ids: List[int]
) -> Dict[int, Optional[str]]:
    if not _DB_PATH.exists():
        return {}

    conn = _get_connection()
    try:
        placeholders = ",".join("?" * len(problem_ids))
        cursor = conn.execute(
            f"SELECT problem_id, problem_label FROM problem_label_mappings "
            f"WHERE online_judge = ? AND problem_id IN ({placeholders})",
            [oj_name] + problem_ids,
        )
        return {row[0]: row[1] for row in cursor.fetchall()}
    finally:
        conn.close()


def _cache_labels(oj_name: str, mappings: Dict[int, Optional[str]]) -> None:
    _init_db()

    conn = _get_connection()
    try:
        conn.executemany(
            "INSERT OR REPLACE INTO problem_label_mappings (online_judge, problem_id, problem_label) "
            "VALUES (?, ?, ?)",
            [(oj_name, pid, label) for pid, label in mappings.items()],
        )
        conn.commit()
    finally:
        conn.close()


async def resolve_labels(
    session: aiohttp.ClientSession,
    oj_name: str,
    problem_ids: List[int],
    resolver: Callable[[aiohttp.ClientSession, int], Awaitable[Optional[str]]],
    rate_limit_delay: float = 0.0,
) -> Dict[int, Optional[str]]:
    """
    Resolve problem labels with caching.

    Checks the database cache first, then fetches missing labels using the
    provided resolver callback. Results are cached for future use.

    Args:
        session: aiohttp ClientSession for HTTP requests
        oj_name: Online judge name (used as cache key)
        problem_ids: List of problem IDs to resolve
        resolver: Async callback that takes (session, problem_id) and returns
                  the problem label, or None if not found
        rate_limit_delay: Optional delay between requests in seconds

    Returns:
        Dict mapping problem_id -> label (or None if resolution failed)
    """
    if not problem_ids:
        return {}

    cached = _get_cached_labels(oj_name, problem_ids)

    missing_ids = [pid for pid in problem_ids if pid not in cached]
    if not missing_ids:
        return cached

    semaphore = asyncio.Semaphore(_CONCURRENT_REQUESTS)

    async def resolve_with_semaphore(pid: int) -> tuple[int, Optional[str]]:
        async with semaphore:
            if rate_limit_delay > 0:
                await asyncio.sleep(rate_limit_delay)
            return (pid, await resolver(session, pid))

    tasks = [resolve_with_semaphore(pid) for pid in missing_ids]
    results = await asyncio.gather(*tasks)
    new_mappings = dict(results)

    if new_mappings:
        _cache_labels(oj_name, new_mappings)

    return {**cached, **new_mappings}
