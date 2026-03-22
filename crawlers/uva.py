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
from typing import Dict, List, Optional, Union

from crawlers._utils import resolve_labels

__crawler_meta__ = {
    "title": "UVA",
    "description": "",
    "url": "https://uva.onlinejudge.org/",
    "test_username": "leoloveacm",
}

UHUNT_PREFIX = "https://uhunt.onlinejudge.org"


async def _resolve_label(
    session: aiohttp.ClientSession, problem_id: int
) -> Optional[str]:
    """
    Resolve UVA problem ID to display number using uhunt API.

    Args:
        session: aiohttp ClientSession
        problem_id: UVA internal problem ID

    Returns:
        Display number as string, or None if resolution failed
    """
    try:
        async with session.get(
            f"{UHUNT_PREFIX}/api/p/id/{problem_id}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status != 200:
                return None
            data = await response.json()
            return str(data.get("num", problem_id))
    except Exception:
        return None


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query UVA Online Judge for user statistics using UHunt API.

    UVA API: https://uhunt.onlinejudge.org/api
    Note: UVA doesn't support pagination, so all data is fetched at once.

    Args:
        session: aiohttp ClientSession
        username: UVA username

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty or user doesn't exist
        RuntimeError: If request fails
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    try:
        async with session.get(
            f"{UHUNT_PREFIX}/api/uname2uid/{username}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            uid = await response.json()

            if uid == 0:
                raise ValueError("The user does not exist")
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    try:
        async with session.get(
            f"{UHUNT_PREFIX}/api/subs-user/{uid}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            data = await response.json()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    ac_set = set()
    problem_array = data.get("subs", [])

    for element in problem_array:
        if len(element) >= 3 and element[2] == 90:
            ac_set.add(element[1])

    problem_ids = list(ac_set)

    label_mappings = await resolve_labels(session, "uva", problem_ids, _resolve_label)

    solved_list = []
    for pid in problem_ids:
        label = label_mappings.get(pid)
        if label:
            solved_list.append(label)
        else:
            solved_list.append(str(pid))

    return {
        "solved": len(ac_set),
        "submissions": len(problem_array),
        "solved_list": solved_list,
    }
