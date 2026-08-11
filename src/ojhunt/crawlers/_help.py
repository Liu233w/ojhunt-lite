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

import inspect
from collections.abc import Callable
from typing import Any

from ojhunt.core.models import CrawlerMeta, LoginType

_RULE = "-" * 56


def compose_query_doc(raw_doc: str | None, crawler_doc: str) -> str:
    """Append generated crawler documentation to a query function's own docstring.

    The crawler's docstring is dedented first so that help() renders both halves
    at the same indentation, and a rule separates them so the generated text does
    not read as a continuation of the last section.

    The result lands on the *wrapped* query the registry hands out, whose return
    type differs from the one the module's own docstring describes, so the join
    says so.

    Args:
        raw_doc: The crawler query function's __doc__, or None if it has none
        crawler_doc: Text from render_crawler_doc()

    Returns:
        The combined documentation text.
    """
    if not raw_doc or not raw_doc.strip():
        return crawler_doc
    wrapped_note = (
        "Reached through the registry, this returns a CrawlerResult rather than the\n"
        "dict described above. Import the module directly for the raw dict."
    )
    return f"{inspect.cleandoc(raw_doc)}\n\n{_RULE}\n\n{wrapped_note}\n\n{crawler_doc}"


def _login_paragraph(name: str, meta: CrawlerMeta, params: list[str]) -> str:
    if meta.login_type is LoginType.NOT_REQUIRED:
        return "Login: not required."

    shared = meta.login_type is LoginType.SHARED_ACCOUNT
    assert shared or meta.login_type is LoginType.OWN_ACCOUNT, (
        f"no login paragraph written for {meta.login_type}"
    )

    if shared:
        lines = [
            "Login: required, any account.",
            f"{meta.title} hides every profile from guests, but any authenticated",
            "account can look up any user.",
        ]
    else:
        lines = [
            "Login: required, as the user being queried.",
            f"{meta.title} only exposes the statistics of whoever is logged in, so",
            "the credentials must belong to the user being queried.",
        ]

    # get_login_kwargs() only ever passes login_user/login_password, so the env
    # vars are worth naming only to a crawler that accepts them.
    if "login_user" in params:
        upper = name.upper()
        which = (
            "login_user and login_password"
            if shared
            else "password, or login_user and login_password set to that user"
        )
        lines += [
            f"Pass {which}; the web app reads them from",
            f"LOGIN_USERNAME__{upper} and LOGIN_PASSWORD__{upper}.",
        ]
    else:
        lines.append("Pass password.")

    return "\n".join(lines)


def _usage_example(name: str, meta: CrawlerMeta, params: list[str]) -> str:
    sample = meta.test_username or "username"
    creds = ""
    if meta.login_type is not LoginType.NOT_REQUIRED:
        if "login_user" in params:
            creds = ', login_user="...", login_password="..."'
        else:
            creds = ', password="..."'
    return (
        "Usage:\n"
        "    from ojhunt.crawlers import crawlers\n"
        f'    result = crawlers.{name}.query_sync("{sample}"{creds})\n'
        "    print(result.solved, result.submissions, result.solved_list)\n"
        "\n"
        f"Same query without the registry, which is what a copy of {name}.py\n"
        "can use:\n"
        "    from ojhunt.crawlers import query_sync\n"
        f"    from ojhunt.crawlers.{name} import query\n"
        f'    result = query_sync(query, "{sample}"{creds})'
    )


def render_crawler_doc(
    name: str, meta: CrawlerMeta, query_fn: Callable[..., Any]
) -> str:
    """Build the documentation text shown by help() for one crawler.

    Registry discovery attaches the result to each CrawlerInfo and to the query
    function it hands out, so `help()` on either answers what the crawler does,
    whether it needs a login, and how to pass arguments. Everything is derived
    from __crawler_meta__ and the query signature rather than written per crawler
    file, whose docstring slot holds the license header — see ADR 0014.

    Args:
        name: Crawler name, i.e. its module basename (e.g. "codeforces")
        meta: Metadata parsed from the crawler's __crawler_meta__
        query_fn: The crawler's query function; its signature supplies the
            accepted arguments, which the login and usage sections both need

    Returns:
        Documentation text, suitable for assigning to __doc__.
    """
    params: list[str] = list(inspect.signature(query_fn).parameters)

    sections = [f"{meta.title} — {meta.url}" if meta.url else meta.title]

    if meta.description:
        sections.append(meta.description)

    if meta.is_aggregator:
        sections.append(
            "Aggregator: mirrors problems from other judges and submits through its\n"
            "own shared accounts, so solved_list entries already carry a source\n"
            "prefix (e.g. codeforces-1A)."
        )

    sections.append(_login_paragraph(name, meta, params))
    sections.append(f"Call: query({', '.join(params)}) -> CrawlerResult")
    sections.append(_usage_example(name, meta, params))

    return "\n\n".join(sections) + "\n"
