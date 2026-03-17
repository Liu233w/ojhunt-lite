"""
Unit tests for cli/output.py
"""

from cli.models import Query
from cli.output import (
    check_duplicate_queries,
    validate_crawlers,
    validate_credentials,
)
from cli.parser import build_all_queries
from core.models import CrawlerInfo, CrawlerMeta, QueryResult
from core.stats import collect_solved_problems


def make_crawler(name: str, **meta_kwargs) -> CrawlerInfo:
    """Helper to create CrawlerInfo for testing."""

    async def _dummy_query():
        return {}

    meta_kwargs.setdefault("title", name)
    return CrawlerInfo(name=name, meta=CrawlerMeta(**meta_kwargs), query=_dummy_query)


class TestBuildAllQueries:
    """Tests for build_all_queries function."""

    def test_build_all_queries(self):
        """Test building queries for all crawlers."""
        crawlers = {
            "codeforces": make_crawler("codeforces", title="CodeForces"),
            "poj": make_crawler("poj", title="POJ"),
            "hdu": make_crawler("hdu", title="HDU"),
        }
        result = build_all_queries("tourist", crawlers)
        assert len(result) == 3
        assert all(q.username == "tourist" for q in result)
        assert set(q.crawler for q in result) == {"codeforces", "poj", "hdu"}

    def test_build_all_queries_empty(self):
        """Test with empty crawlers dict."""
        result = build_all_queries("user", {})
        assert result == []

    def test_build_all_queries_order(self):
        """Test that order is preserved from dict keys."""
        crawlers = {
            "a": make_crawler("a"),
            "b": make_crawler("b"),
            "c": make_crawler("c"),
        }
        result = build_all_queries("user", crawlers)
        assert [q.crawler for q in result] == ["a", "b", "c"]


class TestCheckDuplicateQueries:
    """Tests for check_duplicate_queries function."""

    def test_no_duplicates(self, capsys):
        """Test that no warning is printed for unique queries."""
        queries = [
            Query(crawler="codeforces", username="user1"),
            Query(crawler="poj", username="user2"),
        ]
        check_duplicate_queries(queries)
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_single_duplicate(self, capsys):
        """Test warning for a single duplicate query."""
        queries = [
            Query(crawler="codeforces", username="user1"),
            Query(crawler="codeforces", username="user1"),
        ]
        check_duplicate_queries(queries)
        captured = capsys.readouterr()
        assert "Warning: duplicate query 'user1@codeforces'" in captured.err
        assert "will run 2 times" in captured.err

    def test_multiple_duplicates(self, capsys):
        """Test warnings for multiple duplicate queries."""
        queries = [
            Query(crawler="codeforces", username="user1"),
            Query(crawler="codeforces", username="user1"),
            Query(crawler="poj", username="user2"),
            Query(crawler="poj", username="user2"),
        ]
        check_duplicate_queries(queries)
        captured = capsys.readouterr()
        assert "user1@codeforces" in captured.err
        assert "user2@poj" in captured.err

    def test_triple_duplicate(self, capsys):
        """Test count is correct for triple duplicates."""
        queries = [
            Query(crawler="codeforces", username="user1"),
            Query(crawler="codeforces", username="user1"),
            Query(crawler="codeforces", username="user1"),
        ]
        check_duplicate_queries(queries)
        captured = capsys.readouterr()
        assert "will run 3 times" in captured.err

    def test_empty_list(self, capsys):
        """Test with empty query list."""
        check_duplicate_queries([])
        captured = capsys.readouterr()
        assert captured.err == ""


class TestValidateCrawlers:
    """Tests for validate_crawlers function."""

    def test_all_valid(self):
        """Test with all valid crawlers."""
        queries = [
            Query(crawler="codeforces", username="user1"),
            Query(crawler="poj", username="user2"),
        ]
        crawlers = {
            "codeforces": make_crawler("codeforces"),
            "poj": make_crawler("poj"),
        }
        assert validate_crawlers(queries, crawlers) is True

    def test_unknown_crawler(self, capsys):
        """Test with unknown crawler."""
        queries = [
            Query(crawler="codeforces", username="user1"),
            Query(crawler="unknown", username="user2"),
        ]
        crawlers = {
            "codeforces": make_crawler("codeforces"),
        }
        assert validate_crawlers(queries, crawlers) is False
        captured = capsys.readouterr()
        assert "unknown crawler(s): unknown" in captured.err

    def test_multiple_unknown_crawlers(self, capsys):
        """Test with multiple unknown crawlers (sorted in output)."""
        queries = [
            Query(crawler="zebra", username="user1"),
            Query(crawler="alpha", username="user2"),
        ]
        crawlers = {"codeforces": make_crawler("codeforces")}
        assert validate_crawlers(queries, crawlers) is False
        captured = capsys.readouterr()
        assert "unknown crawler(s): alpha, zebra" in captured.err

    def test_empty_queries(self):
        """Test with empty query list."""
        crawlers = {"codeforces": make_crawler("codeforces")}
        assert validate_crawlers([], crawlers) is True

    def test_empty_crawlers(self):
        """Test with empty crawlers dict and no queries."""
        assert validate_crawlers([], {}) is True


class TestValidateCredentials:
    """Tests for validate_credentials function."""

    def test_no_auth_required(self):
        """Test crawler that doesn't require authentication."""
        queries = [Query(crawler="codeforces", username="user1")]
        crawlers = {"codeforces": make_crawler("codeforces")}
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is True

    def test_requires_login_with_embedded_password(self):
        """Test requires_login crawler with embedded password."""
        queries = [Query(crawler="vjudge", username="user1", password="pass")]
        crawlers = {"vjudge": make_crawler("vjudge", requires_login=True)}
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is True

    def test_requires_login_with_flag_credentials(self):
        """Test requires_login crawler with -l flag credentials."""
        queries = [Query(crawler="vjudge", username="user1")]
        crawlers = {"vjudge": make_crawler("vjudge", requires_login=True)}
        crawler_logins = {"vjudge": ("loginuser", "pass")}
        assert validate_credentials(queries, crawlers, crawler_logins) is True

    def test_requires_login_missing_credentials(self, capsys):
        """Test requires_login crawler without any credentials."""
        queries = [Query(crawler="vjudge", username="user1")]
        crawlers = {"vjudge": make_crawler("vjudge", requires_login=True)}
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is False
        captured = capsys.readouterr()
        assert "requires login credentials" in captured.err

    def test_requires_login_duplicate_credentials(self, capsys):
        """Test requires_login crawler with both embedded and flag credentials."""
        queries = [Query(crawler="vjudge", username="user1", password="pass")]
        crawlers = {"vjudge": make_crawler("vjudge", requires_login=True)}
        crawler_logins = {"vjudge": ("loginuser", "pass2")}
        assert validate_credentials(queries, crawlers, crawler_logins) is False
        captured = capsys.readouterr()
        assert "duplicate credentials" in captured.err

    def test_requires_password_provided(self):
        """Test requires_password crawler with password provided."""
        queries = [Query(crawler="someoj", username="user1", password="pass")]
        crawlers = {"someoj": make_crawler("someoj", requires_password=True)}
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is True

    def test_requires_password_missing(self, capsys):
        """Test requires_password crawler without password."""
        queries = [Query(crawler="someoj", username="user1")]
        crawlers = {"someoj": make_crawler("someoj", requires_password=True)}
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is False
        captured = capsys.readouterr()
        assert "requires a password" in captured.err

    def test_unwanted_password_in_query(self, capsys):
        """Test crawler that doesn't require auth but password provided."""
        queries = [Query(crawler="codeforces", username="user1", password="pass")]
        crawlers = {"codeforces": make_crawler("codeforces")}
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is False
        captured = capsys.readouterr()
        assert "does not require credentials" in captured.err

    def test_empty_queries(self):
        """Test with empty query list."""
        crawlers = {"codeforces": make_crawler("codeforces")}
        crawler_logins = {}
        assert validate_credentials([], crawlers, crawler_logins) is True

    def test_multiple_queries_mixed(self):
        """Test multiple queries with different auth requirements."""
        queries = [
            Query(crawler="codeforces", username="user1"),
            Query(crawler="vjudge", username="user2", password="pass"),
        ]
        crawlers = {
            "codeforces": make_crawler("codeforces"),
            "vjudge": make_crawler("vjudge", requires_login=True),
        }
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is True


def make_result(
    crawler_name: str, success: bool, solved_list: list, **meta_kwargs
) -> QueryResult:
    """Helper to create QueryResult for testing."""
    crawler = make_crawler(crawler_name, **meta_kwargs)
    return QueryResult(
        crawler=crawler,
        username="testuser",
        success=success,
        solved=0,
        submissions=0,
        solved_list=solved_list,
    )


class TestCollectSolvedProblems:
    """Tests for collect_solved_problems function."""

    def test_normal_crawler_prefix(self):
        """Test that normal crawlers get prefixed with crawler name."""
        results = [
            make_result("hdu", True, ["1000", "1001", "1002"]),
        ]
        solved = collect_solved_problems(results)
        assert solved == {"hdu-1000", "hdu-1001", "hdu-1002"}

    def test_virtual_judge_no_prefix(self):
        """Test that virtual judges use labels as-is."""
        results = [
            make_result(
                "vjudge", True, ["codeforces-123A", "poj-1000"], is_virtual_judge=True
            ),
        ]
        solved = collect_solved_problems(results)
        assert solved == {"codeforces-123A", "poj-1000"}

    def test_mixed_crawlers(self):
        """Test mix of normal and virtual judges."""
        results = [
            make_result("hdu", True, ["1000"]),
            make_result("vjudge", True, ["codeforces-123A"], is_virtual_judge=True),
        ]
        solved = collect_solved_problems(results)
        assert solved == {"hdu-1000", "codeforces-123A"}

    def test_deduplication(self):
        """Test that duplicates are removed."""
        results = [
            make_result("hdu", True, ["1000", "1001"]),
            make_result("hdu", True, ["1000", "1002"]),
        ]
        solved = collect_solved_problems(results)
        assert solved == {"hdu-1000", "hdu-1001", "hdu-1002"}

    def test_failed_result_ignored(self):
        """Test that failed results are ignored."""
        results = [
            make_result("hdu", True, ["1000"]),
            make_result("poj", False, ["1001"]),
        ]
        solved = collect_solved_problems(results)
        assert solved == {"hdu-1000"}

    def test_empty_results(self):
        """Test with empty results list."""
        solved = collect_solved_problems([])
        assert solved == set()

    def test_empty_solved_list(self):
        """Test with empty solved_list in result."""
        results = [
            make_result("hdu", True, []),
        ]
        solved = collect_solved_problems(results)
        assert solved == set()
