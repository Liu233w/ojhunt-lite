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
    "title": "Kilonova",
    "description": "Romanian competitive programming platform",
    "url": "https://kilonova.ro/",
    "test_username": "AlexVasiluta",
}

BASE_URL = "https://kilonova.ro/api"


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query Kilonova for user statistics.

    Args:
        session: aiohttp ClientSession
        username: Kilonova username

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
            f"{BASE_URL}/user/byName/{username}/solvedProblems",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 404:
                raise ValueError("The user does not exist")

            data = await response.json()

            if data.get("status") == "error":
                if "not found" in data.get("data", "").lower():
                    raise ValueError("The user does not exist")
                raise RuntimeError(data.get("data", "Unknown error"))

            problems = data.get("data", [])

            solved_list = [str(p["id"]) for p in problems]

            return {
                "solved": len(solved_list),
                # Kilonova publishes no submission total; report the solved
                # count, which every accepted problem cost at least (ADR 0015).
                "submissions": len(solved_list),
                "solved_list": sorted(solved_list, key=int),
            }

    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")
