"""
Tests for Yosupo Judge crawler
"""

import pytest
import pytest_asyncio
import aiohttp
from crawlers.yosupo import __crawler_meta__, query

pytestmark = pytest.mark.network

TEST_USERNAME = __crawler_meta__["test_username"]
NOT_EXIST_USERNAME = "nonexistentuser12345678xyz"


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
    with pytest.raises(ValueError):
        await query(session, " " + NOT_EXIST_USERNAME)


@pytest.mark.asyncio
async def test_valid_user(session):
    """Test that valid user returns correct data structure"""
    result = await query(session, TEST_USERNAME)

    assert "solved" in result
    assert "submissions" in result
    assert "solved_list" in result

    assert isinstance(result["solved"], int)
    assert result["submissions"] == 0
    assert isinstance(result["solved_list"], list)

    assert result["solved"] > 0
    assert len(result["solved_list"]) == result["solved"]

    expected_problems = {
        "aplusb",
        "unionfind",
        "static_range_sum",
        "convolution_mod",
    }
    assert expected_problems.issubset(set(result["solved_list"]))
