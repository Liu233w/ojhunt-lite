"""
Tests for Nowcoder crawler
"""

import pytest
import pytest_asyncio
import aiohttp
from crawlers.nowcoder import __crawler_meta__, query

pytestmark = pytest.mark.network

TEST_USERNAME = __crawler_meta__["test_username"]
NOT_EXIST_USERNAME = "11"  # This ID doesn't exist


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
async def test_username_not_id_format(session):
    """Test that usernames that are not ID format are rejected"""
    # Must be numeric ID format
    with pytest.raises(ValueError, match="牛客网的输入必须是用户ID（数字格式）"):
        await query(session, "wwwlsmcom")

    with pytest.raises(ValueError, match="牛客网的输入必须是用户ID（数字格式）"):
        await query(session, "123wwwlsmcom")

    with pytest.raises(ValueError, match="牛客网的输入必须是用户ID（数字格式）"):
        await query(session, "123 wwwlsmcom")

    with pytest.raises(ValueError, match="牛客网的输入必须是用户ID（数字格式）"):
        await query(session, " wwwlsmcom")


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
    assert result["submissions"] >= result["solved"]

    # Check that solved_list has the correct length
    assert len(result["solved_list"]) == result["solved"]

    # Check for known solved problem
    assert "16632" in result["solved_list"]
