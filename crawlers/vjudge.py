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
from typing import Dict, List, Union, Optional

__crawler_meta__ = {
    "title": "VJudge",
    "description": "virtual judge，这个OJ的题量是单独计算的",
    "url": "https://vjudge.net/",
    "is_aggregator": True,
    "login_type": "shared_account",
    "test_username": "leoloveacm",
}

HOSTNAME = "vjudge.net"
MAX_PAGE_SIZE = 500


class _AuthRequired(Exception):
    pass


def _map_oj_name(name_in_vjudge: str) -> str:
    """
    Map OJ name in VJudge to crawler name.

    Args:
        name_in_vjudge: OJ name in VJudge

    Returns:
        Crawler name
    """
    # OJs that can map to crawler name by changing to lowercase
    simple_map_oj = {
        "codeforces",
        "uva",
        "uvalive",
        "poj",
        "hdu",
        "zoj",
        "fzu",
        "spoj",
        "timus",
        "csu",
        "atcoder",
        "aizu",
        "codechef",
        "nbut",
    }

    # Special mappings
    oj_map = {
        "": "NO_NAME",
        "LibreOJ": "loj",
        "URAL": "timus",
        "HYSBZ": "dashiye",
        "EIJudge": "eljudge",
        "Gym": "codeforces",
        "51Nod": "nod",
    }

    name_lower = name_in_vjudge.lower()
    if name_lower in simple_map_oj:
        return name_lower
    elif name_in_vjudge in oj_map:
        return oj_map[name_in_vjudge]
    else:
        return name_in_vjudge


async def _fetch_page(
    session: aiohttp.ClientSession, username: str, max_id: Optional[int]
) -> List:
    params: Dict[str, str] = {"username": username, "pageSize": str(MAX_PAGE_SIZE)}
    if max_id is not None:
        params["maxId"] = str(max_id)

    async with session.get(
        f"https://{HOSTNAME}/user/submissions",
        params=params,
        timeout=aiohttp.ClientTimeout(total=30),
    ) as response:
        if response.status != 200:
            raise RuntimeError(f"Server Response Error: {response.status}")
        data = await response.json()

    if data.get("error") and "login" in data.get("error", "").lower():
        raise _AuthRequired()
    if data.get("error") and "does not exist" in data.get("error", ""):
        raise ValueError("The user does not exist")
    if "data" not in data:
        raise RuntimeError(f"Cannot process vjudge data, body: {data}")

    return data.get("data", [])


async def _paginate(session: aiohttp.ClientSession, username: str) -> tuple:
    ac_set: set = set()
    total_submissions = 0
    max_id: Optional[int] = None
    while True:
        problem_array = await _fetch_page(session, username, max_id)
        if not problem_array:
            break
        for element in problem_array:
            crawler_name = _map_oj_name(element[2])
            if element[4] == "AC":
                ac_set.add(f"{crawler_name}-{element[3]}")
        total_submissions += len(problem_array)
        max_id = problem_array[-1][0] - 1
        if len(problem_array) < MAX_PAGE_SIZE:
            break
    return ac_set, total_submissions


async def _try_login(
    session: aiohttp.ClientSession, login_user: str, login_password: str
) -> None:
    try:
        async with session.post(
            f"https://{HOSTNAME}/user/login",
            data={
                "username": login_user,
                "password": login_password,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            },
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            text = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"vjudge login failed: {str(e)}")
    if text != "success":
        raise RuntimeError(f"vjudge login failed: {text}")


async def query(
    session: aiohttp.ClientSession,
    username: str,
    password: Optional[str] = None,
    login_user: Optional[str] = None,
    login_password: Optional[str] = None,
) -> Dict[str, Union[int, List[str]]]:
    """
    Query VJudge for user statistics.

    VJudge requires authentication. You can provide credentials in two ways:
    1. Embedded in query: user:pass@vjudge (login and query same user)
    2. Via -l flag: -l login:pass@vjudge -- target@vjudge (login as one user, query another)

    Args:
        session: aiohttp ClientSession
        username: VJudge username to query
        password: Password if using embedded credentials (login as target user)
        login_user: Login username if using -l flag (separate from target user)
        login_password: Login password if using -l flag

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty or credentials not provided
        RuntimeError: If API returns an error or login fails
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    # Determine login credentials
    if login_user and login_password:
        # Using -l flag: separate login from target user
        actual_login_user = login_user
        actual_login_password = login_password
    elif password:
        # Using embedded password: login as target user
        actual_login_user = username
        actual_login_password = password
    else:
        raise ValueError("VJudge requires login credentials.")

    MAX_LOGIN_RETRIES = 2
    for attempt in range(MAX_LOGIN_RETRIES + 1):
        if attempt > 0:
            await _try_login(session, actual_login_user, actual_login_password)
        try:
            ac_set, total_submissions = await _paginate(session, username)
        except _AuthRequired:
            continue
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Request failed: {str(e)}")
        except ValueError:
            raise
        except Exception:
            raise RuntimeError("Error while parsing")
        break
    else:
        raise ValueError("VJudge login failed after multiple attempts")

    return {
        "solved": len(ac_set),
        "submissions": total_submissions,
        "solved_list": sorted(list(ac_set)),
    }
