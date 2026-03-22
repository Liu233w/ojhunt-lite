"""
Background crawler availability checker.

Checks each crawler one at a time, caching results in memory.
"""

import asyncio
import logging
import os
from typing import Dict, Optional

import aiohttp

from core.models import CrawlerInfo
from core.runner import run_crawler
from crawlers import discover_crawlers

logger = logging.getLogger(__name__)

STATUS_ONLINE = "online"
STATUS_OFFLINE = "offline"
STATUS_WAITING = "waiting"
STATUS_NO_CREDENTIALS = "no_credentials"

# Check interval between individual crawlers (seconds)
CHECK_INTERVAL = 2
# Interval between full passes (seconds)
FULL_PASS_INTERVAL = 7200

_status: Dict[str, str] = {}
_checker_task: Optional[asyncio.Task] = None


def get_all_status() -> Dict[str, str]:
    return dict(_status)


def _get_login_kwargs(crawler: CrawlerInfo) -> Optional[Dict[str, str]]:
    """Get login kwargs for requires_login crawlers. Returns None if credentials unavailable."""
    if not crawler.meta.requires_login:
        return {}
    username = os.environ.get("VJUDGE_USERNAME")
    password = os.environ.get("VJUDGE_PASSWORD")
    if username and password:
        return {"login_user": username, "login_password": password}
    return None


async def _check_one(client: aiohttp.ClientSession, name: str, crawler: CrawlerInfo) -> str:
    """Check a single crawler's availability. Returns status string."""
    kwargs = _get_login_kwargs(crawler)
    if kwargs is None:
        return STATUS_NO_CREDENTIALS

    test_user = crawler.meta.test_username
    if not test_user:
        return STATUS_OFFLINE

    try:
        result = await run_crawler(client, crawler, test_user, **kwargs)
        return STATUS_ONLINE if result.success else STATUS_OFFLINE
    except Exception:
        logger.exception("Error checking crawler %s", name)
        return STATUS_OFFLINE


async def _checker_loop(client: aiohttp.ClientSession) -> None:
    """Background loop that checks crawlers one by one."""
    crawlers = discover_crawlers()

    # Initialize all to waiting
    for name in crawlers:
        _status[name] = STATUS_WAITING

    while True:
        for name, crawler in crawlers.items():
            _status[name] = STATUS_WAITING
            try:
                _status[name] = await _check_one(client, name, crawler)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Unexpected error in checker loop for %s", name)
                _status[name] = STATUS_OFFLINE
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
