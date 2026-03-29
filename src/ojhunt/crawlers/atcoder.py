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
from typing import Dict, Union

__crawler_meta__ = {
    "title": "AtCoder",
    "description": "API provided by kenkoooo (https://github.com/kenkoooo/AtCoderProblems). Only AC number is supported",
    "url": "https://atcoder.jp",
    "test_username": "wata",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, None]]:
    """
    Query AtCoder for user statistics using kenkoooo's API.

    Args:
        session: aiohttp ClientSession
        username: AtCoder username

    Returns:
        Dictionary with keys: solved, submissions, solved_list (None)

    Raises:
        ValueError: If username is empty or user doesn't exist
        RuntimeError: If request fails
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    # First check if user exists on AtCoder
    try:
        async with session.get(
            f"https://atcoder.jp/users/{username}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 404:
                raise ValueError("The user does not exist")
            response.raise_for_status()
    except aiohttp.ClientError as e:
        if isinstance(e, aiohttp.ClientResponseError) and e.status == 404:
            raise ValueError("The user does not exist")
        raise RuntimeError(f"Request failed: {str(e)}")

    # Query kenkoooo's API for AC count
    # Thank @kenkoooo for the API
    # Source code: https://github.com/kenkoooo/AtCoderProblems
    try:
        async with session.get(
            "https://kenkoooo.com/atcoder/atcoder-api/v3/user/ac_rank",
            params={"user": username},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            data = await response.json()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    solved = data.get("count", 0)

    return {
        "solved": solved,
        "submissions": solved,  # API only provides AC count
        "solved_list": None,  # Problem list not available from this API
    }
