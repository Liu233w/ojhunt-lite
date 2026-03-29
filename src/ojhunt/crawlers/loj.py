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
from datetime import datetime, timezone

__crawler_meta__ = {
    "title": "LibreOJ",
    "description": "",
    "url": "https://loj.ac/",
    "test_username": "cz_xuyixuan",
}


async def _resolve_solved_list(
    session: aiohttp.ClientSession, username: str
) -> List[str]:
    """
    Resolve solved list by querying submission API.

    Args:
        session: aiohttp ClientSession
        username: LOJ username

    Returns:
        List of solved problem IDs
    """
    ac_set = set()
    max_id = None

    while True:
        payload = {
            "submitter": username,
            "status": "Accepted",
            "locale": "en_US",
            "takeCount": 10,
        }
        if max_id is not None:
            payload["maxId"] = max_id

        async with session.post(
            "https://api.loj.ac/api/submission/querySubmission",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            data = await response.json()

            submissions = data.get("submissions", [])
            if not submissions:
                break

            for item in submissions:
                problem_id = str(item.get("problem", {}).get("id", ""))
                ac_set.add(problem_id)
                max_id = item.get("id", 0) - 1

    return list(ac_set)


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query LibreOJ for user statistics.

    Args:
        username: LOJ username

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
        # Get user details
        async with session.post(
            "https://api.loj.ac/api/user/getUserDetail",
            json={
                "now": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "timezone": "UTC",
                "username": username,
            },
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status not in (200, 201):
                raise RuntimeError(f"Server Response Error: {response.status}")

            data = await response.json()

            if data.get("error"):
                raise ValueError("The user does not exist")

            submissions = data.get("meta", {}).get("submissionCount", 0)

        # Get solved list
        solved_list = await _resolve_solved_list(session, username)
        # If a submission is not public, it can be different from the value of the user api
        solved = len(solved_list)

        return {
            "solved": solved,
            "submissions": submissions,
            "solved_list": solved_list,
        }

    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")
    except ValueError:
        raise
    except Exception:
        raise RuntimeError("Error while parsing")
