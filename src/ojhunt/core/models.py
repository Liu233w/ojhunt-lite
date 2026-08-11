"""
Core models for OJHunt Lite.

These types are used across CLI, web, and crawler modules.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

import aiohttp


class LoginType(Enum):
    """Whether a crawler needs credentials, and whose.

    NOT_REQUIRED
        Profiles are public; pass nothing.
    OWN_ACCOUNT
        The judge only shows the logged-in user's own statistics, so the
        credentials must belong to the user being queried.
    SHARED_ACCOUNT
        The judge hides profiles from guests, but any authenticated account can
        look up any user, so one shared account serves every query.
    """

    NOT_REQUIRED = "not_required"
    OWN_ACCOUNT = "own_account"  # Must log in as the target user
    SHARED_ACCOUNT = "shared_account"  # Any shared account can query any user

    @classmethod
    def from_meta(cls, value: str | None) -> "LoginType":
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
    """Typed result returned by crawler query functions.

    Attributes:
        solved: Number of accepted problems.
        submissions: Total submissions, as the crawler reports them.
        solved_list: IDs of the solved problems, or None if the judge does not
            publish them.
    """

    solved: int
    submissions: int
    solved_list: list[str] | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CrawlerResult":
        """Build a CrawlerResult from the raw dict a crawler's query returns.

        Args:
            d: Dict with keys solved, submissions and optionally solved_list.

        Returns:
            The equivalent CrawlerResult.

        Raises:
            KeyError: If solved or submissions is missing.
        """
        return cls(
            solved=d["solved"],
            submissions=d["submissions"],
            solved_list=d.get("solved_list"),
        )

    @classmethod
    def coerce(cls, result: Any) -> "CrawlerResult":
        """Build a CrawlerResult from whatever a query function returned.

        Crawler modules return the raw dict their own docstring describes, but a
        query function is free to build the result itself, so accept both.

        Args:
            result: A raw crawler dict, or an already-built CrawlerResult.

        Returns:
            The equivalent CrawlerResult.

        Raises:
            TypeError: If the query function returned neither.
            KeyError: If a dict is missing solved or submissions.
        """
        if isinstance(result, cls):
            return result
        if not isinstance(result, dict):
            raise TypeError(
                f"query function returned {type(result).__name__}, "
                "expected a dict or a CrawlerResult"
            )
        return cls.from_dict(result)


@dataclass
class CrawlerMeta:
    """Metadata for a crawler, parsed from its __crawler_meta__ dict.

    Attributes:
        title: Display name of the online judge.
        description: What a user should type as the username, when that needs
            explaining.
        cli_description: Replaces description in `ojhunt --list` when CLI usage
            differs, e.g. login instructions.
        url: Homepage of the judge.
        is_aggregator: Whether the judge mirrors problems from other judges, in
            which case solved_list entries carry a source prefix.
        login_type: Whether credentials are needed, and whose.
        test_username: A username known to exist, used by tests and the
            /crawlers availability check.
    """

    title: str
    description: str = ""
    cli_description: str = ""
    url: str = ""
    is_aggregator: bool = False
    login_type: LoginType = LoginType.NOT_REQUIRED
    test_username: str = ""


@dataclass
class CrawlerInfo:
    """A crawler with metadata and query function.

    Discovery fills each instance's __doc__ with generated documentation, so
    help() on a CrawlerInfo describes that specific crawler.

    query_sync() blocks until the judge answers, which makes
    crawlers.codeforces.query_sync("tourist") the shortest way to one result.

    Attributes:
        name: Crawler name, i.e. its module basename (e.g. "codeforces").
        meta: Metadata from the crawler's __crawler_meta__.
        query: The crawler's query function, awaited as
            query(session, username, **credentials) and returning a
            CrawlerResult.
    """

    name: str
    meta: CrawlerMeta
    query: Callable[..., Awaitable[CrawlerResult]]

    def __repr__(self) -> str:
        return (
            f'<{type(self).__name__} {self.name} "{self.meta.title}" '
            f"login={self.meta.login_type.value}>"
        )

    def query_sync(self, username: str, **kwargs: Any) -> CrawlerResult:
        """Query this crawler, blocking until it answers.

        Runs its own event loop, so it cannot be called from inside a running one
        (a notebook, or any async function) — await self.query(session, username)
        there instead.

        Args:
            username: Username to query.
            **kwargs: Credentials the crawler accepts, e.g. password, or
                login_user and login_password. help() on this crawler names
                them.

        Returns:
            CrawlerResult with solved, submissions, solved_list fields.

        Raises:
            ValueError: If the username or credentials are unusable.
            RuntimeError: If the request fails or the response cannot be parsed.

        Example:
            from ojhunt.crawlers import crawlers
            result = crawlers.codeforces.query_sync("tourist")
            print(result.solved, result.submissions, result.solved_list)
        """
        # Local import: ojhunt.crawlers imports this module.
        from ojhunt.crawlers import query_sync

        return query_sync(self.query, username, **kwargs)


class CrawlerRegistry(dict[str, CrawlerInfo]):
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

    def __dir__(self) -> list[str]:
        return [*super().__dir__(), *self]

    def copy(self) -> "CrawlerRegistry":
        return CrawlerRegistry(self)

    def __or__(self, other: dict[str, CrawlerInfo]) -> "CrawlerRegistry":
        return CrawlerRegistry({**self, **other})

    def __ror__(self, other: dict[str, CrawlerInfo]) -> "CrawlerRegistry":
        return CrawlerRegistry({**other, **self})


@dataclass
class QueryResult:
    """Result of querying a crawler."""

    crawler: CrawlerInfo
    username: str
    success: bool
    solved: int = 0
    submissions: int = 0
    solved_list: list[str] | None = None
    duration: float = 0.0
    error: str | None = None


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
