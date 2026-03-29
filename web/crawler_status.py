"""
Background crawler availability checker.

Checks each crawler one at a time, caching results in memory.
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum

import aiohttp

from core.credentials import get_login_kwargs
from core.models import CrawlerInfo, LoginType
from core.runner import run_crawler
from crawlers import discover_crawlers

logger = logging.getLogger(__name__)


class CheckStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    WAITING = "waiting"


@dataclass
class CrawlerAvailability:
    status: CheckStatus
    error: str | None = None


# Check interval between individual crawlers (seconds)
CHECK_INTERVAL = 2
# Interval between full passes (seconds)
FULL_PASS_INTERVAL = 7200

_status: dict[str, CrawlerAvailability] = {}
_checker_task: asyncio.Task | None = None


def get_all_status() -> dict[str, CrawlerAvailability]:
    return dict(_status)


async def _check_one(
    client: aiohttp.ClientSession, name: str, crawler: CrawlerInfo
) -> CrawlerAvailability:
    """Check a single crawler's availability."""
    if crawler.meta.login_type == LoginType.SHARED_ACCOUNT:
        kwargs = get_login_kwargs(name)
        if kwargs is None:
            upper = name.upper()
            return CrawlerAvailability(
                CheckStatus.OFFLINE,
                error=f"Login credentials not configured (set LOGIN_USERNAME__{upper} / LOGIN_PASSWORD__{upper})",
            )
    else:
        kwargs = {}

    test_user = crawler.meta.test_username
    if not test_user:
        return CrawlerAvailability(
            CheckStatus.OFFLINE, error="No test_username configured"
        )

    try:
        result = await run_crawler(client, crawler, test_user, **kwargs)
        if result.success:
            return CrawlerAvailability(CheckStatus.ONLINE)
        return CrawlerAvailability(CheckStatus.OFFLINE, error=result.error)
    except Exception:
        logger.exception("Error checking crawler %s", name)
        return CrawlerAvailability(
            CheckStatus.OFFLINE, error="Unexpected error during check"
        )


async def _checker_loop(client: aiohttp.ClientSession) -> None:
    """Background loop that checks crawlers one by one."""
    crawlers = discover_crawlers()

    # Initialize all to waiting
    for name in crawlers:
        _status[name] = CrawlerAvailability(CheckStatus.WAITING)

    while True:
        for name, crawler in crawlers.items():
            _status[name] = CrawlerAvailability(CheckStatus.WAITING)
            try:
                _status[name] = await _check_one(client, name, crawler)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Unexpected error in checker loop for %s", name)
                _status[name] = CrawlerAvailability(
                    CheckStatus.OFFLINE, error="Unexpected error in checker loop"
                )
            await asyncio.sleep(CHECK_INTERVAL)

        await asyncio.sleep(FULL_PASS_INTERVAL)


def start_checker(client: aiohttp.ClientSession) -> None:
    global _checker_task
    _checker_task = asyncio.create_task(_checker_loop(client))


async def stop_checker() -> None:
    global _checker_task
    if _checker_task:
        _checker_task.cancel()
        try:
            await _checker_task
        except asyncio.CancelledError:
            pass
        _checker_task = None
