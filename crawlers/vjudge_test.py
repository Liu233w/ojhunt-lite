"""
Tests for VJudge crawler

Note: VJudge tests require configuration with login credentials.
These tests will be skipped if environment variables are not set.
Set VJUDGE_USERNAME and VJUDGE_PASSWORD environment variables to run these tests.
"""

import pytest
import pytest_asyncio
import aiohttp
import os
from crawlers.vjudge import __crawler_meta__, query

TEST_USERNAME = __crawler_meta__["test_username"]
NOT_EXIST_USERNAME = "fmv84zcq3hwu"
USERNAME_WITHOUT_SUBMISSIONS = "nwpuacm"


@pytest_asyncio.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


VJUDGE_USERNAME = os.getenv("VJUDGE_USERNAME")
VJUDGE_PASSWORD = os.getenv("VJUDGE_PASSWORD")


pytestmark = [
    pytest.mark.network,
    pytest.mark.skipif(
        not VJUDGE_USERNAME or not VJUDGE_PASSWORD,
        reason="VJudge credentials not configured. Set VJUDGE_USERNAME and VJUDGE_PASSWORD environment variables.",
    ),
]


@pytest.mark.asyncio
@pytest.mark.timeout(50)
async def test_user_not_exist(session):
    """Test that non-existent user raises ValueError"""
    with pytest.raises(ValueError, match="The user does not exist"):
        await query(
            session,
            NOT_EXIST_USERNAME,
            login_user=VJUDGE_USERNAME,
            login_password=VJUDGE_PASSWORD,
        )


@pytest.mark.asyncio
@pytest.mark.timeout(50)
async def test_username_with_space(session):
    """Test that username with space is handled correctly"""
    with pytest.raises(ValueError, match="The user does not exist"):
        await query(
            session,
            " " + NOT_EXIST_USERNAME,
            login_user=VJUDGE_USERNAME,
            login_password=VJUDGE_PASSWORD,
        )


@pytest.mark.asyncio
@pytest.mark.timeout(50)
async def test_valid_user_with_embedded_password(session):
    """Test valid user with embedded password (login as target user)"""
    assert VJUDGE_USERNAME is not None
    result = await query(
        session,
        VJUDGE_USERNAME,
        password=VJUDGE_PASSWORD,
    )

    assert "solved" in result
    assert "submissions" in result
    assert "solved_list" in result

    assert isinstance(result["solved"], int)
    assert isinstance(result["submissions"], int)
    assert isinstance(result["solved_list"], list)

    assert result["solved"] >= 0
    assert result["submissions"] >= 0
    assert result["submissions"] >= result["solved"]


@pytest.mark.asyncio
@pytest.mark.timeout(50)
async def test_valid_user_with_separate_login(session):
    """Test valid user with separate login credentials (query another user)"""
    result = await query(
        session,
        TEST_USERNAME,
        login_user=VJUDGE_USERNAME,
        login_password=VJUDGE_PASSWORD,
    )

    assert "solved" in result
    assert "submissions" in result
    assert "solved_list" in result

    assert isinstance(result["solved"], int)
    assert isinstance(result["submissions"], int)
    assert isinstance(result["solved_list"], list)

    assert result["solved"] > 0
    assert result["submissions"] > 0
    assert result["submissions"] >= result["solved"]

    assert len(result["solved_list"]) == result["solved"]

    assert "codeforces-436B" in result["solved_list"]


@pytest.mark.asyncio
@pytest.mark.timeout(50)
async def test_missing_credentials(session):
    """Test that missing credentials raises ValueError"""
    with pytest.raises(ValueError, match="requires login credentials"):
        await query(session, TEST_USERNAME)


@pytest.mark.asyncio
@pytest.mark.timeout(50)
async def test_user_with_no_submissions(session):
    """Test user with no submissions returns zero stats"""
    result = await query(
        session,
        USERNAME_WITHOUT_SUBMISSIONS,
        login_user=VJUDGE_USERNAME,
        login_password=VJUDGE_PASSWORD,
    )

    assert result["solved"] == 0
    assert result["submissions"] == 0
    assert result["solved_list"] == []
