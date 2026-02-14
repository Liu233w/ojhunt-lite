"""
Tests for LeetCode CN crawler
"""

import pytest
import pytest_asyncio
import aiohttp
from crawlers.leetcode_cn import query

# Test username from crawlers.test.js
TEST_USERNAME = "wwwlsmcom"
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

    assert result["solved"] > 0
    assert result["submissions"] > 0
    assert result["submissions"] >= result["solved"]

    if result["solved_list"] is not None:
        assert len(result["solved_list"]) == result["solved"]
