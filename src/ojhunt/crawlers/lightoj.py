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
    "title": "LightOJ",
    "url": "https://lightoj.com/",
    "test_username": "flash_7",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    if " " in username:
        raise ValueError("The user does not exist")

    try:
        async with session.get(
            f"https://lightoj.com/api/v1/users/{username}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 404:
                raise ValueError("The user does not exist")

            data = await response.json()

    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    data_obj = data.get("data") if isinstance(data, dict) else None
    if not isinstance(data_obj, dict) or "userStat" not in data_obj:
        raise ValueError("The user does not exist")

    user_stat = data_obj["userStat"]

    try:
        solved = int(user_stat["isSolved"])
        submissions = int(user_stat["numSubmissions"])
    except (KeyError, ValueError, TypeError) as e:
        raise RuntimeError(f"Failed to parse response: {str(e)}")

    return {
        "solved": solved,
        "submissions": submissions,
        "solved_list": None,
    }
