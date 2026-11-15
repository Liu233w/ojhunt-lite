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
    "title": "ACMU.ru",
    "description": (
        "Please use your numeric user ID (the id= value in your profile URL, "
        "?main=user&id=...)"
    ),
    "url": "https://acmu.ru/",
    "test_username": "88854",
}

BASE_URL = "https://acmu.ru"
ENCODING = "cp1251"


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str] | None]:
    """
    Query ACMU.ru for user statistics.

    Args:
        session: aiohttp ClientSession
        username: Numeric ACMU user ID, visible in the profile URL
            (?main=user&id=...) — a display name is rejected

    Returns:
        Dictionary with keys: solved, submissions, solved_list. The counts cover
        all languages; submissions is the sum of the profile's result table.

    Raises:
        ValueError: If username is empty, not numeric, or the user does not exist
        RuntimeError: If the request fails or the page cannot be parsed
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    user_id = username.strip()

    if not user_id.isdigit():
        raise ValueError("ACMU.ru requires a numeric user ID (not a username)")

    try:
        async with session.get(
            f"{BASE_URL}/",
            params={"main": "user", "id": user_id},
            allow_redirects=False,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status in (301, 302, 303, 307, 308):
                raise ValueError("The user does not exist")
            response.raise_for_status()
            html = (await response.read()).decode(ENCODING, errors="replace")
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")

    doc = LexborHTMLParser(html)

    # The page repeats the block for the "Courses" section; the first one covers
    # all languages and is the one that matches the rating.
    heading = next(
        (
            node
            for node in doc.css("b.btext")
            if re.match(r"Решенные задачи \((\d+)\)", node.text(strip=True))
        ),
        None,
    )
    if heading is None:
        raise RuntimeError("Solved tasks block not found")
    solved = int(re.search(r"\((\d+)\)", heading.text()).group(1))

    task_list = heading.next
    while task_list is not None and task_list.tag != "p":
        task_list = task_list.next
    if task_list is None:
        raise RuntimeError("Solved tasks list not found")
    solved_list = [a.text(strip=True) for a in task_list.css("a")]

    submissions = 0
    for table in doc.css("table.main"):
        if table.css_first('th:lexbor-contains("Всего")') is None:
            continue
        submissions = sum(
            int(cell.text(strip=True)) for cell in table.css("td[align=right]")
        )
        break
    else:
        raise RuntimeError("Results table not found")

    return {
        "solved": solved,
        "submissions": max(submissions, solved),
        "solved_list": solved_list,
    }
