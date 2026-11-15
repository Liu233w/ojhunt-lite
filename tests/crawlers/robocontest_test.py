"""
Tests for RoboContest crawler
"""

import pytest

from ojhunt.crawlers.robocontest import __crawler_meta__, query

pytestmark = pytest.mark.network

TEST_USERNAME = __crawler_meta__["test_username"]
NOT_EXIST_USERNAME = "zzqxnouser123"


@pytest.mark.asyncio
async def test_user_not_exist(session):
    """Test that non-existent user raises ValueError"""
    with pytest.raises(ValueError, match="The user does not exist"):
        await query(session, NOT_EXIST_USERNAME)


@pytest.mark.asyncio
async def test_username_with_space(session):
    """Test that a blank username raises ValueError"""
    with pytest.raises(ValueError):
        await query(session, "   ")


@pytest.mark.asyncio
async def test_valid_user(session):
    """Test that valid user returns correct data structure"""
    result = await query(session, TEST_USERNAME)

    assert isinstance(result["solved"], int)
    assert isinstance(result["submissions"], int)
    assert isinstance(result["solved_list"], list)

    assert result["solved"] > 0
    assert result["submissions"] >= result["solved"]

    assert 0 < len(result["solved_list"]) <= result["solved"], (
        "the profile's task map omits some tasks, so the list can be shorter"
    )
    assert "A0001" in result["solved_list"]
