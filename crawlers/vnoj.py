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
from typing import Dict, List, Union

__crawler_meta__ = {
    "title": "VNOJ",
    "description": "VNOI Online Judge",
    "url": "https://oj.vnoi.info/",
}

BASE_URL = "https://oj.vnoi.info"


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query VNOJ for user statistics.

    Args:
        session: aiohttp ClientSession
        username: VNOJ username

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty or user doesn't exist
        RuntimeError: If request fails or parsing fails
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    try:
        async with session.get(
            f"{BASE_URL}/user/{username}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 404:
                raise ValueError("The user does not exist")
            response.raise_for_status()
            html = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    try:
        doc = LexborHTMLParser(html)

        solved_list = await _fetch_solved_list(session, username)
        solved = len(solved_list)
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError("Error while parsing")

    return {
        "solved": solved,
        "submissions": 0,
        "solved_list": solved_list,
    }


def _extract_solved_count(doc: LexborHTMLParser) -> int:
    """Extract solved count from user profile page."""
    for div in doc.css("div.user-sidebar div"):
        text = div.text()
        if "Problems solved:" in text or "Số bài đã giải:" in text:
            match = re.search(r":\s*(\d+)", text)
            if match:
                return int(match.group(1))
    return 0


async def _fetch_solved_list(
    session: aiohttp.ClientSession, username: str
) -> List[str]:
    """Fetch list of solved problems from the solved page."""
    try:
        async with session.get(
            f"{BASE_URL}/user/{username}/solved/",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            html = await response.text()
    except aiohttp.ClientError:
        return []

    doc = LexborHTMLParser(html)
    solved_set = set()

    for link in doc.css("a[href^='/problem/']"):
        href = link.attributes.get("href") or ""
        if href.startswith("/problem/"):
            problem_part = href[9:].rstrip("/")
            if problem_part and "/" not in problem_part:
                solved_set.add(problem_part)

    return sorted(list(solved_set))
