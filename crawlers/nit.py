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
from selectolax.lexbor import LexborHTMLParser
from typing import Dict, List, Optional, Union

from crawlers._utils import resolve_labels

__crawler_meta__ = {
    "title": "OurOJ (NIT)",
    "description": "",
    "url": "https://www.nitacm.com/",
    "is_virtual_judge": True,
}


def _oj_map(oj: str) -> str:
    """
    Map OJ name from NIT to crawler name.

    Args:
        oj: OJ name from NIT

    Returns:
        Crawler name (lowercase)
    """
    simple_map_oj = {
        "codeforces",
        "hdu",
        "fzu",
        "nbut",
        "uva",
        "uvalive",
        "spoj",
        "aizu",
        "codechef",
        "nit",
    }

    oj_mapping = {
        "": "NO_NAME",
        "PKU": "poj",
        "URAL": "timus",
    }

    oj_lower = oj.lower()
    if oj_lower in simple_map_oj:
        return oj_lower
    elif oj in oj_mapping:
        return oj_mapping[oj]
    else:
        return oj


async def _resolve_label(
    session: aiohttp.ClientSession, problem_id: int
) -> Optional[str]:
    """
    Resolve NIT problem ID to OJ-specific label.

    NIT is a virtual judge that hosts problems from multiple OJs.
    This function scrapes the problem page to determine the source OJ
    and the original problem ID.

    Args:
        session: aiohttp ClientSession
        problem_id: NIT internal problem ID

    Returns:
        Label in format "oj-problem_id" (e.g., "hdu-2181", "nit-100"),
        or None if resolution failed
    """
    try:
        async with session.get(
            "https://www.nitacm.com/problem_show.php",
            params={"pid": problem_id},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status != 200:
                return None
            html = await response.text()

        doc = LexborHTMLParser(html)
        oj_dom = doc.css_first("span.badge.badge-info")
        if oj_dom is None:
            return f"nit-{problem_id}"

        oj = _oj_map(oj_dom.text(strip=True))

        next_elem = oj_dom.next
        while next_elem:
            if next_elem.tag == "a":
                label = next_elem.text(strip=True)
                if label:
                    return f"{oj}-{label}"
            next_elem = next_elem.next

        return None
    except Exception:
        return None


def _extract_number_from_cell(cell) -> int:
    """
    Extract a number from a table cell, handling nested <a> tags.

    Args:
        cell: A selectolax table cell element

    Returns:
        The extracted number, or 0 if not found
    """
    link = cell.css_first("a")
    if link:
        text = link.text(strip=True)
    else:
        text = cell.text(strip=True)

    if text.isdigit():
        return int(text)
    return 0


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query NIT (OurOJ) for user statistics.

    Args:
        username: NIT username

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
            "https://www.nitacm.com/userinfo.php",
            params={"name": username},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"Server Response Error: {response.status}")
            text = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    if "No such user!" in text:
        raise ValueError("The user does not exist")

    try:
        doc = LexborHTMLParser(text)

        submissions = 0
        solved = 0

        for row in doc.css("tr"):
            th = row.css_first("th")
            if th is None:
                continue
            header = th.text(strip=True)
            if header not in ("Total Submissions", "Accepted"):
                continue
            td = row.css_first("td")
            if td is None:
                continue
            if header == "Total Submissions":
                submissions = _extract_number_from_cell(td)
            else:
                solved = _extract_number_from_cell(td)

        ac_list = [
            int(a.text(strip=True))
            for a in doc.css("#userac a")
            if a.text(strip=True).isdigit()
        ]

        label_mappings = await resolve_labels(
            session, "nit", ac_list, _resolve_label, rate_limit_delay=0.05
        )

        solved_list = []
        for pid in ac_list:
            label = label_mappings.get(pid)
            if label:
                solved_list.append(label)
            else:
                solved_list.append(f"nit-{pid}")

        return {
            "solved": solved,
            "submissions": submissions,
            "solved_list": solved_list,
        }

    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError("Error while parsing")
