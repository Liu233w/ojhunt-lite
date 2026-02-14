"""
OJHunt Lite Crawlers Package

This package contains async crawlers for various Online Judge platforms.
Each crawler is self-contained and follows a consistent interface.
All crawlers are async functions that can be awaited.
"""

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, Callable, Any, Awaitable

__all__ = ["discover_crawlers", "get_crawler", "list_crawlers"]


def discover_crawlers() -> Dict[str, Dict[str, Any]]:
    """
    Auto-discover all crawlers in the package.

    Returns:
        Dictionary mapping crawler names to their metadata and query function.
        Format: {
            'crawler_name': {
                'meta': {...},  # __crawler_meta__ from the module
                'query': callable  # async query function
            }
        }
    """
    crawlers = {}
    package_dir = Path(__file__).parent

    # Iterate through all Python files in the package
    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        # Skip test files and internal modules
        if (
            module_name.startswith("test_")
            or module_name.endswith("_test")
            or module_name.startswith("_")
        ):
            continue

        try:
            # Import the module
            module = importlib.import_module(f".{module_name}", package="crawlers")

            # Check if it has the required attributes
            if hasattr(module, "query") and hasattr(module, "__crawler_meta__"):
                crawlers[module_name] = {
                    "meta": module.__crawler_meta__,
                    "query": module.query,
                }
        except (ImportError, AttributeError) as e:
            # Skip modules that can't be imported or don't have required attributes
            print(f"Warning: Could not load crawler '{module_name}': {e}")
            continue

    return crawlers


def get_crawler(name: str) -> Callable[[str], Awaitable[Dict[str, Any]]]:
    """
    Get a specific crawler's query function by name.

    Args:
        name: The crawler name (e.g., 'codeforces', 'poj')

    Returns:
        The async query function that takes a username and returns results

    Raises:
        ValueError: If the crawler doesn't exist
    """
    crawlers = discover_crawlers()
    if name not in crawlers:
        available = ", ".join(sorted(crawlers.keys()))
        raise ValueError(f"Crawler '{name}' not found. Available: {available}")

    return crawlers[name]["query"]


def list_crawlers() -> Dict[str, str]:
    """
    Get a list of all available crawlers with their titles.

    Returns:
        Dictionary mapping crawler names to their display titles
    """
    crawlers = discover_crawlers()
    return {name: info["meta"].get("title", name) for name, info in crawlers.items()}
