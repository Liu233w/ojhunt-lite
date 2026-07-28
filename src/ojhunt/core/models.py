"""
Core models for OJHunt Lite.

These types are used across CLI, web, and crawler modules.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

import aiohttp


class LoginType(Enum):
    NOT_REQUIRED = "not_required"
    OWN_ACCOUNT = "own_account"  # Must log in as the target user
    SHARED_ACCOUNT = "shared_account"  # Any shared account can query any user

    @classmethod
    def from_meta(cls, value: Optional[str]) -> "LoginType":
        if not value:
            return cls.NOT_REQUIRED
        return cls(value)

    @property
    def label(self) -> str:
        return {
            LoginType.NOT_REQUIRED: "-",
            LoginType.OWN_ACCOUNT: "Own Account",
            LoginType.SHARED_ACCOUNT: "Shared Account",
        }[self]


@dataclass
class CrawlerResult:
    """Typed result returned by crawler query functions."""

    solved: int
    submissions: int
    solved_list: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CrawlerResult":
        return cls(
            solved=d["solved"],
            submissions=d["submissions"],
            solved_list=d.get("solved_list"),
        )


@dataclass
class CrawlerMeta:
    """Metadata for a crawler."""

    title: str
    description: str = ""
    cli_description: str = ""
    url: str = ""
    is_aggregator: bool = False
    login_type: LoginType = LoginType.NOT_REQUIRED
    test_username: str = ""


@dataclass
class CrawlerInfo:
    """A crawler with metadata and query function."""

    name: str
    meta: CrawlerMeta
    query: Callable[..., Awaitable[CrawlerResult]]


class CrawlerRegistry(Dict[str, CrawlerInfo]):
    """Every crawler in this build, keyed by name.

    This is a dict, so anything a dict does works — iteration, len(),
    .items(), `"cses" in registry`, registry["cses"]. Crawlers are reachable as
    attributes too, which reads better at a prompt and tab-completes:

        from ojhunt.crawlers import crawlers

        crawlers["codeforces"]      # by key
        crawlers.codeforces         # the same object, as an attribute
        help(crawlers.cses)         # what CSES queries, and what it needs

    Prefer the subscript form in code a type checker reads: attribute names are
    only known at runtime. An attribute that is not a crawler raises
    AttributeError; because __dir__ lists the crawler names, Python appends its
    own "Did you mean" suggestion when the miss looks like a typo.

    copy() and `|` hand back a registry, so a filtered or extended copy keeps
    attribute access. Only dict(registry) drops it, as an explicit conversion
    should.
    """

    def __getattr__(self, name: str) -> CrawlerInfo:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"no crawler named {name!r}") from None

    def __dir__(self) -> List[str]:
        return [*super().__dir__(), *self]

    def copy(self) -> "CrawlerRegistry":
        return CrawlerRegistry(self)

    def __or__(self, other: Dict[str, CrawlerInfo]) -> "CrawlerRegistry":
        return CrawlerRegistry({**self, **other})

    def __ror__(self, other: Dict[str, CrawlerInfo]) -> "CrawlerRegistry":
        return CrawlerRegistry({**other, **self})


@dataclass
class QueryResult:
    """Result of querying a crawler."""

    crawler: CrawlerInfo
    username: str
    success: bool
    solved: int = 0
    submissions: int = 0
    solved_list: Optional[List[str]] = None
    duration: float = 0.0
    error: Optional[str] = None


class NullCrawler(CrawlerInfo):
    """A null crawler for unknown crawler names."""

    def __init__(self, name: str):
        super().__init__(
            name=name,
            meta=CrawlerMeta(title=name),
            query=self._null_query,
        )

    async def _null_query(
        self, session: aiohttp.ClientSession, username: str
    ) -> CrawlerResult:
        raise RuntimeError("NullCrawler cannot execute queries")
