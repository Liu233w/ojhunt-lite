"""
Shared HTTP client for web application.
"""

from typing import Annotated

import aiohttp
from fastapi import Depends

from ojhunt.core.session import create_session

_CLIENT: aiohttp.ClientSession


def init_http_client() -> None:
    global _CLIENT
    _CLIENT = create_session()


async def get_http_client() -> aiohttp.ClientSession:
    return _CLIENT


async def close_http_client() -> None:
    await _CLIENT.close()


HttpClientDep = Annotated[aiohttp.ClientSession, Depends(get_http_client)]
