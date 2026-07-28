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

import json
import aiohttp
from typing import Dict, List, Union

__crawler_meta__ = {
    "title": "EOlymp",
    "description": "Submission count reflects accepted submissions only.",
    "url": "https://www.eolymp.com/",
    "test_username": "vjudge5",
}

GRAPHQL_URL = (
    "https://api.eolymp.com/spaces/00000000-0000-0000-0000-000000000000/graphql"
)


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str], None]]:
    """
    Query EOlymp for user statistics.

    Args:
        username: EOlymp username (display name)

    Returns:
        Dictionary with keys: solved, submissions

    Raises:
        ValueError: If username is empty or user doesn't exist
        RuntimeError: If request fails or parsing fails
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    query_str = """
    {
        members(first: 1, search: "%s") {
            nodes {
                id
                displayName
                stats {
                    problemsSolved
                    submissionsAccepted
                }
            }
        }
    }
    """ % username.replace('"', '\\"')

    try:
        async with session.post(
            GRAPHQL_URL,
            json={"query": query_str},
            headers={"Content-Type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            data = await response.json()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")
    except json.JSONDecodeError:
        raise RuntimeError("Failed to parse response")

    if "errors" in data:
        raise RuntimeError(
            f"GraphQL error: {data['errors'][0].get('message', 'Unknown error')}"
        )

    nodes = data.get("data", {}).get("members", {}).get("nodes", [])

    if not nodes:
        raise ValueError("The user does not exist")

    user = nodes[0]

    if user.get("displayName", "").lower() != username.lower():
        raise ValueError("The user does not exist")

    stats = user.get("stats", {})

    solved = stats.get("problemsSolved", 0)

    return {
        "solved": solved,
        # EOlymp counts accepted submissions only, and the field can be absent;
        # solved is the floor either way (ADR 0015).
        "submissions": max(stats.get("submissionsAccepted", 0), solved),
        "solved_list": None,
    }
