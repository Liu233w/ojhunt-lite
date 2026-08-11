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
from selectolax.lexbor import LexborHTMLParser

__crawler_meta__ = {
    "title": "牛客OJ",
    "description": "目前只支持输入用户ID（在你的AC列表的URL中）",
    "url": "https://ac.nowcoder.com/acm/home",
    "test_username": "112946",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> dict[str, int | list[str]]:
    """
    Query Nowcoder for user statistics.

    Args:
        username: Nowcoder user ID (must be numeric)

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty, not numeric, or user doesn't exist
        RuntimeError: If API returns an error
    """
    if not username or not username.strip():
        raise ValueError("请输入用户ID")

    username = username.strip()

    # Check if username is numeric
    if not username.isdigit():
        raise ValueError("牛客网的输入必须是用户ID（数字格式）")

    # Convert to number and back to string to normalize
    username = str(int(username))

    solved = None
    submissions = None
    solved_set = set()
    last_submission_id = float("inf")
    page = 1

    try:
        while True:
            params = {
                "pageSize": "200",
                "statusTypeFilter": "5",  # AC submissions
                "languageCategoryFilter": "-1",
                "orderType": "DESC",
                "page": str(page),
            }
            async with session.get(
                f"https://ac.nowcoder.com/acm/contest/profile/{username}/practice-coding",
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Server Response Error: {response.status}")
                text = await response.text()

            # Check if user exists
            if "用户不存在" in text:
                raise ValueError("The user does not exist")

            doc = LexborHTMLParser(text)

            # Extract solved and submissions on first page
            if solved is None:
                solved_text = doc.css_first(
                    'span:lexbor-contains("题已通过")'
                ).parent.text(strip=True)
                solved = int(solved_text.replace("题已通过", ""))
                submissions_text = doc.css_first(
                    'span:lexbor-contains("次提交")'
                ).parent.text(strip=True)
                submissions = int(submissions_text.replace("次提交", ""))

            # Extract new submission ID to check for pagination loop
            # Look for first <a href="/acm/contest/view-submission...">SUBMISSION_ID</a>
            submission_link = doc.css_first('a[href*="/acm/contest/view-submission"]')
            if submission_link:
                new_submission_id = int(submission_link.text(strip=True))
                if new_submission_id == last_submission_id:
                    break
                last_submission_id = new_submission_id

            # Extract problem IDs - look for <a href="/acm/problem/...">
            for link in doc.css('a[href^="/acm/problem/"]'):
                href = link.attributes.get("href", "")
                pid = href.split("/")[-1]
                if pid.isdigit():
                    solved_set.add(pid)

            page += 1

    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {e!s}")
    except ValueError:
        raise
    except Exception:
        raise RuntimeError("Error while parsing")

    return {
        "solved": solved if solved is not None else 0,
        "submissions": submissions if submissions is not None else 0,
        "solved_list": list(solved_set),
    }
