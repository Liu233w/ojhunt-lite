"""
Shared aiohttp session factory.

Every outbound crawler request originates from a session built here so that OJHunt
identifies itself to the online judges it queries — giving their maintainers a way to
see who is querying them and how to reach the project (feedback, opt-out). The
identification lives at the session layer, never in the individual ``crawlers/*.py``
files, so a copied-out crawler carries no OJHunt branding.
"""

import importlib.metadata
from typing import Any

import aiohttp


def _version() -> str:
    try:
        return importlib.metadata.version("ojhunt")
    except importlib.metadata.PackageNotFoundError:
        return "0"


USER_AGENT = f"OJHunt/{_version()} (+https://ojhunt.com)"

# ``X-OJHunt`` rides on EVERY request. No crawler sets this key, so it survives even
# when a crawler overrides ``User-Agent`` with a browser string to dodge bot-blocking
# (e.g. poj, vjudge) — keeping us identifiable in that case.
IDENTITY_HEADER = "X-OJHunt"
IDENTITY_VALUE = (
    "OJHunt online-judge stats aggregator (https://ojhunt.com). "
    "Contact support@ojhunt.com with questions or to opt out."
)

DEFAULT_HEADERS = {"User-Agent": USER_AGENT, IDENTITY_HEADER: IDENTITY_VALUE}


def create_session(
    *, headers: dict | None = None, **kwargs: Any
) -> aiohttp.ClientSession:
    """
    Build an ``aiohttp.ClientSession`` pre-seeded with OJHunt identification headers.

    aiohttp merges these session-default headers with any per-request ``headers=`` a
    crawler passes, overriding only matching keys. So a crawler that sets its own
    ``User-Agent`` still sends ``X-OJHunt`` from these defaults.

    Extra keyword arguments (e.g. ``trust_env=True``) are forwarded to
    ``aiohttp.ClientSession``.
    """
    merged = {**DEFAULT_HEADERS, **(headers or {})}
    return aiohttp.ClientSession(headers=merged, **kwargs)
