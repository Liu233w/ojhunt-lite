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
    "title": "Sort-Me",
    "description": (
        "Please use your numeric user ID (visible in your profile URL, "
        "sort-me.org/profile/<id>)"
    ),
    "url": "https://sort-me.org/",
    "test_username": "5000",
}

USER_URL = "https://api.sort-me.org/getUserById"
TIMEOUT = aiohttp.ClientTimeout(total=30)


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str] | None]:
    """
    Query Sort-Me for user statistics.

    Args:
        session: aiohttp ClientSession
        username: Numeric Sort-Me user ID, visible in the profile URL
            (sort-me.org/profile/<id>); a login is rejected

    Returns:
        Dictionary with keys: solved, submissions, solved_list. Sort-Me shows
        no submission total or solved list to guests, so submissions equals
        solved and solved_list is None.

    Raises:
        ValueError: If username is empty, not numeric, or the user does not exist
        RuntimeError: If the request fails or the response cannot be parsed
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    user_id = username.strip()

    if not user_id.isascii() or not user_id.isdigit():
        raise ValueError("Sort-Me requires a numeric user ID (not a username)")

    try:
        async with session.get(
            USER_URL, params={"id": user_id}, timeout=TIMEOUT
        ) as response:
            if response.status == 404:
                raise ValueError("The user does not exist")
            if response.status != 200:
                raise RuntimeError(f"Request failed: HTTP {response.status}")
            data = await response.json(content_type=None)
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")

    try:
        solved = int(data["regal"]["statistics"]["total"])
    except (KeyError, TypeError, ValueError) as e:
        raise RuntimeError(f"Unexpected response: {e!s}")

    return {
        "solved": solved,
        # Sort-Me publishes no submission total to guests; report the solved
        # count, which every accepted problem cost at least (ADR 0015).
        "submissions": solved,
        "solved_list": None,
    }
