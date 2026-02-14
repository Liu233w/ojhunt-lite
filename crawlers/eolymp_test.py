"""
Tests for EOlymp crawler
"""

import pytest
import pytest_asyncio
import aiohttp
from crawlers.eolymp import query

TEST_USERNAME = "vjudge5"
NOT_EXIST_USERNAME = "fmv84zcq3hwu"


@pytest_asyncio.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


@pytest.mark.asyncio
async def test_user_not_exist(session):
    """Test that non-existent user raises ValueError"""
    with pytest.raises(ValueError, match="The user does not exist"):
        await query(session, NOT_EXIST_USERNAME)


@pytest.mark.asyncio
async def test_username_with_space(session):
    """Test that username with space is handled correctly"""
    with pytest.raises(ValueError, match="The user does not exist"):
        await query(session, " " + NOT_EXIST_USERNAME)


@pytest.mark.asyncio
async def test_valid_user(session):
    """Test that valid user returns correct data structure"""
    result = await query(session, TEST_USERNAME)

    assert "solved" in result
    assert "submissions" in result
    assert "solved_list" in result

    assert isinstance(result["solved"], int)
    assert isinstance(result["submissions"], int)
    assert result["solved_list"] is None

    assert result["solved"] > 0
    assert result["submissions"] > 0


@pytest.mark.asyncio
async def test_case_insensitive_search(session):
    """Test that search is case-insensitive"""
    result_lower = await query(session, "vjudge5")
    result_upper = await query(session, "VJUDGE5")

    assert result_lower["solved"] == result_upper["solved"]
    assert result_lower["submissions"] == result_upper["submissions"]
