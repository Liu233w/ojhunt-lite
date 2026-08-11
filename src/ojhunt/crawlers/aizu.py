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
    "title": "AIZU",
    "description": "",
    "url": "http://judge.u-aizu.ac.jp/onlinejudge/index.jsp",
    "test_username": "vjudge5",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str]]:
    """
    Query AIZU for user statistics.

    Args:
        username: AIZU username

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
        # Get user status
        try:
            async with session.get(
                f"https://judgeapi.u-aizu.ac.jp/users/{username}",
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 404:
                    raise ValueError("The user does not exist")
                if response.status != 200:
                    raise RuntimeError(f"Server Response Error: {response.status}")

                status_data = await response.json()
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                raise ValueError("The user does not exist")
            raise

        # Get solved list - the list seems big enough, we don't need pages
        async with session.get(
            f"https://judgeapi.u-aizu.ac.jp/solutions/users/{username}",
            params={"page": "0", "size": "10000"},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            list_data = await response.json()

            # Extract unique problem IDs
            solved_set = {item.get("problemId") for item in list_data}

            return {
                "solved": status_data.get("status", {}).get("solved", 0),
                "submissions": status_data.get("status", {}).get("submissions", 0),
                "solved_list": list(solved_set),
            }

    except aiohttp.ClientError as e:
        if "404" in str(e):
            raise ValueError("The user does not exist")
        raise RuntimeError(f"Request failed: {e!s}")
    except ValueError:
        raise
    except Exception:
        raise RuntimeError("Error while parsing")
