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
    "title": "ICPC Live Archive",
    "description": "",
    "url": "https://icpcarchive.ecs.baylor.edu/index.php",
}

PREFIX = "https://icpcarchive.ecs.baylor.edu/uhunt"


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query ICPC Live Archive for user statistics.

    Args:
        username: ICPC Live Archive username

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
        # Get user ID from username
        async with session.get(
            f"{PREFIX}/api/uname2uid/{username}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            uid = await response.json()

            if uid == 0:
                raise ValueError("The user does not exist")

        # Get user submissions
        async with session.get(
            f"{PREFIX}/api/subs-user/{uid}", timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            data = await response.json()

            ac_set = set()
            problem_array = data.get("subs", [])

            for element in problem_array:
                # element[2] == 90 means accepted
                if element[2] == 90:
                    ac_set.add(element[1])

        # TODO: Remove dependency on ojhunt.com API
        # The ojhunt API converts UVALive internal problem IDs to display numbers
        # Consider alternatives:
        # 1. Use UVALive's own problem number mapping if available
        # 2. Display internal IDs directly
        # 3. Build a local mapping database
        # 4. Use community-maintained problem lists
        async with session.post(
            "https://ojhunt.com/api/ohunt/problems/resolve-label",
            json={
                "onlineJudge": "uvalive",
                "list": list(ac_set),
            },
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            resolve_data = await response.json()
            solved_list = list(resolve_data.get("result", {}).values())

        return {
            "solved": len(ac_set),
            "submissions": len(problem_array),
            "solved_list": solved_list,
        }

    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError("Error while parsing")
