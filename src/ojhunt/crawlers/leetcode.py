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
    "title": "LeetCode.com",
    "description": "LeetCode (international)",
    "url": "https://leetcode.com/",
    "test_username": "tourist",
}

_GRAPHQL_URL = "https://leetcode.com/graphql"

_PROFILE_QUERY = """
query getUserProfile($username: String!) {
  matchedUser(username: $username) {
    submitStatsGlobal {
      acSubmissionNum {
        count
        submissions
      }
    }
  }
}
"""


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str]]:
    """
    Query LeetCode for user statistics via the public GraphQL API.

    Args:
        session: aiohttp ClientSession
        username: LeetCode username

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty or user doesn't exist
        RuntimeError: If API returns an error or network failure occurs
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    payload = {
        "query": _PROFILE_QUERY,
        "variables": {"username": username},
    }

    try:
        async with session.post(
            _GRAPHQL_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Referer": "https://leetcode.com/",
            },
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"LeetCode API returned HTTP {response.status}")
            data = await response.json()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")

    if "errors" in data:
        errors = data["errors"]
        # LeetCode returns a GraphQL error (not null matchedUser) when user doesn't exist
        if any("does not exist" in e.get("message", "") for e in errors):
            raise ValueError("The user does not exist")
        raise RuntimeError(f"GraphQL error: {errors}")

    matched_user = data.get("data", {}).get("matchedUser")
    if matched_user is None:
        raise ValueError("The user does not exist")

    ac_submission_num = matched_user.get("submitStatsGlobal", {}).get(
        "acSubmissionNum", []
    )

    # acSubmissionNum[0] is the "All" difficulty entry (total)
    if not ac_submission_num:
        raise RuntimeError("Unexpected API response: acSubmissionNum is empty")

    all_entry = ac_submission_num[0]
    solved = all_entry.get("count", 0)
    submissions = all_entry.get("submissions", 0)

    return {
        "solved": solved,
        "submissions": submissions,
        "solved_list": None,  # LeetCode does not expose the full solved list publicly
    }
