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
from selectolax.lexbor import LexborHTMLParser

__crawler_meta__ = {
    "title": "HDU",
    "description": "",
    "url": "http://acm.hdu.edu.cn/",
    "test_username": "vjudge4",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str]]:
    """
    Query Hangzhou Dianzi University OJ for user statistics.

    Args:
        username: HDU username

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty or user doesn't exist
        RuntimeError: If request fails or parsing fails
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    # HDU can be unreliable, try with retry
    max_retries = 2
    html = None

    for attempt in range(max_retries):
        try:
            async with session.get(
                "http://acm.hdu.edu.cn/userstatus.php",
                params={"user": username},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                html = await response.text()
                break
        except aiohttp.ClientError as e:
            if attempt >= max_retries - 1:
                raise RuntimeError(
                    f"Request failed after {max_retries} attempts: {e!s}"
                )
            print(f"HDU connection error, retry {attempt + 1}/{max_retries}...")

    # Check if user exists
    if "No such user." in html:
        raise ValueError("The user does not exist")

    try:
        doc = LexborHTMLParser(html)

        # Extract submissions: <td>Submissions</td><td>123</td>
        submissions = int(
            doc.css_first('td:lexbor-contains("Submissions") + td').text(strip=True)
        )

        # Extract solved: <td>Problems Solved</td><td>456</td>
        solved = int(
            doc.css_first('td:lexbor-contains("Problems Solved") + td').text(strip=True)
        )

        # Extract solved list from JavaScript
        # Format: p(1000,3588,11274);p(1001,1951,7721);...
        solved_list = []
        for script in doc.css("script"):
            text = script.text()
            if text and "p(" in text:
                solved_list = re.findall(r"p\((\d+)", text)
                if solved_list:
                    break

        return {
            "solved": solved,
            "submissions": submissions,
            "solved_list": solved_list,
        }
    except Exception:
        raise RuntimeError("Error while parsing")
