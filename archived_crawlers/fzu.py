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
    "title": "FZU",
    "description": "",
    "url": "http://acm.fzu.edu.cn/index.php",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query FZU for user statistics.

    Args:
        username: FZU username

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty, contains spaces, or user doesn't exist
        RuntimeError: If API returns an error
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    if re.search(r"\s", username):
        raise ValueError("The crawler does not support username with spaces")

    try:
        async with session.get(
            "http://acm.fzu.edu.cn/user.php",
            params={"uname": username},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"Server Response Error: {response.status}")
            text = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    try:
        doc = LexborHTMLParser(text)

        # Check if user exists - look for <font>No such user or user has been deleted!</font>
        if doc.css_first(
            'font:lexbor-contains("No such user or user has been deleted!")'
        ):
            raise ValueError("The user does not exist")

        # Extract AC list - <b><a href="problem.php?pid=...">PROBLEM_ID</a></b>
        ac_list = [
            a.text(strip=True) for a in doc.css('b > a[href^="problem.php?pid="]')
        ]

        # Extract submissions - "Total Submitted" followed by <td>NUMBER</td>
        submissions = int(
            doc.css_first('td:lexbor-contains("Total Submitted") + td').text(strip=True)
        )

        # Extract solved - "Total Accepted" followed by <td>NUMBER</td>
        solved = int(
            doc.css_first('td:lexbor-contains("Total Accepted") + td').text(strip=True)
        )

        return {
            "solved": solved,
            "submissions": submissions,
            "solved_list": ac_list,
        }

    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError("Error while parsing")
