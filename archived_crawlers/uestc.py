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
import json
import aiohttp
from typing import Dict, List, Union

__crawler_meta__ = {
    "title": "CDOJ (Lutece)",
    "description": "UESTC Online Judge (migrated to Hydro)",
    "url": "https://cdoj.site/",
    "test_username": "HeRaNO",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query CDOJ (formerly Lutece) for user statistics.

    The platform has migrated from Lutece to Hydro. User statistics are now
    retrieved from the Hydro platform at hydro.ac.

    Args:
        username: CDOJ/Hydro username

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
            "https://hydro.ac/api/user",
            params={"uname": username},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"Server Response Error: {response.status}")

            user_data = await response.json()

            if not user_data or "error" in user_data:
                raise ValueError("The user does not exist")

            user_id = user_data.get("_id")
            if not user_id:
                raise ValueError("The user does not exist")

        async with session.get(
            f"https://hydro.ac/user/{user_id}", timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"Server Response Error: {response.status}")

            html = await response.text()

        match = re.search(r"UiContextNew\s*=\s*\'({.+?})\';", html, re.DOTALL)
        if not match:
            raise RuntimeError("Error while parsing user data")

        context_data = json.loads(match.group(1))
        udoc = context_data.get("udoc", {})

        n_accept = udoc.get("nAccept", 0)
        n_submit = udoc.get("nSubmit", 0)

        return {
            "solved": n_accept,
            "submissions": n_submit,
            "solved_list": [],
        }

    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")
    except json.JSONDecodeError:
        raise RuntimeError("Error while parsing")
    except ValueError:
        raise
    except Exception:
        raise RuntimeError("Error while parsing")
