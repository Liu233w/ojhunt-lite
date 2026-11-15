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
from urllib.parse import quote

import aiohttp
from selectolax.lexbor import LexborHTMLParser

__crawler_meta__ = {
    "title": "DOJ",
    "description": "Please use your DOJ handle (the name in your profile URL, doj.kr/ko/user/...)",
    "url": "https://doj.kr/",
    "test_username": "paracompact",
}

BASE_URL = "https://doj.kr"
SOLVED_HEADING = "푼 문제"


async def _fetch(
    session: aiohttp.ClientSession, path: str, params: dict[str, str] | None = None
) -> str:
    try:
        async with session.get(
            f"{BASE_URL}{path}",
            params=params,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            return await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")


def _count_submissions(doc: LexborHTMLParser) -> tuple[int, int]:
    """Return (rows on this page, total pages) of a status page."""
    rows = len(doc.css("table.doj-submission-status-table tbody tr"))
    nav = doc.css_first(".doj-pagination-nav")
    pages = 1
    if nav is not None:
        match = re.search(r"/\s*(\d+)", nav.attributes.get("aria-label") or "")
        if match is None:
            raise RuntimeError("Submission page count not found")
        pages = int(match.group(1))
    return rows, pages


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str] | None]:
    """
    Query DOJ (doj.kr) for user statistics.

    Args:
        session: aiohttp ClientSession
        username: DOJ handle, as it appears in the profile URL (doj.kr/ko/user/...)

    Returns:
        Dictionary with keys: solved, submissions, solved_list. solved_list is
        None because the site's solved-problem listing omits some solved problems.
        submissions is counted from the user's submission history.

    Raises:
        ValueError: If username is empty or the user does not exist
        RuntimeError: If the request fails or the page cannot be parsed
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    handle = username.strip()

    html = await _fetch(session, f"/ko/user/{quote(handle, safe='')}")
    # The site answers 200 for unknown users and embeds the Next.js 404 marker.
    if "NEXT_HTTP_ERROR_FALLBACK;404" in html:
        raise ValueError("The user does not exist")

    doc = LexborHTMLParser(html)
    solved = None
    for card in doc.css(".doj-summary-card"):
        heading = card.css_first(".panel-heading")
        value = card.css_first(".doj-summary-value")
        if heading is None or value is None:
            continue
        if SOLVED_HEADING in heading.text():
            digits = value.text(strip=True).replace(",", "")
            if not digits.isdigit():
                raise RuntimeError("Solved count is not a number")
            solved = int(digits)
            break
    if solved is None:
        raise RuntimeError("Solved count not found")

    status_html = await _fetch(session, "/ko/status", {"user": handle})
    status_doc = LexborHTMLParser(status_html)
    rows, pages = _count_submissions(status_doc)
    page_size = rows
    submissions = rows
    if pages > 1:
        last_html = await _fetch(
            session, "/ko/status", {"user": handle, "page": str(pages)}
        )
        last_rows, _ = _count_submissions(LexborHTMLParser(last_html))
        submissions = page_size * (pages - 1) + last_rows

    return {
        "solved": solved,
        "submissions": max(submissions, solved),
        "solved_list": None,
    }
