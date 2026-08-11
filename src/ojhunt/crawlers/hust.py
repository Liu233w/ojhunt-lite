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
    "title": "HUST",
    "description": "HUST Online Judge",
    "url": "https://hustoj.org/",
    "test_username": "freefcw",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str] | None]:
    """
    Query HUST Online Judge for user statistics.

    Args:
        username: HUST username

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
            f"https://hustoj.org/user/{username}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            html = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")

    try:
        doc = LexborHTMLParser(html)

        title = doc.css_first("title")
        if title is None or "Profile ::" not in title.text():
            raise ValueError("The user does not exist")

        solved_text = None
        submissions_text = None

        for li in doc.css("li"):
            text = li.text(strip=True)
            if text.startswith("Submit:"):
                submissions_text = text.replace("Submit:", "").strip()
            elif text.startswith("Solved:"):
                solved_text = text.replace("Solved:", "").strip()

        if solved_text is None or submissions_text is None:
            raise RuntimeError("Error while parsing")

        solved = int(solved_text)
        submissions = int(submissions_text)

        return {
            "solved": solved,
            "submissions": submissions,
            "solved_list": None,
        }
    except ValueError:
        raise
    except Exception:
        raise RuntimeError("Error while parsing")
