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
    "title": "NBUT",
    "description": "",
    "url": "https://ac.2333.moe/",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query NBUT for user statistics.

    Args:
        username: NBUT username

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty, contains spaces, or user doesn't exist
        RuntimeError: If API returns an error
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    if re.search(r"\s", username):
        raise ValueError("The crawler does not support username with spaces")

    username = username.strip()

    try:
        # First, get submissions page to extract user ID
        async with session.get(
            "https://ac.2333.moe/Problem/status.xhtml",
            params={"username": username},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"Server Response Error: {response.status}")
            submission_text = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    doc_submission = LexborHTMLParser(submission_text)
    # Check if user exists - look for <a href="/User/view_user.xhtml?id=...">
    user_link = doc_submission.css_first('a[href^="/User/view_user.xhtml?id="]')
    if not user_link:
        raise ValueError("The user does not exist")

    href = user_link.attributes["href"]
    match = re.search(r"id=(\d+)", href)
    if not match:
        raise ValueError("The user does not exist")
    user_id = match.group(1)

    try:
        # Now get user profile page
        async with session.get(
            "https://ac.2333.moe/User/view_user.xhtml",
            params={"id": user_id},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"Server Response Error: {response.status}")
            profile_text = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    try:
        doc_profile = LexborHTMLParser(profile_text)

        # Extract submissions and solved from <li id="limit">SUBMISSIONS / SOLVED</li>
        limit_text = doc_profile.css_first("li#limit").text(strip=True)
        numbers = re.findall(r"(\d+)", limit_text)
        submissions = int(numbers[0])
        solved = int(numbers[1])

        # Extract solved list - <li id="solvedlist">...<a href="/Problem/view.xhtml?id=...">PROBLEM_ID</a>...
        solved_list = [
            a.text(strip=True)
            for a in doc_profile.css('li#solvedlist a[href^="/Problem/view.xhtml?id="]')
        ]

        return {
            "solved": solved,
            "submissions": submissions,
            "solved_list": solved_list,
        }

    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError("Error while parsing")
