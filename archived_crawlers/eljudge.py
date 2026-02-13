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
    "title": "El Judge",
    "description": "",
    "url": "http://acm.mipt.ru",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query El Judge for user statistics.

    Args:
        username: El Judge username

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
            "http://acm.mipt.ru/judge/users.pl",
            params={"user": username},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"Server Response Error: {response.status}")
            text = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    # Check if user exists
    if re.search(r"User .+ does not exist", text):
        raise ValueError("The user does not exist")

    try:
        doc = LexborHTMLParser(text)

        # Extract solved count - <font...>solved:</font> followed by <b>NUMBER</b>
        solved = int(
            doc.css_first('font:lexbor-contains("solved:") + b').text(strip=True)
        )

        # Extract solved list - problems after "solved:" in <a> tags
        # We can find all <a> tags that are siblings of the "solved:" font tag, before the next font tag.
        # selectolax doesn't have a direct "next_siblings_until" but we can iterate.
        solved_list = []
        solved_font = doc.css_first('font:lexbor-contains("solved:")')
        if solved_font:
            curr = solved_font.next
            while curr:
                if curr.tag == "font":
                    break
                if curr.tag == "a":
                    txt = curr.text(strip=True)
                    if txt:
                        solved_list.append(txt)
                curr = curr.next

        # Extract submissions from Statistics table
        # Find <font>Statistics:</font> followed by <table> with <div> entries
        submissions = 0
        stats_font = doc.css_first('font:lexbor-contains("Statistics:")')
        if stats_font:
            table = stats_font.css_first(" + table")
            if table:
                for div in table.css("div"):
                    txt = div.text(strip=True)
                    if txt.isdigit():
                        submissions += int(txt)

        return {
            "solved": solved,
            "submissions": submissions,
            "solved_list": solved_list,
        }

    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError("Error while parsing")
