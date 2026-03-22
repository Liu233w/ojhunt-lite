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
    "title": "CSU",
    "description": "",
    "url": "https://vlab.csu.edu.cn/oj",
    "test_username": "admin",
}


async def query(
    session: aiohttp.ClientSession, username: str
) -> Dict[str, Union[int, List[str]]]:
    """
    Query CSU for user statistics.

    Args:
        username: CSU username

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
            "https://vlab.csu.edu.cn/oj/userinfo.php",
            params={"user": username},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"Server Response Error: {response.status}")
            text = await response.text()

        doc = LexborHTMLParser(text)

        if "No such User!" in doc.css_first(".jumbotron").text():
            raise ValueError("The user does not exist")

        # ill-formatted html: <tr ><td>Submit<td align=center><a href='status.php?user_id=admin'>2110</a></tr>
        solved = doc.css_first('td:lexbor-contains("Solved") + td a').text()
        submissions = doc.css_first('td:lexbor-contains("Submit") + td a').text()

        # Extract ac lists (rendered in browser) - data from script
        """
        format:
        function p(id,c){
        ...
        }
        p(0,61);p(1000,4);p(1001,1);...
        """
        ac_list_script = doc.css_first('script:lexbor-contains("function p(id,c){")')
        if ac_list_script:
            ac_list = re.findall(r"p\((\d+),\d+\);", ac_list_script.text(), re.A)
        else:
            ac_list = []

        return {
            "solved": int(solved),
            "submissions": int(submissions),
            "solved_list": ac_list,
        }

    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")
    except ValueError:
        raise
    except Exception:
        raise RuntimeError("Error while parsing")
