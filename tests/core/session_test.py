"""
Tests for the shared aiohttp session factory (no network).
"""

import pytest

from ojhunt.core.session import (
    IDENTITY_HEADER,
    INSTANCE_URL_ENV,
    PROJECT_CONTACT,
    PROJECT_URL,
    create_session,
    default_headers,
    identity_value,
    user_agent,
)

INSTANCE = "https://example.test"


@pytest.fixture(autouse=True)
def _no_instance_url(monkeypatch):
    # The developer's own .env must not leak into the default-identity tests.
    monkeypatch.delenv(INSTANCE_URL_ENV, raising=False)


def test_default_headers_contain_identity():
    headers = default_headers()
    assert headers["User-Agent"] == user_agent()
    assert headers[IDENTITY_HEADER] == identity_value()


def test_user_agent_links_to_repository():
    ua = user_agent()
    assert ua.startswith("OJHunt/")
    assert PROJECT_URL in ua, (
        "the repo URL is correct for every instance, hosted or not"
    )


def test_identity_value_has_contact_and_link():
    value = identity_value()
    assert PROJECT_URL in value
    assert PROJECT_CONTACT in value


def test_identity_omits_instance_when_unconfigured():
    assert "instance" not in user_agent()
    assert "This instance runs at" not in identity_value()


def test_configured_instance_url_joins_both_headers(monkeypatch):
    monkeypatch.setenv(INSTANCE_URL_ENV, INSTANCE)
    assert INSTANCE in user_agent()
    assert INSTANCE in identity_value()
    assert PROJECT_URL in user_agent(), (
        "the operator URL adds to the repo URL, not replaces it"
    )
    assert PROJECT_URL in identity_value()


@pytest.mark.parametrize(
    "bad",
    [
        "ojhunt.com",
        "ftp://ojhunt.com",
        "https://a.test\r\nX-Evil: 1",
        "https://a b.test",
    ],
)
def test_malformed_instance_url_is_rejected(monkeypatch, bad):
    monkeypatch.setenv(INSTANCE_URL_ENV, bad)
    with pytest.raises(ValueError, match=INSTANCE_URL_ENV):
        user_agent()


def test_blank_instance_url_is_treated_as_unset(monkeypatch):
    monkeypatch.setenv(INSTANCE_URL_ENV, "   ")
    assert "instance" not in user_agent()


@pytest.mark.asyncio
async def test_session_sends_identity_headers_by_default():
    session = create_session()
    try:
        assert session.headers[IDENTITY_HEADER] == identity_value()
        assert session.headers["User-Agent"] == user_agent()
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_caller_headers_merge_without_dropping_identity():
    # A crawler-style User-Agent override must not drop the X-OJHunt header:
    # aiohttp merges these session defaults with per-request headers by key.
    session = create_session(headers={"User-Agent": "Mozilla/5.0 (browser)"})
    try:
        assert session.headers["User-Agent"] == "Mozilla/5.0 (browser)"
        assert session.headers[IDENTITY_HEADER] == identity_value()
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
        assert merged[IDENTITY_HEADER] == identity_value()
    finally:
        await session.close()
