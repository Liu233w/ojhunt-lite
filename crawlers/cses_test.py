"""
Tests for CSES crawler

Note: CSES tests require login credentials.
These tests will be skipped if environment variables are not set.
Set LOGIN_USERNAME__CSES and LOGIN_PASSWORD__CSES environment variables to run these tests.
"""

import os
import pytest
import pytest_asyncio
import aiohttp
from crawlers.cses import query, __crawler_meta__

TEST_USERNAME = __crawler_meta__["test_username"]
NOT_EXIST_ID = "9999999999"

CSES_USERNAME = os.getenv("LOGIN_USERNAME__CSES")
CSES_PASSWORD = os.getenv("LOGIN_PASSWORD__CSES")

pytestmark = [
    pytest.mark.network,
    pytest.mark.skipif(
        not CSES_USERNAME or not CSES_PASSWORD,
        reason="CSES credentials not configured. Set LOGIN_USERNAME__CSES and LOGIN_PASSWORD__CSES environment variables.",
    ),
]


@pytest_asyncio.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_user_not_exist(session):
    with pytest.raises(ValueError, match="The user does not exist"):
        await query(
            session,
            NOT_EXIST_ID,
            login_user=CSES_USERNAME,
            login_password=CSES_PASSWORD,
        )


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_username_with_space(session):
    with pytest.raises(ValueError):
        await query(session, "   ")


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_missing_credentials(session):
    with pytest.raises(ValueError, match="requires login credentials"):
        await query(session, TEST_USERNAME)


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_valid_user(session):
    result = await query(
        session,
        TEST_USERNAME,
        login_user=CSES_USERNAME,
        login_password=CSES_PASSWORD,
    )
    assert result["solved"] > 0
    assert result["submissions"] >= result["solved"]
    assert isinstance(result["solved_list"], list)
    assert len(result["solved_list"]) == result["solved"]


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_self_query(session):
    assert CSES_USERNAME is not None
    result = await query(session, CSES_USERNAME, password=CSES_PASSWORD)
    assert result["solved"] >= 0
    assert result["submissions"] >= 0
    assert isinstance(result["solved_list"], list)
