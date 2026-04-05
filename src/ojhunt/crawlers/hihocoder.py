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

import re
import aiohttp
from typing import Dict, List, Optional, Union

__crawler_meta__ = {
    "title": "HihoCoder",
    "description": "",
    "cli_description": "Enter numeric user ID (not username). Find your ID at hihocoder.com/user/<id>.",
    "url": "https://hihocoder.com/",
    "test_username": "2",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, Optional[List[str]]]]:
    """
    Query HihoCoder for user statistics by numeric user ID.

    Args:
        username: HihoCoder numeric user ID

    Returns:
        Dictionary with keys: solved, submissions, solved_list (always None)

    Raises:
        ValueError: If username is empty or user doesn't exist
        RuntimeError: If request fails or parsing fails
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    async with session.get(
        f"https://hihocoder.com/user/{username}",
        ssl=False,
        timeout=aiohttp.ClientTimeout(total=30),
        headers={"User-Agent": "Mozilla/5.0"},
    ) as response:
        html = await response.text()

    if "Missing or Invalid User Id" in html:
        raise ValueError("The user does not exist")

    solved_match = re.search(r"通过题目数：(\d+)", html)
    submissions_match = re.search(r"总提交数：(\d+)", html)

    if not solved_match and not submissions_match:
        raise RuntimeError("Error while parsing")

    solved = int(solved_match.group(1)) if solved_match else 0
    submissions = int(submissions_match.group(1)) if submissions_match else 0

    return {
        "solved": solved,
        "submissions": submissions,
        "solved_list": None,
    }
