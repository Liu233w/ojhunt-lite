"""
Shared HTTP client for web application.
"""

from typing import Annotated

import aiohttp
from fastapi import Depends

_CLIENT: aiohttp.ClientSession


def init_http_client() -> None:
    global _CLIENT
    _CLIENT = aiohttp.ClientSession()


async def get_http_client() -> aiohttp.ClientSession:
    return _CLIENT


async def close_http_client() -> None:
    global _CLIENT
    await _CLIENT.close()


HttpClientDep = Annotated[aiohttp.ClientSession, Depends(get_http_client)]
