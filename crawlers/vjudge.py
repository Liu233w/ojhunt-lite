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
    "is_virtual_judge": True,
    "requires_login": True,
}

HOSTNAME = "vjudge.net"
MAX_PAGE_SIZE = 500


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


async def _try_login(
    session: aiohttp.ClientSession, login_user: str, login_password: str
) -> None:
    """
    Login to VJudge.

    Args:
        session: aiohttp ClientSession
        login_user: VJudge login username
        login_password: VJudge login password

    Raises:
        RuntimeError: If login fails
    """
    try:
        async with session.post(
            f"https://{HOSTNAME}/user/login",
            data={
                "username": login_user,
                "password": login_password,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
            },
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            text = await response.text()

            if text != "success":
                raise RuntimeError(f"vjudge login failed: {text}")

    except Exception as e:
        raise RuntimeError(f"vjudge login failed: {str(e)}")


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

    ac_set = set()
    submissions_by_crawler_name = {}
    total_submissions = 0

    await _try_login(session, actual_login_user, actual_login_password)

    max_id = None

    try:
        while True:
            params = {
                "username": username,
                "pageSize": str(MAX_PAGE_SIZE),
            }
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
                    await _try_login(session, actual_login_user, actual_login_password)
                    continue

                if data.get("error") and "does not exist" in data.get("error", ""):
                    raise ValueError("The user does not exist")

                if not data.get("data"):
                    raise RuntimeError(f"Cannot process vjudge data, body: {data}")

                problem_array = data.get("data", [])

                if not problem_array:
                    break

                for element in problem_array:
                    crawler_name = _map_oj_name(element[2])

                    if crawler_name not in submissions_by_crawler_name:
                        submissions_by_crawler_name[crawler_name] = 1
                    else:
                        submissions_by_crawler_name[crawler_name] += 1

                    if element[4] == "AC":
                        title = f"{crawler_name}-{element[3]}"
                        ac_set.add(title)

                total = len(problem_array)
                total_submissions += total

                max_id = problem_array[-1][0] - 1

                if total < MAX_PAGE_SIZE:
                    break

    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError("Error while parsing")

    return {
        "solved": len(ac_set),
        "submissions": total_submissions,
        "solved_list": sorted(list(ac_set)),
    }
