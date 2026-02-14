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
import re
from selectolax.lexbor import LexborHTMLParser
from typing import Dict, List, Union

__crawler_meta__ = {
    "title": "UOJ",
    "description": "",
    "url": "http://uoj.ac/",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query UOJ for user statistics.

    Args:
        username: UOJ username

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
        # Get user profile
        async with session.get(
            f"https://uoj.ac/user/profile/{username}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 404:
                raise ValueError("The user does not exist")
            if response.status != 200:
                raise RuntimeError(f"Server Response Error: {response.status}")
            profile_text = await response.text()
    except aiohttp.ClientError as e:
        if "404" in str(e):
            raise ValueError("The user does not exist")
        raise RuntimeError(f"Request failed: {str(e)}")

    # Check for user not found: <div class="panel panel-danger"> containing "不存在该用户"
    doc_profile = LexborHTMLParser(profile_text)
    for panel in doc_profile.css("div.panel"):
        classes = panel.attributes.get("class") or ""
        if "panel-danger" in classes:
            if "不存在该用户" in panel.text():
                raise ValueError("The user does not exist")

    try:
        # Extract solved count - "AC 过的题目：共 217 道题"
        solved = 0
        for h4 in doc_profile.css("h4"):
            text = h4.text(strip=True)
            if "AC 过的题目" in text:
                solved_match = re.search(r"(\d+)", text)
                if solved_match:
                    solved = int(solved_match.group(1))
                break

        # Extract solved list - <a href="https://uoj.ac/problem/30">#30. 【CF Round #278】Tourists</a>
        # Extract just the problem ID from "#30. Title" format
        solved_list = []
        for a in doc_profile.css('a[href^="https://uoj.ac/problem/"]'):
            text = a.text(strip=True)
            match = re.match(r"#(\d+)", text)
            if match:
                solved_list.append(match.group(1))

        # Note: Submissions page now requires login, so we cannot get exact submission count
        # We estimate submissions based on solved count (at minimum, solved count)
        submissions = solved

        return {
            "solved": solved,
            "submissions": submissions,
            "solved_list": solved_list,
        }

    except ValueError:
        raise
    except Exception:
        raise RuntimeError("Error while parsing")
