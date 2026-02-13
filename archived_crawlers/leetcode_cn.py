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
    "title": "LeetCode_CN",
    "description": "",
    "url": "https://leetcode.cn",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, None]]:
    """
    Query LeetCode China for user statistics.

    Args:
        username: LeetCode CN username

    Returns:
        Dictionary with keys: solved, submissions, solved_list (None)

    Raises:
        ValueError: If username is empty or user doesn't exist
        RuntimeError: If request fails
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    # GraphQL query
    graphql_query = {
        "query": """
        query userSessionProgress($userSlug:String!){
          userProfileUserQuestionSubmitStats(userSlug:$userSlug){
            acSubmissionNum {
              difficulty
              count
            }
            totalSubmissionNum {
              difficulty
              count
            }
          }
        }""",
        "variables": {"userSlug": username},
    }

    try:
        async with session.post(
            "https://leetcode.cn/graphql/",
            json=graphql_query,
            headers={"User-Agent": "ojhunt/1.0.0"},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            data = await response.json()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    # Parse response
    try:
        user_data = data["data"]["userProfileUserQuestionSubmitStats"]
        ac_list = user_data["acSubmissionNum"]
        sub_list = user_data["totalSubmissionNum"]

        # Check if user exists (both lists empty means user doesn't exist)
        if len(ac_list) == 0 and len(sub_list) == 0:
            raise ValueError("The user does not exist")

        # Sum up counts across all difficulty levels
        solved = sum(item["count"] for item in ac_list)
        submissions = sum(item["count"] for item in sub_list)

        return {
            "solved": solved,
            "submissions": submissions,
            "solved_list": None,  # Not provided by this API
        }
    except (KeyError, TypeError) as e:
        raise RuntimeError(f"Error parsing response: {str(e)}")
