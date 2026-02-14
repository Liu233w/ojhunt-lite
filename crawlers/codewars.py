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
    "title": "Codewars",
    "description": "Currently it does not have submission number.\nUsername is case sensitive.",
    "url": "https://www.codewars.com",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query Codewars for user statistics.

    Args:
        username: Codewars username (case sensitive)

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
    current_page = 0

    try:
        # First request to get total pages
        try:
            async with session.get(
                f"https://www.codewars.com/api/v1/users/{username}/code-challenges/completed",
                params={"page": "0"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 404:
                    raise ValueError("The user does not exist")
                if response.status != 200:
                    raise RuntimeError(f"Server Response Error: {response.status}")

                data = await response.json()
                total_pages = data.get("totalPages", 1)

                # Process first page
                for item in data.get("data", []):
                    ac_set.add(item.get("slug"))

                current_page = 1

        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                raise ValueError("The user does not exist")
            raise

        # Fetch remaining pages
        while current_page < total_pages:
            async with session.get(
                f"https://www.codewars.com/api/v1/users/{username}/code-challenges/completed",
                params={"page": str(current_page)},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                data = await response.json()

                for item in data.get("data", []):
                    ac_set.add(item.get("slug"))

                current_page += 1

        # Codewars doesn't track submission count separately, use solved count
        return {
            "solved": len(ac_set),
            "submissions": len(ac_set),
            "solved_list": list(ac_set),
        }

    except aiohttp.ClientError as e:
        if "404" in str(e):
            raise ValueError("The user does not exist")
        raise RuntimeError(f"Request failed: {str(e)}")
    except ValueError:
        raise
    except Exception:
        raise RuntimeError("Error while parsing")
