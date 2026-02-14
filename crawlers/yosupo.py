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
    "title": "Yosupo Judge",
    "description": "Library Checker (judge.yosupo.jp)",
    "url": "https://judge.yosupo.jp/",
}

API_BASE_URL = "https://v3.api.judge.yosupo.jp"


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query Yosupo Judge for user statistics.

    Args:
        session: aiohttp ClientSession
        username: Yosupo Judge username

    Returns:
        Dictionary with keys: solved, solved_list

    Raises:
        ValueError: If username is empty or user doesn't exist
        RuntimeError: If network request fails
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    user_info = await _fetch_user_info(session, username)
    statistics = await _fetch_user_statistics(session, username)

    solved_map = statistics.get("solved_map", {})
    solved_list = [
        name for name, status in solved_map.items() if status in ("AC", "LATEST_AC")
    ]

    return {
        "solved": len(solved_list),
        "submissions": 0,
        "solved_list": sorted(solved_list),
    }


async def _fetch_user_info(session: aiohttp.ClientSession, username: str) -> Dict:
    """
    Fetch user info from Yosupo Judge API.

    Args:
        session: aiohttp ClientSession
        username: Yosupo Judge username

    Returns:
        User info dictionary

    Raises:
        ValueError: If user doesn't exist
        RuntimeError: If network request fails
    """
    url = f"{API_BASE_URL}/users/{username}"

    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            text = await response.text()

            if response.status == 200:
                import json

                return json.loads(text)
            elif "invalid user name" in text.lower():
                raise ValueError("The user does not exist")
            else:
                raise RuntimeError(f"API error: {response.status} {text}")

    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")


async def _fetch_user_statistics(session: aiohttp.ClientSession, username: str) -> Dict:
    """
    Fetch user statistics from Yosupo Judge API.

    Args:
        session: aiohttp ClientSession
        username: Yosupo Judge username

    Returns:
        Statistics dictionary with solved_map

    Raises:
        RuntimeError: If network request fails
    """
    url = f"{API_BASE_URL}/users/{username}/statistics"

    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status != 200:
                text = await response.text()
                raise RuntimeError(f"API error: {response.status} {text}")

            import json

            return json.loads(await response.text())

    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")
