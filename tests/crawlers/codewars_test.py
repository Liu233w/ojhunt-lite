"""
Tests for Codewars crawler
"""

import pytest
import pytest_asyncio
import aiohttp
from ojhunt.crawlers.codewars import __crawler_meta__, query

pytestmark = pytest.mark.network

# Test username from ojhunt.crawlers.test.js - username is case sensitive
TEST_USERNAME = __crawler_meta__["test_username"]
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
    assert isinstance(result["solved_list"], list)

    assert result["solved"] > 0
    assert result["submissions"] > 0

    # Codewars only returns completed kata count, so submissions == solved
    assert result["submissions"] == result["solved"]

    # Check that solved_list has the correct length
    assert len(result["solved_list"]) == result["solved"]

    # Check for known solved problem
    assert "equal-sides-of-an-array" in result["solved_list"]
