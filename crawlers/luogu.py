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
import json
import re
from typing import Dict, List, Union

__crawler_meta__ = {
    "title": "洛谷",
    "description": "Both username and user_id are supported",
    "url": "https://www.luogu.com.cn",
    "test_username": "811437",
}


async def _get_user_id(session: aiohttp.ClientSession, username: str) -> str:
    async with session.get(
        "https://www.luogu.com.cn/api/user/search",
        params={"keyword": username},
        timeout=aiohttp.ClientTimeout(total=30),
    ) as response:
        if response.status != 200:
            raise RuntimeError(f"Server Response Error: {response.status}")

        data = await response.json()

        if not data.get("users") or len(data["users"]) == 0:
            raise ValueError("The user does not exist")

        return str(data["users"][0]["uid"])


def _extract_lentille_context(html: str) -> dict:
    match = re.search(
        r'<script id="lentille-context" type="application/json">(.*?)</script>', html
    )
    if not match:
        raise RuntimeError("Could not find lentille-context")
    return json.loads(match.group(1))


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str], None]]:
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    try:
        async with session.get(
            f"https://www.luogu.com.cn/user/{username}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            text = await response.text()

        context = _extract_lentille_context(text)

        if context.get("status") == 404 or context.get("template") == "error":
            uid = await _get_user_id(session, username)
            async with session.get(
                f"https://www.luogu.com.cn/user/{uid}",
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                text = await response.text()
            context = _extract_lentille_context(text)

        if context.get("status") == 404 or context.get("template") == "error":
            raise ValueError("The user does not exist")

        user_data = context.get("data", {}).get("user", {})

        return {
            "solved": user_data.get("passedProblemCount", 0) or 0,
            "submissions": user_data.get("submittedProblemCount", 0) or 0,
            "solved_list": None,
        }

    except ValueError:
        raise
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")
    except Exception:
        raise RuntimeError("Error while parsing")
