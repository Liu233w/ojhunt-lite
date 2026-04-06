# ARCHIVED: Topcoder Algorithm Arena shut down July 2024. The v5 members API
# (api.topcoder.com/v5/members) returns 503 Service Unavailable consistently.
# Keeping this for reference in case the API is restored.

import aiohttp
from typing import Dict, List, Union

__crawler_meta__ = {
    "title": "Topcoder",
    "description": "",
    "url": "https://www.topcoder.com/",
    "test_username": "petr",
}

BASE_URL = "https://api.topcoder.com/v5"


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    try:
        async with session.get(
            f"{BASE_URL}/members/{username}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 404:
                raise ValueError("The user does not exist")
            response.raise_for_status()
            data = await response.json()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    try:
        # wins = challenge wins; no submissions count in member profile, use wins as proxy
        solved = int(data.get("wins", 0) or 0)

        return {
            "solved": solved,
            "submissions": solved,
            "solved_list": [],
        }
    except Exception as e:
        raise RuntimeError(f"Error while parsing: {str(e)}")
