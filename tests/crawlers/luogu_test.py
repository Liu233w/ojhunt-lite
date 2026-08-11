"""
Tests for Luogu crawler
"""

import pytest

from ojhunt.crawlers.luogu import __crawler_meta__, query

pytestmark = pytest.mark.network

TEST_USERNAME_ID = __crawler_meta__["test_username"]  # user_id
TEST_USERNAME_HEAVY = "NaCly_Fish"  # user with >1000 submissions
NOT_EXIST_USERNAME = "fmv84zcq3hwu"


@pytest.mark.asyncio
@pytest.mark.timeout(50)  # Luogu needs longer timeout (50 seconds in original)
async def test_user_not_exist(session):
    """Test that non-existent user raises ValueError"""
    with pytest.raises(ValueError, match="The user does not exist"):
        await query(session, NOT_EXIST_USERNAME)


@pytest.mark.asyncio
@pytest.mark.timeout(50)
async def test_username_with_space(session):
    """Test that username with space is handled correctly"""
    with pytest.raises(ValueError, match="The user does not exist"):
        await query(session, " " + NOT_EXIST_USERNAME)


@pytest.mark.asyncio
@pytest.mark.timeout(50)
async def test_valid_user(session):
    """Test that valid user returns correct data structure"""
    result = await query(session, TEST_USERNAME_ID)

    assert "solved" in result
    assert "submissions" in result
    assert "solved_list" in result

    assert isinstance(result["solved"], int)
    assert isinstance(result["submissions"], int)
    assert result["solved_list"] is None  # Luogu no longer exposes solved list

    assert result["solved"] > 0
    assert result["submissions"] > 0
    assert result["submissions"] >= result["solved"]

    # This user should have more than 100 solved problems
    assert result["solved"] > 100


@pytest.mark.asyncio
@pytest.mark.timeout(50)
async def test_user_with_many_submissions(session):
    """Test that user with submission count bigger than 1000 is handled correctly"""
    result = await query(session, TEST_USERNAME_HEAVY)

    assert "solved" in result
    assert "submissions" in result
    assert "solved_list" in result

    assert isinstance(result["solved"], int)
    assert isinstance(result["submissions"], int)
    assert result["solved_list"] is None  # Luogu no longer exposes solved list

    assert result["solved"] > 0
    assert result["submissions"] > 1000
    assert result["submissions"] >= result["solved"]
