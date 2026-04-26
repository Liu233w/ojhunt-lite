"""
Tests for LightOJ crawler
"""

import pytest
from ojhunt.crawlers.lightoj import __crawler_meta__, query

pytestmark = pytest.mark.network

TEST_USERNAME = __crawler_meta__["test_username"]
NOT_EXIST_USERNAME = "fmv84zcq3hwu_notexist_xyz"


@pytest.mark.asyncio
async def test_user_not_exist(session):
    with pytest.raises(ValueError, match="The user does not exist"):
        await query(session, NOT_EXIST_USERNAME)


@pytest.mark.asyncio
async def test_username_with_space(session):
    with pytest.raises(ValueError):
        await query(session, " " + NOT_EXIST_USERNAME)


@pytest.mark.asyncio
async def test_valid_user(session):
    result = await query(session, TEST_USERNAME)

    assert "solved" in result
    assert "submissions" in result
    assert "solved_list" in result

    assert result["solved"] > 0
    assert result["submissions"] >= result["solved"]
    # solved_list is not available without authentication
    assert result["solved_list"] is None
