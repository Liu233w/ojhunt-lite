"""
Unit tests for cli/output.py
"""

import json
from unittest.mock import patch

from ojhunt.cli.models import Query
from ojhunt.cli.output import (
    check_duplicate_queries,
    print_crawler_list,
    print_report,
    validate_crawlers,
    validate_credentials,
)
from ojhunt.cli.parser import build_all_queries
from ojhunt.core.models import CrawlerInfo, CrawlerMeta, LoginType, QueryResult
from ojhunt.core.stats import collect_solved_problems


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
        assert {q.crawler for q in result} == {"codeforces", "poj", "hdu"}

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
        crawlers = {
            "vjudge": make_crawler("vjudge", login_type=LoginType.SHARED_ACCOUNT)
        }
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is True

    def test_requires_login_with_flag_credentials(self):
        """Test requires_login crawler with -l flag credentials."""
        queries = [Query(crawler="vjudge", username="user1")]
        crawlers = {
            "vjudge": make_crawler("vjudge", login_type=LoginType.SHARED_ACCOUNT)
        }
        crawler_logins = {"vjudge": ("loginuser", "pass")}
        assert validate_credentials(queries, crawlers, crawler_logins) is True

    def test_requires_login_missing_credentials(self, capsys):
        """Test requires_login crawler without any credentials."""
        queries = [Query(crawler="vjudge", username="user1")]
        crawlers = {
            "vjudge": make_crawler("vjudge", login_type=LoginType.SHARED_ACCOUNT)
        }
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is False
        captured = capsys.readouterr()
        assert "requires login credentials" in captured.err

    def test_requires_login_duplicate_credentials(self, capsys):
        """Test requires_login crawler with both embedded and flag credentials."""
        queries = [Query(crawler="vjudge", username="user1", password="pass")]
        crawlers = {
            "vjudge": make_crawler("vjudge", login_type=LoginType.SHARED_ACCOUNT)
        }
        crawler_logins = {"vjudge": ("loginuser", "pass2")}
        assert validate_credentials(queries, crawlers, crawler_logins) is False
        captured = capsys.readouterr()
        assert "duplicate credentials" in captured.err

    def test_requires_password_provided(self):
        """Test requires_password crawler with password provided."""
        queries = [Query(crawler="someoj", username="user1", password="pass")]
        crawlers = {"someoj": make_crawler("someoj", login_type=LoginType.OWN_ACCOUNT)}
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is True

    def test_requires_password_missing(self, capsys):
        """Test requires_password crawler without password."""
        queries = [Query(crawler="someoj", username="user1")]
        crawlers = {"someoj": make_crawler("someoj", login_type=LoginType.OWN_ACCOUNT)}
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
            "vjudge": make_crawler("vjudge", login_type=LoginType.SHARED_ACCOUNT),
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

    def test_aggregator_no_prefix(self):
        """Test that virtual judges use labels as-is."""
        results = [
            make_result(
                "vjudge", True, ["codeforces-123A", "poj-1000"], is_aggregator=True
            ),
        ]
        solved = collect_solved_problems(results)
        assert solved == {"codeforces-123A", "poj-1000"}

    def test_mixed_crawlers(self):
        """Test mix of normal and virtual judges."""
        results = [
            make_result("hdu", True, ["1000"]),
            make_result("vjudge", True, ["codeforces-123A"], is_aggregator=True),
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


def make_full_result(
    crawler_name: str,
    success: bool,
    solved: int = 0,
    submissions: int = 0,
    solved_list=None,
    duration: float = 1.0,
    error: str | None = None,
    **meta_kwargs,
) -> QueryResult:
    """Helper to create QueryResult with all fields set."""
    crawler = make_crawler(crawler_name, **meta_kwargs)
    return QueryResult(
        crawler=crawler,
        username="testuser",
        success=success,
        solved=solved,
        submissions=submissions,
        solved_list=solved_list,
        duration=duration,
        error=error,
    )


class TestPrintReportJson:
    """Tests for print_report with json_output=True."""

    def test_json_goes_to_stdout(self, capsys):
        """Test that JSON output goes to stdout."""
        results = [make_full_result("codeforces", True, solved=10, submissions=15)]
        print_report(results, show_problems=False, total_duration=1.0, json_output=True)
        captured = capsys.readouterr()
        assert captured.out.strip() != ""
        assert captured.err == ""

    def test_json_structure(self, capsys):
        """Test top-level JSON structure has results and summary."""
        results = [make_full_result("codeforces", True, solved=10, submissions=15)]
        print_report(results, show_problems=False, total_duration=1.5, json_output=True)
        data = json.loads(capsys.readouterr().out)
        assert "results" in data
        assert "summary" in data

    def test_json_successful_result_fields(self, capsys):
        """Test a successful result has the expected fields."""
        results = [
            make_full_result(
                "codeforces",
                True,
                solved=5,
                submissions=10,
                solved_list=["1A", "2A"],
                duration=1.23,
                title="Codeforces",
            )
        ]
        print_report(
            results, show_problems=False, total_duration=1.23, json_output=True
        )
        entry = json.loads(capsys.readouterr().out)["results"][0]
        assert entry["crawler"] == "codeforces"
        assert entry["title"] == "Codeforces"
        assert entry["username"] == "testuser"
        assert entry["success"] is True
        assert entry["solved"] == 5
        assert entry["submissions"] == 10
        assert entry["solved_list"] == ["1A", "2A"]
        assert abs(entry["duration"] - 1.23) < 0.01

    def test_json_failed_result_fields(self, capsys):
        """Test a failed result has the expected fields."""
        results = [
            make_full_result("codeforces", False, error="User not found", duration=0.5)
        ]
        print_report(results, show_problems=False, total_duration=0.5, json_output=True)
        entry = json.loads(capsys.readouterr().out)["results"][0]
        assert entry["success"] is False
        assert entry["error"] == "User not found"
        assert "solved" not in entry
        assert "submissions" not in entry

    def test_json_null_solved_list(self, capsys):
        """Test that None solved_list serializes to null."""
        results = [make_full_result("codeforces", True, solved=5, solved_list=None)]
        print_report(results, show_problems=False, total_duration=1.0, json_output=True)
        entry = json.loads(capsys.readouterr().out)["results"][0]
        assert entry["solved_list"] is None

    def test_json_summary_fields(self, capsys):
        """Test summary contains correct aggregated values."""
        results = [
            make_full_result(
                "cf", True, solved=3, submissions=5, solved_list=["1A", "2A", "3A"]
            ),
            make_full_result("hdu", False, error="timeout"),
        ]
        print_report(results, show_problems=False, total_duration=2.5, json_output=True)
        summary = json.loads(capsys.readouterr().out)["summary"]
        assert summary["unique_solved"] == 3
        assert summary["total_submissions"] == 5
        assert summary["ok"] == 1
        assert summary["failed"] == 1
        assert abs(summary["duration"] - 2.5) < 0.01

    def test_json_returns_0_all_success(self, capsys):
        """Test exit code 0 when all results succeed."""
        results = [make_full_result("codeforces", True)]
        code = print_report(
            results, show_problems=False, total_duration=1.0, json_output=True
        )
        capsys.readouterr()
        assert code == 0

    def test_json_returns_1_on_failure(self, capsys):
        """Test exit code 1 when any result fails."""
        results = [make_full_result("codeforces", False, error="err")]
        code = print_report(
            results, show_problems=False, total_duration=1.0, json_output=True
        )
        capsys.readouterr()
        assert code == 1

    def test_json_show_problems_ignored(self, capsys):
        """Test that show_problems=True doesn't change JSON output."""
        results = [
            make_full_result("codeforces", True, solved=2, solved_list=["1A", "2A"])
        ]
        print_report(results, show_problems=True, total_duration=1.0, json_output=True)
        data = json.loads(capsys.readouterr().out)
        # solved_list is always in JSON regardless of show_problems
        assert data["results"][0]["solved_list"] == ["1A", "2A"]


class TestPrintReportShowProblems:
    """Tests for print_report text-mode output with show_problems=True."""

    def test_listless_crawler_shows_explanation(self, capsys):
        """Listless crawler (solved_list=None) prints a note with its solved count."""
        results = [
            make_full_result("luogu", True, solved=42, solved_list=None, title="Luogu")
        ]
        print_report(results, show_problems=True, total_duration=1.0, json_output=False)
        out = capsys.readouterr().out
        assert "Luogu (testuser): (list not available — 42 solved)" in out

    def test_crawler_with_list_prints_problems(self, capsys):
        """Crawler with a solved_list still prints the comma-joined list."""
        results = [
            make_full_result(
                "cf", True, solved=2, solved_list=["2A", "1A"], title="Codeforces"
            )
        ]
        print_report(results, show_problems=True, total_duration=1.0, json_output=False)
        out = capsys.readouterr().out
        assert "Codeforces (testuser): 1A, 2A" in out

    def test_empty_list_crawler_prints_no_problems_line(self, capsys):
        """Crawler with empty solved_list ([]) prints no per-crawler line (current behavior)."""
        results = [
            make_full_result("cf", True, solved=0, solved_list=[], title="Codeforces")
        ]
        print_report(results, show_problems=True, total_duration=1.0, json_output=False)
        out = capsys.readouterr().out
        assert "Codeforces (testuser)" not in out
        assert "list not available" not in out


class TestPrintCrawlerListJson:
    """Tests for print_crawler_list with json_output=True."""

    def _make_crawlers(self):
        return {
            "codeforces": make_crawler(
                "codeforces", title="Codeforces", url="https://codeforces.com"
            ),
            "vjudge": make_crawler(
                "vjudge",
                title="VJudge",
                url="https://vjudge.net",
                login_type=LoginType.SHARED_ACCOUNT,
            ),
        }

    def test_json_goes_to_stdout(self, capsys):
        """Test that JSON output goes to stdout."""
        with patch("ojhunt.cli.output.crawler_registry", self._make_crawlers()):
            print_crawler_list(json_output=True)
        captured = capsys.readouterr()
        assert captured.out.strip() != ""
        assert captured.err == ""

    def test_json_is_dict(self, capsys):
        """Test that JSON output is a dict keyed by crawler name."""
        with patch("ojhunt.cli.output.crawler_registry", self._make_crawlers()):
            print_crawler_list(json_output=True)
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, dict)

    def test_json_entry_fields(self, capsys):
        """Test each entry has the expected fields."""
        with patch("ojhunt.cli.output.crawler_registry", self._make_crawlers()):
            print_crawler_list(json_output=True)
        data = json.loads(capsys.readouterr().out)
        entry = data["codeforces"]
        assert entry["title"] == "Codeforces"
        assert entry["url"] == "https://codeforces.com"
        assert entry["login_type"] == "not_required"
        assert entry["is_aggregator"] is False
        assert "description" in entry
        assert "name" not in entry

    def test_json_requires_login_field(self, capsys):
        """Test requires_login is correctly set for login crawlers."""
        with patch("ojhunt.cli.output.crawler_registry", self._make_crawlers()):
            print_crawler_list(json_output=True)
        data = json.loads(capsys.readouterr().out)
        assert data["vjudge"]["login_type"] == "shared_account"

    def test_json_sorted_by_name(self, capsys):
        """Test crawlers are sorted by name."""
        with patch("ojhunt.cli.output.crawler_registry", self._make_crawlers()):
            print_crawler_list(json_output=True)
        data = json.loads(capsys.readouterr().out)
        keys = list(data.keys())
        assert keys == sorted(keys)

    def test_json_no_crawlers_goes_to_stderr(self, capsys):
        """Test 'no crawlers' message goes to stderr in JSON mode."""
        with patch("ojhunt.cli.output.crawler_registry", {}):
            print_crawler_list(json_output=True)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "No crawlers" in captured.err
