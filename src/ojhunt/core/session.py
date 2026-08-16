"""
Shared aiohttp session factory.

Every outbound crawler request originates from a session built here so that OJHunt
identifies itself to the online judges it queries — giving their maintainers a way to
see who is querying them and how to reach the project (feedback, opt-out). The
identification lives at the session layer, never in the individual ``crawlers/*.py``
files, so a copied-out crawler carries no OJHunt branding.

The identity points at the *repository*, which is correct for every instance — hosted,
self-hosted or third-party. An operator names their own deployment by setting
``OJHUNT_INSTANCE_URL``, so a judge maintainer can reach whoever actually runs it.
"""

import importlib.metadata
import os
from typing import Any

import aiohttp

PROJECT_URL = "https://github.com/Liu233w/ojhunt-lite"
PROJECT_CONTACT = "support@ojhunt.com"
INSTANCE_URL_ENV = "OJHUNT_INSTANCE_URL"

# ``X-OJHunt`` rides on EVERY request. No crawler sets this key, so it survives even
# when a crawler overrides ``User-Agent`` with a browser string to dodge bot-blocking
# (e.g. poj, vjudge) — keeping us identifiable in that case.
IDENTITY_HEADER = "X-OJHunt"


def _version() -> str:
    try:
        return importlib.metadata.version("ojhunt")
    except importlib.metadata.PackageNotFoundError:
        return "0"


def _instance_url() -> str | None:
    """
    Return the operator-configured URL of this deployment, or ``None``.

    Read per call, not at import time: ``web/app.py`` imports this module before it
    calls ``load_dotenv()``, so a module-level read would miss ``.env``.
    """
    raw = os.environ.get(INSTANCE_URL_ENV, "").strip()
    if not raw:
        return None
    # The value lands verbatim in a header, so whitespace (a newline above all) would
    # let a bad config inject one.
    if not raw.startswith(("http://", "https://")) or any(c.isspace() for c in raw):
        raise ValueError(
            f"{INSTANCE_URL_ENV} must be an absolute http(s) URL without whitespace, "
            f"got {raw!r}"
        )
    return raw


def user_agent() -> str:
    """Build the ``User-Agent`` — the primary signal, visible in judge access logs."""
    instance = _instance_url()
    suffix = f"; instance {instance}" if instance else ""
    return f"OJHunt/{_version()} (+{PROJECT_URL}{suffix})"


def identity_value() -> str:
    """Build the ``X-OJHunt`` value, which survives a crawler's ``User-Agent`` override."""
    instance = _instance_url()
    run_by = f" This instance runs at {instance}." if instance else ""
    return (
        f"OJHunt online-judge stats aggregator ({PROJECT_URL})."
        f"{run_by}"
        f" Contact {PROJECT_CONTACT} with questions or to opt out."
    )


def default_headers() -> dict[str, str]:
    return {"User-Agent": user_agent(), IDENTITY_HEADER: identity_value()}


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

    Raises ``ValueError`` when ``OJHUNT_INSTANCE_URL`` is set to a malformed value.
    """
    merged = {**default_headers(), **(headers or {})}
    return aiohttp.ClientSession(headers=merged, **kwargs)
