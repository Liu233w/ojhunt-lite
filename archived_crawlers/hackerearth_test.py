# ARCHIVED: HackerEarth is blocked by Cloudflare WAF. These tests are kept
# for reference but are not run by pytest.

import pytest
import pytest_asyncio
import aiohttp
from crawlers.hackerearth import query

TEST_USERNAME = "akash"
NOT_EXIST_USERNAME = "fmv84zcq3hwu"


@pytest_asyncio.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


@pytest.mark.asyncio
async def test_user_not_exist(session):
    with pytest.raises(ValueError, match="The user does not exist"):
        await query(session, NOT_EXIST_USERNAME)


@pytest.mark.asyncio
async def test_username_with_space(session):
    with pytest.raises(ValueError):
        await query(session, "   ")


@pytest.mark.asyncio
async def test_valid_user(session):
    result = await query(session, TEST_USERNAME)

    assert isinstance(result["solved"], int)
    assert isinstance(result["submissions"], int)
    assert result["solved_list"] == []
    assert result["solved"] >= 0
    assert result["submissions"] >= 0
