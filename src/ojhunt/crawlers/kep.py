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

__crawler_meta__ = {
    "title": "KEP.uz",
    "description": "Your KEP.uz username (from the profile URL)",
    "url": "https://kep.uz/",
    "test_username": "physics",
}

API_URL = "https://kep.uz/api"
TIMEOUT = aiohttp.ClientTimeout(total=30)


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str] | None]:
    """
    Query KEP.uz for user statistics.

    Args:
        session: aiohttp ClientSession
        username: KEP.uz username

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
            f"{API_URL}/problems-rating/{quote(username, safe='')}/",
            timeout=TIMEOUT,
        ) as response:
            if response.status == 404:
                raise ValueError("The user does not exist")
            if response.status != 200:
                raise RuntimeError(f"Rating request failed: HTTP {response.status}")
            rating = await response.json(content_type=None)

        try:
            canonical_name = rating["user"]["username"]
            solved = int(rating["solved"])
        except (KeyError, TypeError, ValueError) as e:
            raise RuntimeError(f"Unexpected rating response: {e!s}")

        async with session.get(
            f"{API_URL}/attempts/",
            params={"username": canonical_name, "pageSize": "1"},
            timeout=TIMEOUT,
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"Attempts request failed: HTTP {response.status}")
            attempts = await response.json(content_type=None)
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")

    try:
        submissions = int(attempts["total"])
        owners = {row["user"]["username"] for row in attempts["data"]}
    except (KeyError, TypeError, ValueError) as e:
        raise RuntimeError(f"Unexpected attempts response: {e!s}")

    # Without a working filter the endpoint reports the site-wide total, so
    # accept the figure only if the returned rows belong to this user.
    if owners - {canonical_name}:
        raise RuntimeError("Attempts response was not filtered by username")

    return {
        "solved": solved,
        "submissions": max(submissions, solved),
        # The attempts API pages 50 rows at a time, so listing every solved
        # problem would take an unbounded number of requests.
        "solved_list": None,
    }
