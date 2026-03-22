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
from typing import Dict, List, Union, Optional

__crawler_meta__ = {
    "title": "CSES",
    "description": "Enter your CSES username or numeric user ID (login required).",
    "url": "https://cses.fi/",
    "requires_login": True,
    "test_username": "ojhuntlite",
}

BASE_URL = "https://cses.fi"


async def _login(
    session: aiohttp.ClientSession, login_user: str, login_password: str
) -> None:
    try:
        async with session.get(
            f"{BASE_URL}/login/",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            text = await response.text()
        csrf_input = LexborHTMLParser(text).css_first("input[name=csrf_token]")
        csrf_token = csrf_input.attributes.get("value", "") if csrf_input else ""

        async with session.post(
            f"{BASE_URL}/login/",
            data={"nick": login_user, "pass": login_password, "csrf_token": csrf_token},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=aiohttp.ClientTimeout(total=30),
            allow_redirects=True,
        ) as response:
            text = await response.text()
            if (
                str(response.url).endswith("/login/")
                or "Wrong CSRF token" in text
                or "Invalid password" in text
                or "No such user" in text
            ):
                raise RuntimeError("CSES login failed: invalid credentials")
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Login request failed: {str(e)}")


async def _get_user_id(session: aiohttp.ClientSession) -> str:
    async with session.get(
        f"{BASE_URL}/",
        timeout=aiohttp.ClientTimeout(total=30),
    ) as response:
        text = await response.text()

    account_link = LexborHTMLParser(text).css_first("a.account")
    if not account_link:
        raise RuntimeError("Failed to extract user ID after login")

    href = account_link.attributes.get("href", "")
    match = re.search(r"/user/(\d+)", href)
    if not match:
        raise RuntimeError(f"Unexpected account link format: {href}")

    return match.group(1)


async def query(
    session: aiohttp.ClientSession,
    username: str,
    password: Optional[str] = None,
    login_user: Optional[str] = None,
    login_password: Optional[str] = None,
) -> Dict[str, Union[int, List[str], None]]:
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    if login_user and login_password:
        cred_user, cred_pass = login_user, login_password
    elif password:
        cred_user, cred_pass = username, password
    else:
        raise ValueError("CSES requires login credentials.")

    await _login(session, cred_user, cred_pass)

    # Resolve username to numeric ID
    if username.isdigit():
        user_id = username
    elif cred_user == username:
        # Type A: querying self — extract own ID from the logged-in session
        user_id = await _get_user_id(session)
    else:
        raise ValueError("CSES requires a numeric user ID to query users other than yourself")

    try:
        async with session.get(
            f"{BASE_URL}/problemset/user/{user_id}/",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status in (404, 500):
                raise ValueError("The user does not exist")
            response.raise_for_status()
            text = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    doc = LexborHTMLParser(text)

    # Check for login wall (in case session expired)
    content = doc.css_first(".content")
    if content and "Please login" in content.text():
        raise RuntimeError("Session expired; login failed")

    # Parse "Solved tasks: X/400"
    solved_paragraph = doc.css_first(".content p")
    if not solved_paragraph:
        raise ValueError("The user does not exist")

    match = re.search(r"Solved tasks:\s*(\d+)/\d+", solved_paragraph.text())
    if not match:
        raise ValueError("The user does not exist")

    solved = int(match.group(1))

    # Extract solved problem IDs from links with class "task-score full"
    solved_list = []
    for link in doc.css("a.task-score.full"):
        href = link.attributes.get("href", "")
        task_match = re.search(r"/problemset/task/(\d+)/", href)
        if task_match:
            solved_list.append(task_match.group(1))

    return {
        "solved": solved,
        "submissions": 0,  # CSES does not expose total submission count publicly
        "solved_list": solved_list,
    }
