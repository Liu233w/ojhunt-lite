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
import re
from selectolax.lexbor import LexborHTMLParser
from typing import Dict, List, Union
import json

__crawler_meta__ = {
    "title": "DMOJ",
    "description": "",
    "url": "https://dmoj.ca/",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query DMOJ for user statistics.

    Args:
        username: DMOJ username

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
        # Get submissions page to extract total submissions count
        async with session.get(
            f"https://dmoj.ca/submissions/user/{username}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 404:
                raise ValueError("The user does not exist")
            if response.status != 200:
                raise RuntimeError(f"Server Response Error: {response.status}")
            text = await response.text()
    except aiohttp.ClientError as e:
        if "404" in str(e):
            raise ValueError("The user does not exist")
        raise RuntimeError(f"Request failed: {str(e)}")

    try:
        doc = LexborHTMLParser(text)

        # Extract submissions count from window.results_json in script tag
        submissions = 0
        for script in doc.css("script"):
            script_text = script.text()
            if script_text and "window.results_json" in script_text:
                json_match = re.search(r"\{.*\}", script_text)
                if json_match:
                    try:
                        json_data = json.loads(json_match.group(0))
                        submissions = json_data.get("total", 0)
                        break
                    except:
                        pass

        # Get user API data for solved problems
        async with session.get(
            f"https://dmoj.ca/api/v2/user/{username}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"Server Response Error: {response.status}")
            api_data = await response.json()

        solved_list = (
            api_data.get("data", {}).get("object", {}).get("solved_problems", [])
        )

        return {
            "solved": len(solved_list),
            "submissions": submissions,
            "solved_list": solved_list,
        }

    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError("Error while parsing")
