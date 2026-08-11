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
    "title": "CodeForces",
    "description": "Including CodeForces::Gym",
    "url": "http://codeforces.com/",
    "test_username": "leoloveacm",
}

MAX_PAGE_SIZE = 10000


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str]]:
    """
    Query CodeForces for user statistics.

    Args:
        session: aiohttp ClientSession
        username: CodeForces handle

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty or user doesn't exist
        RuntimeError: If API returns an error
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    ac_set = set()
    submissions = await _query_recursively(session, username, 1, ac_set)

    return {
        "solved": len(ac_set),
        "submissions": submissions,
        "solved_list": sorted(ac_set),
    }


async def _query_recursively(
    session: aiohttp.ClientSession, username: str, page: int, ac_set: set
) -> int:
    """
    Recursively query CodeForces API for all submissions.

    Args:
        session: aiohttp ClientSession
        username: CodeForces handle
        page: Current page number (1-indexed)
        ac_set: Set to accumulate accepted problem IDs

    Returns:
        Total number of submissions retrieved

    Raises:
        ValueError: If user doesn't exist
        RuntimeError: If API returns an error
    """
    params = {
        "handle": username,
        "from": (page - 1) * MAX_PAGE_SIZE + 1,
        "count": MAX_PAGE_SIZE,
    }

    try:
        async with session.get(
            "http://codeforces.com/api/user.status",
            params=params,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            data = await response.json()

            # Check response status in JSON
            if data.get("status") != "OK":
                comment = data.get("comment", "Unknown error")
                if "handle: User with handle" in comment and "not found" in comment:
                    raise ValueError("The user does not exist")
                if "handle: Field should contain only Latin letters" in comment:
                    raise ValueError(comment)
                raise RuntimeError(comment)

    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")

    problem_array = data.get("result", [])

    if not problem_array:
        return 0

    # Process submissions
    for element in problem_array:
        if element.get("verdict") == "OK":
            problem = element.get("problem", {})
            contest_id = problem.get("contestId", "")
            index = problem.get("index", "")
            title = f"{contest_id}{index}"
            ac_set.add(title)

    total = len(problem_array)

    # Check if we need to fetch more pages
    if total < MAX_PAGE_SIZE:
        return total
    else:
        return total + await _query_recursively(session, username, page + 1, ac_set)
