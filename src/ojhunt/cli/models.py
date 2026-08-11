"""
CLI models for OJHunt Lite.
"""

from dataclasses import dataclass


@dataclass
class Query:
    """Represents a query for a crawler with a specific username."""

    crawler: str
    username: str
    password: str | None = None
