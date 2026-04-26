"""
Tests for 51Nod crawler
"""

import pytest
from ojhunt.crawlers.nod import query, __crawler_meta__

TEST_USERNAME = __crawler_meta__["test_username"]
NOT_EXIST_ID = "9999999999"


@pytest.mark.network
@pytest.mark.asyncio
async def test_user_not_exist(session):
    with pytest.raises(ValueError, match="The user does not exist"):
        await query(session, NOT_EXIST_ID)


@pytest.mark.asyncio
async def test_username_with_space(session):
    with pytest.raises(ValueError):
        await query(session, "   ")


@pytest.mark.asyncio
async def test_non_numeric_id(session):
    with pytest.raises(ValueError, match="numeric user ID"):
        await query(session, "tourist")


@pytest.mark.network
@pytest.mark.asyncio
async def test_valid_user(session):
    result = await query(session, TEST_USERNAME)
    assert result["solved"] > 0
    assert result["submissions"] >= result["solved"]
    assert isinstance(result["solved_list"], list)
    # 51Nod may have 1 problem outside standard ProblemTables collections
    assert len(result["solved_list"]) >= result["solved"] - 1
