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

import re
import aiohttp
from selectolax.lexbor import LexborHTMLParser
from typing import Dict, List, Set, Union

__crawler_meta__ = {
    "title": "POJ",
    "description": "",
    "url": "http://poj.org/",
    "test_username": "leoloveacm",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
}

# POJ clamps the /status page-size parameter at 500 rows.
_STATUS_PAGE_SIZE = 500


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query PKU JudgeOnline for user statistics.

    Args:
        session: aiohttp ClientSession
        username: POJ username

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty or user doesn't exist
        RuntimeError: If request fails or parsing fails
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    # Primary source: the per-user summary page. POJ has disabled this route at
    # the nginx layer for out-of-network requests (a bare 403), but self-hosters
    # on the network POJ still serves get the full page. Try it first; only walk
    # the public /status log when the summary page is blocked.
    try:
        async with session.get(
            "http://poj.org/userstatus",
            params={"user_id": username},
            headers=_HEADERS,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 403:
                return await _query_via_status(session, username)
            response.raise_for_status()
            html = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    if "<title>Error -- no user found</title>" in html:
        raise ValueError("The user does not exist")
    if "Sorry," in html and "doesn't exist" in html:
        raise ValueError("The user does not exist")

    try:
        doc = LexborHTMLParser(html)

        # POJ HTML is very old and sometimes ill-formatted.
        # Solved: <a href="status?result=0&user_id=...">NUMBER</a>
        # Submissions: <a href="status?user_id=...">NUMBER</a>
        solved = 0
        submissions = 0

        for a in doc.css("a"):
            href = a.attributes.get("href", "")
            if "status?result=0" in href and f"user_id={username}" in href:
                try:
                    solved = int(a.text(strip=True))
                except ValueError:
                    pass
            elif (
                "status?user_id=" in href
                and f"user_id={username}" in href
                and "result=0" not in href
            ):
                try:
                    submissions = int(a.text(strip=True))
                except ValueError:
                    pass

        # Extract solved list from JavaScript: p(1000)\np(1001)\n...
        solved_list = re.findall(r"p\((\d+)\)", html)

        if solved == 0 and submissions == 0 and not solved_list:
            raise RuntimeError("Empty data")

        return {
            "solved": solved,
            "submissions": submissions,
            "solved_list": solved_list,
        }
    except Exception:
        raise RuntimeError("Error while parsing")


async def _query_via_status(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Reconstruct user statistics from the public /status submission log.

    Used when the /userstatus summary page is blocked. POJ exposes no per-user
    total, so we page through the whole log (newest first via the ``top``
    cursor, ``size=500`` per page) counting submissions and collecting the
    distinct problem ids of Accepted submissions.
    """
    submissions = 0
    solved: Set[str] = set()
    cursor: Union[int, None] = None

    try:
        while True:
            params: Dict[str, Union[str, int]] = {
                "user_id": username,
                "size": _STATUS_PAGE_SIZE,
            }
            if cursor is not None:
                params["top"] = cursor

            async with session.get(
                "http://poj.org/status",
                params=params,
                headers=_HEADERS,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                html = await response.text()

            doc = LexborHTMLParser(html)
            rows = doc.css('table.a tr[align="center"]')
            if not rows:
                break

            run_ids: List[int] = []
            for row in rows:
                cells = row.css("td")
                if len(cells) < 4:
                    continue
                try:
                    run_id = int(cells[0].text(strip=True))
                except ValueError:
                    continue
                run_ids.append(run_id)
                submissions += 1

                if cells[3].text(strip=True) == "Accepted":
                    link = cells[2].css_first('a[href*="problem?id="]')
                    if link:
                        m = re.search(
                            r"problem\?id=(\d+)", link.attributes.get("href", "")
                        )
                        if m:
                            solved.add(m.group(1))

            # A short page (fewer rows than requested) is the last one.
            if not run_ids or len(rows) < _STATUS_PAGE_SIZE:
                break

            next_cursor = min(run_ids)
            if next_cursor == cursor:  # safety: cursor failed to advance
                break
            cursor = next_cursor
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    # /status cannot tell a missing user apart from one with no submissions;
    # treat an empty log as a non-existent user.
    if submissions == 0:
        raise ValueError("The user does not exist")

    return {
        "solved": len(solved),
        "submissions": submissions,
        "solved_list": sorted(solved),
    }
