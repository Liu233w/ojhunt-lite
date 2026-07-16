"""
Tests for the shared aiohttp session factory (no network).
"""

import pytest

from ojhunt.core.session import (
    DEFAULT_HEADERS,
    IDENTITY_HEADER,
    IDENTITY_VALUE,
    USER_AGENT,
    create_session,
)


def test_default_headers_contain_identity():
    assert DEFAULT_HEADERS["User-Agent"] == USER_AGENT
    assert DEFAULT_HEADERS[IDENTITY_HEADER] == IDENTITY_VALUE


def test_user_agent_links_to_site():
    assert USER_AGENT.startswith("OJHunt/")
    assert "https://ojhunt.com" in USER_AGENT


def test_identity_value_has_contact_and_link():
    assert "https://ojhunt.com" in IDENTITY_VALUE
    assert "support@ojhunt.com" in IDENTITY_VALUE


@pytest.mark.asyncio
async def test_session_sends_identity_headers_by_default():
    session = create_session()
    try:
        assert session.headers[IDENTITY_HEADER] == IDENTITY_VALUE
        assert session.headers["User-Agent"] == USER_AGENT
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_caller_headers_merge_without_dropping_identity():
    # A crawler-style User-Agent override must not drop the X-OJHunt header:
    # aiohttp merges these session defaults with per-request headers by key.
    session = create_session(headers={"User-Agent": "Mozilla/5.0 (browser)"})
    try:
        assert session.headers["User-Agent"] == "Mozilla/5.0 (browser)"
        assert session.headers[IDENTITY_HEADER] == IDENTITY_VALUE
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_per_request_override_keeps_identity_header():
    # The load-bearing behavior: a crawler (e.g. poj/vjudge) passing its own
    # User-Agent per request still sends X-OJHunt from the session defaults.
    # _prepare_headers is the exact merge aiohttp applies on every request.
    session = create_session()
    try:
        merged = session._prepare_headers({"User-Agent": "Mozilla/5.0 (browser)"})
        assert merged["User-Agent"] == "Mozilla/5.0 (browser)"
        assert merged[IDENTITY_HEADER] == IDENTITY_VALUE
    finally:
        await session.close()
