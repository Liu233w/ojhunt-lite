"""Unit tests for core/runner.py — run_crawler() exception handling."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from ojhunt.core.models import CrawlerMeta, CrawlerInfo, CrawlerResult
from ojhunt.core.runner import run_crawler


def _make_crawler(query_fn) -> CrawlerInfo:
    return CrawlerInfo(
        name="test",
        meta=CrawlerMeta(title="Test Crawler"),
        query=query_fn,
    )


@pytest.mark.asyncio
async def test_run_crawler_success():
    crawler_result = CrawlerResult(solved=42, submissions=100, solved_list=["1A", "2B"])
    crawler = _make_crawler(AsyncMock(return_value=crawler_result))
    client = MagicMock()

    result = await run_crawler(client, crawler, "tourist")

    assert result.success is True
    assert result.solved == 42
    assert result.submissions == 100
    assert result.solved_list == ["1A", "2B"]
    assert result.duration > 0
    assert result.error is None
    assert result.username == "tourist"
    assert result.crawler is crawler


@pytest.mark.asyncio
async def test_run_crawler_value_error_returns_bare_message():
    crawler = _make_crawler(AsyncMock(side_effect=ValueError("User not found")))
    client = MagicMock()

    result = await run_crawler(client, crawler, "nobody")

    assert result.success is False
    assert result.error == "User not found"


@pytest.mark.asyncio
async def test_run_crawler_generic_exception_returns_type_prefixed_message():
    crawler = _make_crawler(AsyncMock(side_effect=RuntimeError("connection timeout")))
    client = MagicMock()

    result = await run_crawler(client, crawler, "user")

    assert result.success is False
    assert result.error == "RuntimeError: connection timeout"
