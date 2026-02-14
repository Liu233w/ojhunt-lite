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
    "title": "51Nod",
    "description": "Please use your nickname (displayed in your home page)",
    "url": "https://www.51nod.com",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query 51Nod for user statistics.

    Args:
        username: 51Nod username (nickname)

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
        # Search for user to get user ID
        async with session.get(
            "https://www.51nod.com/SearchReader/TitleOnly",
            params={"searchStr": username},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"Server Response Error: {response.status}")

            search_data = await response.json()

            if not search_data:
                raise ValueError("The user does not exist")

            # Find user ID in search results
            user_id = None
            for item in search_data:
                if item.get("Content") == username and item.get("ContentType") == 2:
                    user_id = item.get("LinkId")
                    break

            if user_id is None:
                raise ValueError("The user does not exist")

        # Get user challenge data
        try:
            async with session.get(
                "https://www.51nod.com/Challenge/UserIndex",
                params={"userId": user_id},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 404:
                    raise ValueError("The user does not exist")
                if response.status != 200:
                    raise RuntimeError(f"Server Response Error: {response.status}")

                user_data = await response.json()
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                raise ValueError("The user does not exist")
            raise

        # Extract solved list from problem tables
        solved_list = []
        for table in user_data.get("ProblemTables", []):
            for problem in table.get("ProblemInfos", []):
                user_problem = problem.get("UserProblemSimplify")
                if user_problem and user_problem.get("IsAccepted"):
                    problem_id = str(
                        problem.get("ProblemSimplify", {}).get("ProblemId", "")
                    )
                    solved_list.append(problem_id)

        user_stat = user_data.get("UserStat", {})

        return {
            "solved": user_stat.get("ProblemAcceptedCount", 0),
            "submissions": user_stat.get("ProblemSubmitCount", 0),
            "solved_list": solved_list,
        }

    except aiohttp.ClientError as e:
        if "404" in str(e):
            raise ValueError("The user does not exist")
        raise RuntimeError(f"Request failed: {str(e)}")
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError("Error while parsing")
