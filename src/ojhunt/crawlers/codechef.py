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

__crawler_meta__ = {
    "title": "CodeChef",
    "description": "Only the solved count is available. Submissions report the solved count.",
    "url": "https://www.codechef.com/",
    "test_username": "vjudge",
}

_SOLVED_PATTERN = re.compile(r"Total Problems Solved:\s*(\d+)")


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str] | None]:
    """
    Query CodeChef for user statistics.

    Reads "Total Problems Solved" from the user's public profile page. The page names no
    problem codes and no submission total, so solved_list is None and submissions is the
    solved count.

    Args:
        session: aiohttp ClientSession
        username: CodeChef username

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty or the user does not exist
        RuntimeError: If CodeChef blocks the request, or the page cannot be fetched or parsed
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    try:
        async with session.get(
            f"https://www.codechef.com/users/{username}",
            allow_redirects=False,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if 300 <= response.status < 400:
                raise ValueError("The user does not exist")
            if (
                response.status == 429
                and response.headers.get("cf-mitigated") == "challenge"
            ):
                raise RuntimeError(
                    "CodeChef is challenging automated requests (Cloudflare); retry later"
                )
            if response.status != 200:
                raise RuntimeError(f"Server Response Error: {response.status}")
            html = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")

    doc = LexborHTMLParser(html)
    for heading in doc.css("section.problems-solved h3"):
        match = _SOLVED_PATTERN.search(heading.text())
        if match:
            solved = int(match.group(1))
            return {"solved": solved, "submissions": solved, "solved_list": None}

    raise RuntimeError("Error while parsing")
