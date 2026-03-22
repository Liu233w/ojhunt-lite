"""
OJHunt Lite Crawlers Package

This package contains async crawlers for various Online Judge platforms.
Each crawler is self-contained and follows a consistent interface.
All crawlers are async functions that can be awaited.
"""

import importlib
import pkgutil
from functools import cache
from pathlib import Path
from typing import Dict

from core.models import CrawlerInfo, CrawlerMeta

__all__ = ["discover_crawlers"]


@cache
def discover_crawlers() -> Dict[str, CrawlerInfo]:
    """
    Auto-discover all crawlers in the package.

    Returns:
        Dictionary mapping crawler names to CrawlerInfo objects.
    """
    crawlers: Dict[str, CrawlerInfo] = {}
    package_dir = Path(__file__).parent

    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        if (
            module_name.startswith("test_")
            or module_name.endswith("_test")
            or module_name.startswith("_")
            or module_name == "conftest"
        ):
            continue

        try:
            module = importlib.import_module(f".{module_name}", package="crawlers")

            if hasattr(module, "query") and hasattr(module, "__crawler_meta__"):
                meta_dict = module.__crawler_meta__
                meta = CrawlerMeta(
                    title=meta_dict.get("title", module_name),
                    description=meta_dict.get("description", ""),
                    url=meta_dict.get("url", ""),
                    is_virtual_judge=meta_dict.get("is_virtual_judge", False),
                    requires_login=meta_dict.get("requires_login", False),
                    requires_password=meta_dict.get("requires_password", False),
                    test_username=meta_dict.get("test_username", ""),
                )
                crawlers[module_name] = CrawlerInfo(
                    name=module_name,
                    meta=meta,
                    query=module.query,
                )
        except (ImportError, AttributeError) as e:
            print(f"Warning: Could not load crawler '{module_name}': {e}")
            continue

    return crawlers
