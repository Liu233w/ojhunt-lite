"""
Tests for VNOJ crawler
"""

import pytest
from ojhunt.crawlers.vnoj import __crawler_meta__, query

pytestmark = pytest.mark.network

TEST_USERNAME = __crawler_meta__["test_username"]
NOT_EXIST_USERNAME = "fmv84zcq3hwu"


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
    # VNOJ's API and per-user solved-list page are disabled; only the profile
    # page count remains, so solved_list is unavailable.
    assert result["solved_list"] is None

    assert result["solved"] > 0
