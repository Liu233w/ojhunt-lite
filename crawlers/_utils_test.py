"""
Tests for crawlers._utils module
"""

from typing import Optional

import pytest
import pytest_asyncio
import aiohttp
from crawlers import _utils

pytestmark = pytest.mark.network


@pytest_asyncio.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


async def _mock_resolver(
    session: aiohttp.ClientSession, problem_id: int
) -> Optional[str]:
    return f"label-{problem_id}"


@pytest.mark.asyncio
async def test_resolve_labels_basic(session):
    result = await _utils.resolve_labels(session, "test_oj", [1, 2, 3], _mock_resolver)
    assert result == {1: "label-1", 2: "label-2", 3: "label-3"}


@pytest.mark.asyncio
async def test_resolve_labels_empty_list(session):
    result = await _utils.resolve_labels(session, "test_oj", [], _mock_resolver)
    assert result == {}


@pytest.mark.asyncio
async def test_resolve_labels_caching(session):
    call_count = 0

    async def counting_resolver(sess: aiohttp.ClientSession, pid: int) -> Optional[str]:
        nonlocal call_count
        call_count += 1
        return f"label-{pid}"

    result1 = await _utils.resolve_labels(session, "test_oj", [1, 2], counting_resolver)
    assert result1 == {1: "label-1", 2: "label-2"}
    assert call_count == 2

    result2 = await _utils.resolve_labels(session, "test_oj", [1, 2], counting_resolver)
    assert result2 == {1: "label-1", 2: "label-2"}
    assert call_count == 2


@pytest.mark.asyncio
async def test_resolve_labels_mixed_cache_and_fetch(session):
    call_count = 0

    async def counting_resolver(sess: aiohttp.ClientSession, pid: int) -> Optional[str]:
        nonlocal call_count
        call_count += 1
        return f"label-{pid}"

    result1 = await _utils.resolve_labels(session, "test_oj", [1, 2], counting_resolver)
    assert result1 == {1: "label-1", 2: "label-2"}
    assert call_count == 2

    result2 = await _utils.resolve_labels(
        session, "test_oj", [1, 2, 3], counting_resolver
    )
    assert result2 == {1: "label-1", 2: "label-2", 3: "label-3"}
    assert call_count == 3


@pytest.mark.asyncio
async def test_resolve_labels_rate_limit(session):
    import time

    async def slow_resolver(sess: aiohttp.ClientSession, pid: int) -> Optional[str]:
        return f"label-{pid}"

    start = time.time()
    await _utils.resolve_labels(
        session, "test_oj", [1, 2, 3], slow_resolver, rate_limit_delay=0.1
    )
    elapsed = time.time() - start

    assert elapsed >= 0.1
