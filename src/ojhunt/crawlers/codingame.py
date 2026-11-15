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
    "title": "CodinGame",
    "description": (
        "Your CodinGame public handle: the long hexadecimal string at the end "
        "of your profile URL (codingame.com/profile/...). Nicknames cannot be "
        "looked up. Solved counts the puzzles solved in the language where "
        "you solved the most, so it is a lower bound."
    ),
    "url": "https://www.codingame.com/",
    "test_username": "b528dd3b279d7578674a1129305918e0400484",
}

API_URL = "https://www.codingame.com/services"
TIMEOUT = aiohttp.ClientTimeout(total=30)


async def _post(session: aiohttp.ClientSession, service: str, body: list):
    async with session.post(
        f"{API_URL}/{service}", json=body, timeout=TIMEOUT
    ) as response:
        if response.status != 200:
            raise RuntimeError(f"{service} request failed: HTTP {response.status}")
        return await response.json(content_type=None)


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str] | None]:
    """
    Query CodinGame for user statistics.

    Args:
        session: aiohttp ClientSession
        username: CodinGame public handle (from the profile URL)

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
        stats = await _post(
            session, "CodinGamer/findCodingamePointsStatsByHandle", [username]
        )
        if stats is None:
            raise ValueError("The user does not exist")
        try:
            user_id = int(stats["codingamer"]["userId"])
        except (KeyError, TypeError, ValueError) as e:
            raise RuntimeError(f"Unexpected profile response: {e!s}")

        languages = await _post(
            session, "Puzzle/countSolvedPuzzlesByProgrammingLanguage", [user_id]
        )
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")

    try:
        # A puzzle solved in several languages is counted once per language, so
        # the busiest language is the best known lower bound of distinct puzzles.
        solved = max((int(row["puzzleCount"]) for row in languages), default=0)
    except (KeyError, TypeError, ValueError) as e:
        raise RuntimeError(f"Unexpected puzzle response: {e!s}")

    return {
        "solved": solved,
        # CodinGame publishes no submission total.
        "submissions": solved,
        "solved_list": None,
    }
