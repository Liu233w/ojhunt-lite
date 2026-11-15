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

import aiohttp
from selectolax.lexbor import LexborHTMLParser

__crawler_meta__ = {
    "title": "oj.uz",
    "description": "Online Judge hosting IOI/BOI/JOI/APIO problems. Submissions shows the number of attempted problems, a lower bound on the real total.",
    "url": "https://oj.uz/",
    "test_username": "iamsazidh",
}

BASE_URL = "https://oj.uz"


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str]]:
    """
    Query oj.uz for user statistics.

    Args:
        session: aiohttp ClientSession
        username: oj.uz username

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty or user doesn't exist
        RuntimeError: If request fails or parsing fails
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    profile_url = f"{BASE_URL}/profile/{username}"

    try:
        async with session.get(
            profile_url,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 404:
                raise ValueError("The user does not exist")
            response.raise_for_status()
            html = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")

    try:
        doc = LexborHTMLParser(html)

        solved = _extract_stat(doc, "solved problems")
        attempted = _extract_stat(doc, "attempted problems")
        solved_list = _extract_solved_list(doc)
    except Exception:
        raise RuntimeError("Error while parsing")

    # The submissions page sits behind a Cloudflare challenge, so the profile's
    # attempted-problem count stands in as a lower bound (ADR 0015).
    return {
        "solved": solved,
        "submissions": max(attempted, solved),
        "solved_list": solved_list,
    }


def _extract_stat(doc: LexborHTMLParser, label: str) -> int:
    """Extract a numeric row such as "# solved problems" from the profile stats table."""
    for tr in doc.css("tr"):
        th = tr.css_first("th")
        td = tr.css_first("td")
        if th and td and label in th.text():
            return int(td.text(strip=True))
    return 0


def _extract_solved_list(doc: LexborHTMLParser) -> list[str]:
    """Extract list of solved problem IDs from profile page."""
    solved_list = []
    for panel in doc.css("div.panel"):
        heading = panel.css_first("div.panel-heading")
        if heading and "Solved problems" in heading.text():
            for a in panel.css("a"):
                href = a.attributes.get("href", "")
                if href.startswith("/problem/view/"):
                    problem_id = href.split("/")[-1]
                    solved_list.append(problem_id)
            break
    return solved_list
