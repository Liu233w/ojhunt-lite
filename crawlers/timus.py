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

__crawler_meta__ = {
    "title": "Timus (URAL)",
    "description": "",
    "url": "http://acm.timus.ru/",
}


async def _query_list(session: aiohttp.ClientSession, uri: str) -> int:
    """
    Recursively count submissions by following pagination.

    Args:
        session: aiohttp ClientSession
        uri: URI to query

    Returns:
        Number of submissions found
    """
    async with session.get(
        f"http://acm.timus.ru/{uri}", timeout=aiohttp.ClientTimeout(total=30)
    ) as response:
        text = await response.text()

    doc = LexborHTMLParser(text)

    # Count number of problems in current page
    num = len(doc.css("td.problem"))

    if num == 0:
        return 0

    # Check if there's a next page link
    next_link = doc.css_first('a:lexbor-contains("Next")')
    if next_link and next_link.attributes.get("href"):
        return num + await _query_list(session, next_link.attributes["href"])

    return num


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query Timus for user statistics.

    Args:
        username: Timus username

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
        # First, search for the user
        async with session.get(
            "http://acm.timus.ru/search.aspx",
            params={"Str": username},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            search_text = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    doc_search = LexborHTMLParser(search_text)

    # Find user in search results - look for <td class="name">USERNAME</td> with exact match
    profile_href = None

    # Extract all <td class="name"> entries and find the one with exact username match
    for td in doc_search.css("td.name"):
        if td.text(strip=True) == username:
            # Extract the href from <a> tag within this td
            link = td.css_first("a")
            if link:
                profile_href = link.attributes.get("href")
                break

    if not profile_href:
        raise ValueError("The user does not exist")

    try:
        # Now get the user profile page
        async with session.get(
            f"http://acm.timus.ru/{profile_href}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            profile_text = await response.text()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    try:
        doc_profile = LexborHTMLParser(profile_text)

        # Extract solved count - "Problems solved" followed by <td>NUMBER</td>
        solved_text = doc_profile.css_first(
            'td.author_stats_name:lexbor-contains("Problems solved") + td'
        ).text(strip=True)
        solved_match = re.search(r"(\d+)", solved_text)
        solved = int(solved_match.group(1))

        # Extract submission page URI - look for <a>Recent submissions</a>
        submission_page_uri = doc_profile.css_first(
            'a:lexbor-contains("Recent submissions")'
        ).attributes["href"]

        # Get total submissions by recursively querying submission pages
        submissions = await _query_list(session, submission_page_uri)

        # Extract solved list - <td class="accepted"><a>PROBLEM_ID</a></td>
        solved_list = [a.text(strip=True) for a in doc_profile.css("td.accepted a")]

        return {
            "solved": solved,
            "submissions": submissions,
            "solved_list": solved_list,
        }

    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError("Error while parsing")
