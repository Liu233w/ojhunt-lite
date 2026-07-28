"""Unit tests for the generated library documentation (see ADR 0014)."""

import importlib.util
import pydoc
from pathlib import Path

import ojhunt.crawlers
from ojhunt.core.models import CrawlerMeta, LoginType
from ojhunt.crawlers import crawlers as CRAWLERS
from ojhunt.crawlers._help import compose_query_doc, render_crawler_doc

REPO_ROOT = Path(__file__).parents[2]


def _plain(thing):
    """Render help() output without pydoc's backspace-bolding."""
    return pydoc.render_doc(thing, renderer=pydoc.plaintext)


def _generator():
    """Import scripts/generate_library_docs.py, which is outside the package."""
    path = REPO_ROOT / "scripts" / "generate_library_docs.py"
    spec = importlib.util.spec_from_file_location("generate_library_docs", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_library_md_is_what_the_generator_produces_now():
    generator = _generator()

    assert generator.render_library_docs() == generator.OUTPUT.read_text(
        encoding="utf-8"
    ), "docs/library.md is stale — run ./doit.sh gen-docs and commit the result"


def test_public_api_is_importable():
    for name in ojhunt.crawlers.__all__:
        assert hasattr(ojhunt.crawlers, name), name


def test_package_docstring_documents_library_usage():
    doc = ojhunt.crawlers.__doc__
    for expected in [
        "from ojhunt.crawlers import crawlers",
        "help(crawlers.cses)",
        "query_sync",
        "CrawlerResult",
        "login_user",
    ]:
        assert expected in doc, expected


def test_every_crawler_has_generated_doc():
    for name, crawler in CRAWLERS.items():
        doc = crawler.__doc__
        assert doc, name
        assert crawler.meta.title in doc, name
        assert crawler.meta.url in doc, name
        assert f"from ojhunt.crawlers.{name} import query" in doc, name


def test_every_crawler_doc_states_the_login_requirement():
    for name, crawler in CRAWLERS.items():
        doc = crawler.__doc__
        if crawler.meta.login_type is LoginType.NOT_REQUIRED:
            assert "Login: not required." in doc, name
        else:
            assert "Login: required" in doc, name
            assert "login_user" in doc or "password" in doc, name


def test_aggregator_docs_mention_the_source_prefix():
    aggregators = [c for c in CRAWLERS.values() if c.meta.is_aggregator]
    assert aggregators, "expected at least one aggregator crawler"
    for crawler in aggregators:
        assert "Aggregator:" in crawler.__doc__, crawler.name
        assert "prefix" in crawler.__doc__, crawler.name


def test_every_raw_query_function_is_documented():
    undocumented = []
    for name in CRAWLERS:
        module = importlib.import_module(f"ojhunt.crawlers.{name}")
        if not (module.query.__doc__ or "").strip():
            undocumented.append(name)
    assert undocumented == [], (
        "help() joins the query docstring to the generated text (ADR 0014), "
        "so every query needs one — see the templates in docs/dev/crawlers.md"
    )


def test_help_on_a_crawler_shows_its_documentation():
    rendered = _plain(CRAWLERS["cses"])
    assert '<CrawlerInfo cses "CSES" login=shared_account>' in rendered
    assert "CSES — https://cses.fi/" in rendered
    assert "Login: required, any account." in rendered
    assert "LOGIN_USERNAME__CSES" in rendered
    assert "query(session, username, password, login_user, login_password)" in rendered
    assert 'crawlers.cses.query_sync("3", login_user="..."' in rendered


def test_help_on_a_crawler_query_keeps_the_signature_and_adds_usage():
    rendered = _plain(CRAWLERS["codeforces"].query)
    assert "async query(session:" in rendered, "functools.wraps keeps the signature"
    assert "Query CodeForces for user statistics." in rendered
    assert "CodeForces — http://codeforces.com/" in rendered
    assert 'query_sync(query, "leoloveacm")' in rendered


def test_generated_docs_do_not_touch_the_crawler_module():
    module = importlib.import_module("ojhunt.crawlers.codeforces")
    assert "Login: not required." not in (module.query.__doc__ or ""), (
        "only the wrapper gains generated text"
    )
    assert module.__doc__.lstrip().startswith("BSD 2-Clause License")


def test_render_crawler_doc_uses_the_test_username_in_the_example():
    meta = CrawlerMeta(title="Demo", url="https://demo.test/", test_username="alice")
    doc = render_crawler_doc("demo", meta, lambda session, username: None)

    assert doc.startswith("Demo — https://demo.test/")
    assert "Login: not required." in doc
    assert "Call: query(session, username)" in doc
    assert 'crawlers.demo.query_sync("alice")' in doc, "registry shorthand"
    assert 'query_sync(query, "alice")' in doc, "form a copied file can use"


def test_render_crawler_doc_explains_own_account_login():
    meta = CrawlerMeta(
        title="Demo", url="https://demo.test/", login_type=LoginType.OWN_ACCOUNT
    )

    def query(session, username, password=None):
        return None

    doc = render_crawler_doc("demo", meta, query)

    assert "Login: required, as the user being queried." in doc
    assert 'password="..."' in doc
    assert "LOGIN_USERNAME__DEMO" not in doc


def test_a_shared_account_crawler_taking_only_a_password_says_so():
    meta = CrawlerMeta(
        title="Demo", url="https://demo.test/", login_type=LoginType.SHARED_ACCOUNT
    )

    def query(session, username, password=None):
        return None

    doc = render_crawler_doc("demo", meta, query)

    assert "Login: required, any account." in doc
    assert "Pass password." in doc
    assert "LOGIN_USERNAME__DEMO" not in doc, (
        "get_login_kwargs() only ever passes login_user/login_password"
    )


def test_compose_query_doc_dedents_and_separates():
    raw = """
    Query Demo.

    Args:
        username: A name
    """
    combined = compose_query_doc(raw, "Demo — https://demo.test/\n")

    assert combined.startswith("Query Demo.\n")
    assert "\n    username: A name" in combined
    assert "\nDemo — https://demo.test/" in combined


def test_compose_query_doc_handles_a_missing_docstring():
    assert compose_query_doc(None, "generated") == "generated"
    assert compose_query_doc("   ", "generated") == "generated"
