"""Unit tests for query_sync and the CrawlerInfo.query_sync shorthand.

No network: the stub queries below ignore the session they are handed.
"""

import pytest

from ojhunt.core.models import CrawlerInfo, CrawlerMeta, CrawlerResult
from ojhunt.crawlers import query_sync

RAW = {"solved": 3, "submissions": 5, "solved_list": ["1A", "2B"]}


async def _query_returning_dict(session, username, **kwargs):
    return dict(RAW, solved=len(username))


async def _query_returning_result(session, username, **kwargs):
    return CrawlerResult.from_dict(dict(RAW, solved=len(username)))


def _crawler(query):
    return CrawlerInfo(name="demo", meta=CrawlerMeta(title="Demo"), query=query)


def test_a_bare_query_function_still_works():
    result = query_sync(_query_returning_dict, "alice")

    assert isinstance(result, CrawlerResult)
    assert (result.solved, result.submissions) == (5, 5)
    assert result.solved_list == ["1A", "2B"]


def test_a_crawler_info_can_be_passed_instead_of_its_query():
    assert query_sync(_crawler(_query_returning_dict), "alice").solved == 5


def test_an_already_built_result_is_passed_through():
    assert query_sync(_query_returning_result, "alice").solved == 5
    assert query_sync(_crawler(_query_returning_result), "bob").solved == 3


def test_the_shorthand_queries_the_crawler():
    result = _crawler(_query_returning_result).query_sync("alice")

    assert isinstance(result, CrawlerResult)
    assert result.solved == 5


def test_credentials_reach_the_query_function():
    seen = {}

    async def query(session, username, password=None, login_user=None):
        seen.update(username=username, password=password, login_user=login_user)
        return RAW

    _crawler(query).query_sync("alice", password="pw", login_user="shared")

    assert seen == {"username": "alice", "password": "pw", "login_user": "shared"}


def test_a_crawler_name_is_not_a_crawler():
    with pytest.raises(TypeError, match="needs a lookup first"):
        query_sync("codeforces", "tourist")


def test_a_query_returning_neither_shape_names_what_it_gave_back():
    async def query(session, username, **kwargs):
        return 5, 5, None

    with pytest.raises(TypeError, match="returned tuple"):
        _crawler(query).query_sync("alice")


def test_an_error_from_the_crawler_propagates():
    async def query(session, username, **kwargs):
        raise ValueError("no such user")

    with pytest.raises(ValueError, match="no such user"):
        _crawler(query).query_sync("nobody")
