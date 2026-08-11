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

__crawler_meta__ = {
    "title": "51Nod",
    "description": "Please use your numeric user ID (visible in your profile URL)",
    "url": "https://www.51nod.com",
    "test_username": "10000",
}

BASE_URL = "https://www.51nod.com"


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str] | None]:
    """
    Query 51Nod for user statistics.

    Args:
        session: aiohttp ClientSession
        username: Numeric 51Nod user ID, visible in the profile URL — a display
            name is rejected

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty, not numeric, or the user does not exist
        RuntimeError: If the request fails
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    user_id = username.strip()

    if not user_id.isdigit():
        raise ValueError("51Nod requires a numeric user ID (not a username)")

    try:
        async with session.get(
            f"{BASE_URL}/Api/Challenge/UserIndex",
            params={"userId": user_id},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 404:
                raise ValueError("The user does not exist")
            response.raise_for_status()
            data = await response.json()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")

    user_stat = data.get("UserStat")
    if not user_stat:
        raise ValueError("The user does not exist")

    solved_list = []
    for table in data.get("ProblemTables", []):
        for problem in table.get("ProblemInfos", []):
            user_problem = problem.get("UserProblemSimplify")
            if user_problem and user_problem.get("IsAccepted"):
                problem_id = str(
                    problem.get("ProblemSimplify", {}).get("ProblemId", "")
                )
                if problem_id:
                    solved_list.append(problem_id)

    return {
        "solved": user_stat.get("ProblemAcceptedCount", 0),
        "submissions": user_stat.get("ProblemSubmitCount", 0),
        "solved_list": solved_list,
    }
