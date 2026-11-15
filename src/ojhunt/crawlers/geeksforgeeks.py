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

__crawler_meta__ = {
    "title": "GeeksforGeeks",
    "description": "Your GeeksforGeeks handle (from the profile URL)",
    "url": "https://www.geeksforgeeks.org/",
    "test_username": "theabbie",
}

PROFILE_URL = "https://authapi.geeksforgeeks.org/api-get/user-profile-info/"
SUBMISSIONS_URL = (
    "https://practiceapi.geeksforgeeks.org/api/v1/user/problems/submissions/"
)
TIMEOUT = aiohttp.ClientTimeout(total=30)


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str] | None]:
    """
    Query GeeksforGeeks for user statistics.

    Args:
        session: aiohttp ClientSession
        username: GeeksforGeeks handle

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
            PROFILE_URL,
            params={"handle": username, "article_count": "false", "redirect": "true"},
            timeout=TIMEOUT,
        ) as response:
            if response.status in (400, 404):
                raise ValueError("The user does not exist")
            if response.status != 200:
                raise RuntimeError(f"Profile request failed: HTTP {response.status}")
            profile = await response.json(content_type=None)

        async with session.post(
            SUBMISSIONS_URL,
            json={"handle": username, "requestType": "", "year": "", "month": ""},
            timeout=TIMEOUT,
        ) as response:
            if response.status in (400, 404, 406):
                raise ValueError("The user does not exist")
            if response.status != 200:
                raise RuntimeError(
                    f"Submissions request failed: HTTP {response.status}"
                )
            data = await response.json(content_type=None)
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")

    try:
        groups = list(data["result"].values())
        slugs = {
            problem["slug"] for problems in groups for problem in problems.values()
        }
    except (AttributeError, KeyError, TypeError) as e:
        raise RuntimeError(f"Unexpected submissions response: {e!s}")

    # The same problem can appear under several submission ids; slugs dedupe.
    solved = len(slugs)
    if solved == 0:
        try:
            solved = int(profile["data"]["total_problems_solved"] or 0)
        except (KeyError, TypeError, ValueError) as e:
            raise RuntimeError(f"Unexpected profile response: {e!s}")

    return {
        "solved": solved,
        # GeeksforGeeks publishes no submission total; report the solved
        # count, which every accepted problem cost at least (ADR 0015).
        "submissions": solved,
        "solved_list": sorted(slugs) if slugs else None,
    }
