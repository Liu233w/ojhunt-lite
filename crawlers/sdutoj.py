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
    "title": "SDUT OJ",
    "description": "",
    "url": "https://oj.sdutacm.cn/",
}


async def _fetch_sdutoj(session: aiohttp.ClientSession, api: str, data: dict) -> dict:
    """
    Helper function to fetch SDUT OJ API.

    Args:
        session: aiohttp ClientSession
        api: API endpoint
        data: Request data

    Returns:
        Response data

    Raises:
        RuntimeError: If request fails
    """
    async with session.post(
        f"https://oj.sdutacm.cn/onlinejudge3/api/{api}",
        json=data,
        headers={"Content-Type": "application/json;charset=utf-8"},
        timeout=aiohttp.ClientTimeout(total=30),
    ) as response:
        body = await response.json()

        if not (response.status == 200 and body and body.get("success")):
            code = body.get("code", "") if body else ""
            raise RuntimeError(
                f"Server Response Error: {response.status}, code: {code}"
            )

        return body.get("data", {})


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query SDUT OJ for user statistics.

    Args:
        username: SDUT OJ username

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty or user doesn't exist
        RuntimeError: If API returns an error
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    try:
        # Search for user
        user_search_data = await _fetch_sdutoj(
            session,
            "getUserList",
            {
                "username": username,
                "page": 1,
                "order": [["accepted", "DESC"]],
                "limit": 1000,
            },
        )

        # Find exact username match
        user = None
        for u in user_search_data.get("rows", []):
            if u.get("username") == username:
                user = u
                break

        if not user:
            raise ValueError("The user does not exist")

        user_id = user.get("userId")

        # Fetch user stats and details in parallel
        stats_data = await _fetch_sdutoj(
            session, "getUserProblemResultStats", {"userId": user_id}
        )

        detail_data = await _fetch_sdutoj(session, "getUserDetail", {"userId": user_id})

        solved_list = [str(pid) for pid in stats_data.get("acceptedProblemIds", [])]

        return {
            "solved": detail_data.get("accepted", 0),
            "submissions": detail_data.get("submitted", 0),
            "solved_list": solved_list,
        }

    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError("Error while parsing")
