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
from typing import Dict, List, Union

__crawler_meta__ = {
    "title": "yukicoder",
    "description": "Japanese competitive programming platform",
    "url": "https://yukicoder.me/",
}

API_BASE = "https://yukicoder.me/api/v1"


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query yukicoder for user statistics.

    Args:
        session: aiohttp ClientSession
        username: yukicoder username

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty or user doesn't exist
        RuntimeError: If request fails or parsing fails
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    user_url = f"{API_BASE}/user/name/{username}"

    try:
        async with session.get(
            user_url, timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 404:
                raise ValueError("The user does not exist")
            response.raise_for_status()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    solved_list = await _fetch_solved_list(session, username)

    return {
        "solved": len(solved_list),
        "submissions": 0,
        "solved_list": solved_list,
    }


async def _fetch_solved_list(
    session: aiohttp.ClientSession, username: str
) -> List[str]:
    """
    Fetch the list of solved problems for a user.

    Args:
        session: aiohttp ClientSession
        username: yukicoder username

    Returns:
        List of solved problem IDs as strings
    """
    solved_url = f"{API_BASE}/solved/name/{username}"

    try:
        async with session.get(
            solved_url, timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return [str(item.get("No", item.get("ProblemId", ""))) for item in data]
    except aiohttp.ClientError:
        return []
