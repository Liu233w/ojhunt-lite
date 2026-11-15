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

from urllib.parse import quote

import aiohttp
from selectolax.lexbor import LexborHTMLParser

__crawler_meta__ = {
    "title": "SamCoding",
    "description": "Please enter your SamCoding username (the name in your profile URL)",
    "url": "https://samcoding.uz/",
    "test_username": "yusufsyed",
}

BASE_URL = "https://samcoding.uz"
MAX_SUBMISSION_PAGES = 2000


async def _get_html(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 404:
                raise ValueError("The user does not exist")
            response.raise_for_status()
            return await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str] | None]:
    """
    Query SamCoding for user statistics.

    Args:
        session: aiohttp ClientSession
        username: SamCoding username, as it appears in the profile URL

    Returns:
        Dictionary with keys: solved, submissions, solved_list. solved counts the
        problems highlighted as solved in the profile's problem map; submissions is
        the number of rows in the user's submission list.

    Raises:
        ValueError: If username is empty or the user does not exist
        RuntimeError: If a request fails or the page cannot be parsed
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")
    username = username.strip()

    profile_url = f"{BASE_URL}/profile/{quote(username, safe='')}"
    doc = LexborHTMLParser(await _get_html(session, profile_url))
    problem_map = doc.css_first(".problem-map")
    if problem_map is None:
        raise RuntimeError("Problem map not found")
    solved_list = [
        code.text(strip=True)
        for code in problem_map.css("a.btn-primary code")
        if code.text(strip=True)
    ]
    solved = len(solved_list)

    submissions = 0
    for page in range(1, MAX_SUBMISSION_PAGES + 1):
        page_doc = LexborHTMLParser(
            await _get_html(session, f"{profile_url}/submissions?page={page}")
        )
        submissions += len(page_doc.css("td.status"))
        if page_doc.css_first('a[href*="page="]:lexbor-contains("Keyingi")') is None:
            break
    else:
        raise RuntimeError("Submission list has too many pages")

    return {
        "solved": solved,
        "submissions": max(submissions, solved),
        "solved_list": solved_list or None,
    }
