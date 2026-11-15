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
from selectolax.lexbor import LexborHTMLParser, LexborNode

__crawler_meta__ = {
    "title": "HUST",
    "description": "HUST Online Judge",
    "url": "https://hustoj.org/",
    "test_username": "freefcw",
}


def _segment_after(doc: LexborHTMLParser, heading: str) -> LexborNode | None:
    """Return the segment ``<div>`` that follows the ``<h4>`` titled ``heading``."""
    for h4 in doc.css("h4"):
        if h4.text(strip=True) != heading:
            continue
        node = h4.next
        while node is not None and node.tag != "div":
            node = node.next
        return node
    return None


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str] | None]:
    """
    Query HUST Online Judge for user statistics.

    Args:
        username: HUST username

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
            "https://hustoj.org/userinfo.php",
            params={"user": username},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            html = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")

    if "No such User!" in html:
        raise ValueError("The user does not exist")

    try:
        doc = LexborHTMLParser(html)

        solved = None
        for tr in doc.css("#user_card tr"):
            th = tr.css_first("th")
            if th is not None and th.text(strip=True) == "通过":
                solved = int(tr.css_first("td").text(strip=True))
                break
        if solved is None:
            raise RuntimeError("Error while parsing")

        solved_segment = _segment_after(doc, "通过的题目")
        if solved_segment is None:
            raise RuntimeError("Error while parsing")
        solved_list = [
            a.text(strip=True) for a in solved_segment.css('a[href^="problem.php?id="]')
        ]

        # The result-distribution table has one row per verdict that occurred;
        # their counts add up to the total number of submissions.
        submissions = 0
        verdict_segment = _segment_after(doc, "结果分布")
        if verdict_segment is not None:
            for tr in verdict_segment.css("tr"):
                cells = tr.css("td")
                if len(cells) == 2 and cells[1].text(strip=True).isdigit():
                    submissions += int(cells[1].text(strip=True))

        return {
            "solved": solved,
            "submissions": max(submissions, solved),
            "solved_list": solved_list,
        }
    except Exception:
        raise RuntimeError("Error while parsing")
