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
    "title": "Code360",
    "description": (
        "Enter your Code360 profile name (the last part of "
        "naukri.com/code360/profile/<name>). Counts DSA problems only."
    ),
    "url": "https://www.naukri.com/code360/",
    "test_username": "theabbie",
}

API_URL = "https://www.naukri.com/code360/api/v3/public_section/profile/user_details"

# The site's firewall resets connections whose User-Agent contains a URL or a
# tool name, which the default session User-Agent does.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str] | None]:
    """
    Query Code360 for user statistics.

    The profile API publishes only the number of solved DSA problems, so
    submissions equals solved and solved_list is None.

    Args:
        session: aiohttp ClientSession
        username: Code360 profile name

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty or user doesn't exist
        RuntimeError: If request fails or parsing fails
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    try:
        async with session.get(
            API_URL,
            params={"uuid": username, "request_differentiator": "1"},
            headers=_HEADERS,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 404:
                raise ValueError("The user does not exist")
            response.raise_for_status()
            payload = await response.json(content_type=None)
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")

    try:
        solved = int(
            payload["data"]["dsa_domain_data"]["problem_count_data"]["total_count"]
        )
    except (KeyError, TypeError, ValueError) as e:
        raise RuntimeError(f"Unexpected response format: {e!r}")

    return {
        "solved": solved,
        # Code360 publishes no submission total; report the solved count,
        # which every accepted problem cost at least (ADR 0015).
        "submissions": solved,
        "solved_list": None,
    }
