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
    "description": "Enter your numeric user ID.",
    "cli_description": "Login required. Use username:password@cses to query yourself, or -l login:pass@cses -- id@cses to query another user by numeric ID.",
    "url": "https://cses.fi/",
    "login_type": "shared_account",
    "test_username": "3",
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


async def _get_login_user_id(session: aiohttp.ClientSession) -> Optional[str]:
    async with session.get(
        f"{BASE_URL}/",
        timeout=aiohttp.ClientTimeout(total=30),
    ) as response:
        text = await response.text()

    account_link = LexborHTMLParser(text).css_first("a.account")
    if not account_link:
        return None

    href = account_link.attributes.get("href", "")
    match = re.search(r"/user/(\d+)", href)
    return match.group(1) if match else None


async def query(
    session: aiohttp.ClientSession,
    username: str,
    password: Optional[str] = None,
    login_user: Optional[str] = None,
    login_password: Optional[str] = None,
) -> Dict[str, Union[int, List[str], None]]:
    """
    Query CSES for user statistics.

    CSES has no public profiles, so a login is always required. Any authenticated
    account can look up any user: pass shared-account credentials as login_user /
    login_password and the target's numeric ID as username. Passing password
    instead logs in as `username` itself, in which case a login name is accepted.

    Args:
        session: aiohttp ClientSession
        username: Target user's numeric CSES ID (visible in the profile URL), or
            your own login name when authenticating with password
        password: Password for `username`, to query your own account
        login_user: Account to authenticate as; takes precedence over password
        login_password: Password for login_user

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty, no credentials were given, another user
            was requested by name instead of numeric ID, the user does not exist,
            or the session kept expiring before the profile could be read
        RuntimeError: If the credentials are rejected or a request fails

    Example:
        from ojhunt.crawlers import query_sync
        from ojhunt.crawlers.cses import query
        result = query_sync(query, "3", login_user="me", login_password="secret")
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    if login_user and login_password:
        cred_user, cred_pass = login_user, login_password
    elif password:
        cred_user, cred_pass = username, password
    else:
        raise ValueError("CSES requires login credentials.")

    user_id: Optional[str] = None
    if username != cred_user:
        if username.isdigit():
            user_id = username
        else:
            raise ValueError("CSES requires a numeric user ID to query other users")

    MAX_LOGIN_RETRIES = 2
    user_text: Optional[str] = None
    problemset_text: Optional[str] = None

    for attempt in range(MAX_LOGIN_RETRIES + 1):
        if attempt > 0:
            await _login(session, cred_user, cred_pass)

        current_user_id = user_id
        if current_user_id is None:
            current_user_id = await _get_login_user_id(session)
            not_logged_in = current_user_id is None
            if not_logged_in:
                continue

        try:
            async with session.get(
                f"{BASE_URL}/user/{current_user_id}",
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status in (404, 500):
                    raise ValueError("The user does not exist")
                response.raise_for_status()
                user_text = await response.text()

            async with session.get(
                f"{BASE_URL}/problemset/user/{current_user_id}/",
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status in (404, 500):
                    raise ValueError("The user does not exist")
                response.raise_for_status()
                problemset_text = await response.text()
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Request failed: {str(e)}")

        session_expired = LexborHTMLParser(problemset_text).css_first(
            '.content:lexbor-contains("Please login")'
        )
        if session_expired:
            continue

        break  # success
    else:
        raise ValueError("CSES login failed after multiple attempts")

    user_doc = LexborHTMLParser(user_text)
    sub_cell = user_doc.css_first('td:lexbor-contains("Submission count") + td')
    submissions = int(sub_cell.text(strip=True)) if sub_cell else 0

    problemset_doc = LexborHTMLParser(problemset_text)
    solved_paragraph = problemset_doc.css_first(".content p")
    if not solved_paragraph:
        raise ValueError("The user does not exist")

    match = re.search(r"Solved tasks:\s*(\d+)/\d+", solved_paragraph.text())
    if not match:
        raise ValueError("The user does not exist")

    solved = int(match.group(1))

    solved_list = []
    for link in problemset_doc.css("a.task-score.full"):
        href = link.attributes.get("href", "")
        task_match = re.search(r"/problemset/task/(\d+)/", href)
        if task_match:
            solved_list.append(task_match.group(1))

    return {
        "solved": solved,
        "submissions": submissions,
        "solved_list": solved_list,
    }
