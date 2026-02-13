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
    "title": "HYSBZ",
    "description": "",
    "url": "http://www.lydsy.com/JudgeOnline/",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query HYSBZ for user statistics.

    Args:
        username: HYSBZ username

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
            "http://www.lydsy.com/JudgeOnline/userinfo.php",
            params={"user": username},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"Server Response Error: {response.status}")
            text = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    if text.strip().endswith("No such User!"):
        raise ValueError("The user does not exist")

    try:
        doc = LexborHTMLParser(text)

        # Extract solved count - look for "Solved" followed by <td><a>NUMBER</a></td>
        solved = int(
            doc.css_first('td:lexbor-contains("Solved") + td a').text(strip=True)
        )

        # Extract submissions count - look for "Submit" followed by <td><a>NUMBER</a></td>
        submissions = int(
            doc.css_first('td:lexbor-contains("Submit") + td a').text(strip=True)
        )

        # Extract AC list from script - pattern: p(1000);p(1001);p(1002)...
        # The script is in <td rowspan=14><script>...p(1000);p(1001);...</script></td>
        script_node = doc.css_first('td[rowspan="14"] script')
        ac_list = []
        if script_node:
            ac_list = re.findall(r"p\((\d+)\)", script_node.text())

        return {
            "solved": solved,
            "submissions": submissions,
            "solved_list": ac_list,
        }
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError("Error while parsing")
