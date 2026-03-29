"""
Pytest configuration and fixtures.
"""

import os
from pathlib import Path

import pytest

_DB_PATH = Path(__file__).parent.parent.parent / "problem_labels.db"


@pytest.fixture(autouse=True)
def clean_problem_labels_db():
    if _DB_PATH.exists():
        os.remove(_DB_PATH)
    yield
    if _DB_PATH.exists():
        os.remove(_DB_PATH)
