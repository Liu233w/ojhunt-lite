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
from typing import Dict, List, Union

__crawler_meta__ = {
    "title": "Baekjoon Online Judge",
    "description": "Uses solved.ac API for solved count",
    "url": "https://www.acmicpc.net/",
    "test_username": "xiaowuc1",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str], None]]:
    """
    Query Baekjoon Online Judge for user statistics.

    Args:
        session: aiohttp ClientSession
        username: Baekjoon handle

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty or user doesn't exist
        RuntimeError: If request fails or parsing fails
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    solved = await _fetch_solved_count(session, username)
    submissions, solved_list = await _fetch_user_profile(session, username)

    return {
        "solved": solved,
        "submissions": submissions,
        "solved_list": solved_list,
    }


async def _fetch_solved_count(session: aiohttp.ClientSession, username: str) -> int:
    """
    Fetch solved count from solved.ac API.

    Args:
        session: aiohttp ClientSession
        username: Baekjoon handle

    Returns:
        Number of solved problems

    Raises:
        ValueError: If user doesn't exist (404)
        RuntimeError: If request fails
    """
    try:
        async with session.get(
            "https://solved.ac/api/v3/user/show",
            params={"handle": username},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 404:
                raise ValueError("The user does not exist")
            response.raise_for_status()
            data = await response.json()
            return data.get("solvedCount", 0)
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")


async def _fetch_user_profile(
    session: aiohttp.ClientSession, username: str
) -> tuple[int, List[str]]:
    """
    Fetch submissions count and solved list from user profile page.

    Args:
        session: aiohttp ClientSession
        username: Baekjoon handle

    Returns:
        Tuple of (submissions count, solved_list)

    Raises:
        RuntimeError: If request fails or parsing fails
    """
    try:
        async with session.get(
            f"https://www.acmicpc.net/user/{username}",
            headers=HEADERS,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            html = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    try:
        doc = LexborHTMLParser(html)

        submissions_link = doc.css_first("a[href*='/status?user_id=']")
        if submissions_link:
            submissions_text = submissions_link.text()
            submissions = int(submissions_text) if submissions_text else 0
        else:
            submissions = 0

        solved_list = []
        problem_list_div = doc.css_first("div.problem-list")
        if problem_list_div:
            for link in problem_list_div.css("a"):
                problem_id = link.text(strip=True)
                if problem_id:
                    solved_list.append(problem_id)

        return submissions, solved_list
    except Exception as e:
        raise RuntimeError(f"Error while parsing: {str(e)}")
