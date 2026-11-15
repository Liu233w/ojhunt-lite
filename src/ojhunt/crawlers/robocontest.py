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
from urllib.parse import quote

import aiohttp
from selectolax.lexbor import LexborHTMLParser

__crawler_meta__ = {
    "title": "RoboContest",
    "description": (
        "Please use your RoboContest username (the name in your profile URL, "
        "robocontest.uz/profile/...)"
    ),
    "url": "https://robocontest.uz/",
    "test_username": "the_samurai",
}

BASE_URL = "https://robocontest.uz"


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str] | None]:
    """
    Query RoboContest for user statistics.

    Args:
        session: aiohttp ClientSession
        username: RoboContest username, as in the profile URL

    Returns:
        Dictionary with keys: solved, submissions, solved_list. submissions is
        the sum of the profile's per-language attempts. solved_list holds the
        task numbers the profile marks as solved; it can be shorter than solved
        because the profile's task map omits some tasks.

    Raises:
        ValueError: If username is empty or the user does not exist
        RuntimeError: If the request fails or the page cannot be parsed
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    name = username.strip()

    try:
        async with session.get(
            f"{BASE_URL}/profile/{quote(name, safe='')}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 404:
                raise ValueError("The user does not exist")
            response.raise_for_status()
            html = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")

    node = LexborHTMLParser(html).css_first('script[data-page="robo-app"]')
    if node is None:
        raise RuntimeError("Profile data not found")
    try:
        props = json.loads(node.text())["props"]
        solved = int(props["stats"]["solvedTasks"])
        submissions = sum(int(lang["attempts"]) for lang in props["languages"])
        solved_map = props.get("solvedMap")
        solved_list = (
            [str(task["number"]) for task in solved_map if task["solved"]]
            if solved_map
            else None
        )
    except (ValueError, KeyError, TypeError) as e:
        raise RuntimeError(f"Error while parsing: {e!s}")

    return {
        "solved": solved,
        "submissions": max(submissions, solved),
        "solved_list": solved_list,
    }
