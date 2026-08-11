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
    "title": "CodeChef",
    "description": "",
    "url": "https://www.codechef.com/",
    "test_username": "vjudge",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str]]:
    """
    Query CodeChef for user statistics.

    Walks the user's public submission pages and counts distinct accepted problems.

    Args:
        session: aiohttp ClientSession
        username: CodeChef username

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty, or the user does not exist / has no submissions
        RuntimeError: If a submission page cannot be fetched or parsed
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()
    submissions = 0
    solved_set = set()
    page = 1
    max_page = 1

    try:
        while page <= max_page:
            async with session.get(
                f"https://www.codechef.com/recent/user?page={page}&user_handle={username}",
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Server Response Error: {response.status}")
                data = await response.json(content_type=None)

            html = data.get("content", "")
            max_page = data.get("max_page", 1) if page == 1 else max_page

            doc = LexborHTMLParser(html)
            for tr in doc.css("table.dataTable tbody tr"):
                problem_link = tr.css_first("td:nth-child(2) a")
                result_span = tr.css_first("td:nth-child(3) span")

                if not problem_link:
                    continue

                submissions += 1
                if result_span and result_span.attributes.get("title") == "accepted":
                    solved_set.add(problem_link.text(strip=True))

            page += 1

        if submissions == 0:
            raise ValueError("User not exist or has no submission")

        return {
            "solved": len(solved_set),
            "submissions": submissions,
            "solved_list": sorted(solved_set),
        }

    except ValueError:
        raise
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")
    except Exception:
        raise RuntimeError("Error while parsing")
