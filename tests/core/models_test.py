"""Unit tests for core/models.py — CrawlerRegistry attribute access."""

import pytest

from ojhunt.core.models import (
    CrawlerInfo,
    CrawlerMeta,
    CrawlerRegistry,
    CrawlerResult,
    NullCrawler,
)
from ojhunt.crawlers import crawlers as crawler_registry


def _registry(*names):
    return CrawlerRegistry(
        {
            name: CrawlerInfo(
                name=name, meta=CrawlerMeta(title=name.upper()), query=None
            )
            for name in names
        }
    )


def test_repr_names_the_actual_class():
    crawler = CrawlerInfo(name="cf", meta=CrawlerMeta(title="CF"), query=None)

    assert repr(crawler) == '<CrawlerInfo cf "CF" login=not_required>'
    assert repr(NullCrawler("bogus")).startswith("<NullCrawler bogus"), (
        "an unknown crawler must not read as a real one"
    )


def test_attribute_access_returns_the_same_object_as_the_key():
    registry = _registry("aizu", "codeforces")
    assert registry.aizu is registry["aizu"]


def test_registry_is_still_a_dict():
    registry = _registry("aizu", "codeforces")

    assert isinstance(registry, dict)
    assert len(registry) == 2
    assert "aizu" in registry
    assert sorted(registry) == ["aizu", "codeforces"]
    assert [name for name, _ in registry.items()] == ["aizu", "codeforces"]


def test_a_derived_registry_keeps_attribute_access():
    registry = _registry("aizu", "codeforces")
    extra = _registry("cses")

    assert registry.copy().aizu is registry["aizu"]
    assert (registry | extra).cses is extra["cses"]
    assert (extra | registry).aizu is registry["aizu"]
    assert type(dict(registry)) is dict, "an explicit conversion may drop it"


def test_coerce_takes_either_shape_and_rejects_the_rest():
    built = CrawlerResult(solved=1, submissions=2)

    assert CrawlerResult.coerce(built) is built
    assert CrawlerResult.coerce({"solved": 1, "submissions": 2}) == built
    with pytest.raises(TypeError, match="returned tuple"):
        CrawlerResult.coerce((1, 2))


def test_unknown_attribute_raises_attribute_error():
    registry = _registry("aizu")

    with pytest.raises(AttributeError, match="no crawler named 'nope'"):
        registry.nope


def test_a_near_miss_carries_the_data_python_suggests_from():
    """Python's own "Did you mean" reads dir(obj), so the names must be listed."""
    registry = _registry("codeforces")

    with pytest.raises(AttributeError) as excinfo:
        registry.codefroces

    assert excinfo.value.name == "codefroces"
    assert "codeforces" in dir(excinfo.value.obj)


def test_dir_lists_crawler_names_for_tab_completion():
    registry = _registry("aizu", "codeforces")

    listed = dir(registry)
    assert "aizu" in listed
    assert "codeforces" in listed
    assert "items" in listed, "dict's own attributes must survive"


def test_no_crawler_name_shadows_a_dict_attribute():
    """A crawler called `items` or `get` would be unreachable as an attribute."""
    shadowed = [name for name in crawler_registry if hasattr(dict, name)]
    assert shadowed == []


def test_every_crawler_is_reachable_as_an_attribute():
    for name, crawler in crawler_registry.items():
        assert getattr(crawler_registry, name) is crawler
