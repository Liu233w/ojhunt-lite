"""
Tests for DOJ crawler
"""

import pytest

from ojhunt.crawlers.doj import __crawler_meta__, query

pytestmark = pytest.mark.network

TEST_USERNAME = __crawler_meta__["test_username"]
NOT_EXIST_USERNAME = "this_user_does_not_exist_zzz_123"


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

    assert result["solved"] > 0
    assert result["submissions"] >= result["solved"]

    assert result["solved_list"] is None, (
        "the problems listing omits solved problems, so no list is reported"
    )
