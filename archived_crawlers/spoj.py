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
    "title": "SPOJ",
    "description": "",
    "url": "http://www.spoj.com/",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query SPOJ for user statistics.

    Args:
        username: SPOJ username

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
        async with session.get(
            f"https://www.spoj.com/users/{username}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            # Check for 404 Not Found
            if response.status == 404:
                raise ValueError("The user does not exist")

            if response.status != 200:
                raise RuntimeError(f"Server Response Error: {response.status}")

            text = await response.text()
    except aiohttp.ClientError as e:
        if "Not Found" in str(e):
            raise ValueError("The user does not exist")
        raise RuntimeError(f"Request failed: {str(e)}")

    try:
        doc = LexborHTMLParser(text)

        # Check if user profile exists - look for #user-profile-left element
        if doc.css_first("#user-profile-left") is None:
            raise ValueError("The user does not exist")

        # Extract submissions - "Solutions submitted" followed by <dd>NUMBER</dd>
        submissions = int(
            doc.css_first('dt:lexbor-contains("Solutions submitted") + dd').text(
                strip=True
            )
        )

        # Extract solved - "Problems solved" followed by <dd>NUMBER</dd>
        solved = int(
            doc.css_first('dt:lexbor-contains("Problems solved") + dd').text(strip=True)
        )

        # Extract solved list - look for <h4>List of solved classical problems</h4> followed by <table>...<a>...</a>...</table>
        solved_list = [
            link.text(strip=True)
            for link in doc.css(
                'h4:lexbor-contains("List of solved classical problems") + table a'
            )
            if link.text(strip=True)
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
