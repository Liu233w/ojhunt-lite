# ARCHIVED: Cloudflare WAF blocks all non-browser automated requests.
# HackerEarth uses Cloudflare CDN with WAF protection. The public API at
# https://www.hackerearth.com/api/v2/users/?login={username} returns a
# Cloudflare challenge page (403 or JS challenge) instead of user data when
# accessed via aiohttp. The profile page at https://www.hackerearth.com/@{username}/
# is a React SPA and loads user stats via API calls that are similarly blocked.
# This crawler cannot be implemented with aiohttp-based scraping.

import aiohttp
from typing import Dict, List, Union

__crawler_meta__ = {
    "title": "HackerEarth",
    "description": "",
    "url": "https://www.hackerearth.com/",
    "test_username": "akash",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    if not username or not username.strip():
        raise ValueError("Please enter username")

    username = username.strip()

    try:
        async with session.get(
            f"https://www.hackerearth.com/api/v2/users/?login={username}",
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.hackerearth.com/",
            },
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 403:
                raise RuntimeError(
                    "HackerEarth returned 403 Forbidden (Cloudflare WAF block)"
                )
            if response.status == 404:
                raise ValueError("The user does not exist")
            if response.headers.get("cf-mitigated") == "challenge":
                raise RuntimeError(
                    "HackerEarth returned a Cloudflare challenge — not accessible via aiohttp"
                )
            response.raise_for_status()
            data = await response.json()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    users = data if isinstance(data, list) else data.get("results", [])
    if not users:
        raise ValueError("The user does not exist")

    user = users[0]
    solved = user.get("practice", {}).get("total_problems_solved", 0)
    submissions = user.get("practice", {}).get("total_submissions", solved)

    return {
        "solved": solved,
        "submissions": submissions,
        "solved_list": None,  # HackerEarth API does not expose problem list
    }
