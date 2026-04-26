"""
Pytest configuration and fixtures.
"""

import os
from pathlib import Path

import aiohttp
import pytest
import pytest_asyncio
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

_DB_PATH = Path(__file__).parent.parent.parent / "problem_labels.db"


@pytest.fixture(autouse=True)
def clean_problem_labels_db():
    if _DB_PATH.exists():
        os.remove(_DB_PATH)
    yield
    if _DB_PATH.exists():
        os.remove(_DB_PATH)


@pytest_asyncio.fixture
async def session():
    async with aiohttp.ClientSession(trust_env=True) as s:
        yield s
