"""
Tests for LOJ crawler
"""

import pytest

from ojhunt.crawlers.loj import __crawler_meta__, query

pytestmark = pytest.mark.network

TEST_USERNAME = __crawler_meta__["test_username"]
NOT_EXIST_USERNAME = "fmv84zcq3hwu"


@pytest.mark.asyncio
async def test_user_not_exist(session):
    """Test that non-existent user raises ValueError"""
    with pytest.raises(ValueError, match="The user does not exist"):
        await query(session, NOT_EXIST_USERNAME)


@pytest.mark.asyncio
@pytest.mark.timeout(50)  # LOJ needs longer timeout (50 seconds in original)
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

    assert len(result["solved_list"]) == result["solved"], (
        "solved_list must hold one entry per solved problem"
    )

    assert "103" in result["solved_list"], (
        "a known solved problem must appear in solved_list"
    )
