"""
Unit tests for cli/output.py
"""

import pytest

from cli.models import Query
from cli.output import (
    check_duplicate_queries,
    collect_solved_problems,
    validate_crawlers,
    validate_credentials,
)
from cli.parser import build_all_queries


class TestBuildAllQueries:
    """Tests for build_all_queries function."""

    def test_build_all_queries(self):
        """Test building queries for all crawlers."""
        crawlers = {
            "codeforces": {"meta": {"title": "CodeForces"}},
            "poj": {"meta": {"title": "POJ"}},
            "hdu": {"meta": {"title": "HDU"}},
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
            "a": {"meta": {}},
            "b": {"meta": {}},
            "c": {"meta": {}},
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
            "codeforces": {"meta": {}},
            "poj": {"meta": {}},
        }
        assert validate_crawlers(queries, crawlers) is True

    def test_unknown_crawler(self, capsys):
        """Test with unknown crawler."""
        queries = [
            Query(crawler="codeforces", username="user1"),
            Query(crawler="unknown", username="user2"),
        ]
        crawlers = {
            "codeforces": {"meta": {}},
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
        crawlers = {"codeforces": {"meta": {}}}
        assert validate_crawlers(queries, crawlers) is False
        captured = capsys.readouterr()
        assert "unknown crawler(s): alpha, zebra" in captured.err

    def test_empty_queries(self):
        """Test with empty query list."""
        crawlers = {"codeforces": {"meta": {}}}
        assert validate_crawlers([], crawlers) is True

    def test_empty_crawlers(self):
        """Test with empty crawlers dict and no queries."""
        assert validate_crawlers([], {}) is True


class TestValidateCredentials:
    """Tests for validate_credentials function."""

    def test_no_auth_required(self):
        """Test crawler that doesn't require authentication."""
        queries = [Query(crawler="codeforces", username="user1")]
        crawlers = {"codeforces": {"meta": {}}}
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is True

    def test_requires_login_with_embedded_password(self):
        """Test requires_login crawler with embedded password."""
        queries = [Query(crawler="vjudge", username="user1", password="pass")]
        crawlers = {"vjudge": {"meta": {"requires_login": True}}}
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is True

    def test_requires_login_with_flag_credentials(self):
        """Test requires_login crawler with -l flag credentials."""
        queries = [Query(crawler="vjudge", username="user1")]
        crawlers = {"vjudge": {"meta": {"requires_login": True}}}
        crawler_logins = {"vjudge": ("loginuser", "pass")}
        assert validate_credentials(queries, crawlers, crawler_logins) is True

    def test_requires_login_missing_credentials(self, capsys):
        """Test requires_login crawler without any credentials."""
        queries = [Query(crawler="vjudge", username="user1")]
        crawlers = {"vjudge": {"meta": {"requires_login": True}}}
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is False
        captured = capsys.readouterr()
        assert "requires login credentials" in captured.err

    def test_requires_login_duplicate_credentials(self, capsys):
        """Test requires_login crawler with both embedded and flag credentials."""
        queries = [Query(crawler="vjudge", username="user1", password="pass")]
        crawlers = {"vjudge": {"meta": {"requires_login": True}}}
        crawler_logins = {"vjudge": ("loginuser", "pass2")}
        assert validate_credentials(queries, crawlers, crawler_logins) is False
        captured = capsys.readouterr()
        assert "duplicate credentials" in captured.err

    def test_requires_password_provided(self):
        """Test requires_password crawler with password provided."""
        queries = [Query(crawler="someoj", username="user1", password="pass")]
        crawlers = {"someoj": {"meta": {"requires_password": True}}}
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is True

    def test_requires_password_missing(self, capsys):
        """Test requires_password crawler without password."""
        queries = [Query(crawler="someoj", username="user1")]
        crawlers = {"someoj": {"meta": {"requires_password": True}}}
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is False
        captured = capsys.readouterr()
        assert "requires a password" in captured.err

    def test_unwanted_password_in_query(self, capsys):
        """Test crawler that doesn't require auth but password provided."""
        queries = [Query(crawler="codeforces", username="user1", password="pass")]
        crawlers = {"codeforces": {"meta": {}}}
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is False
        captured = capsys.readouterr()
        assert "does not require credentials" in captured.err

    def test_empty_queries(self):
        """Test with empty query list."""
        crawlers = {"codeforces": {"meta": {}}}
        crawler_logins = {}
        assert validate_credentials([], crawlers, crawler_logins) is True

    def test_multiple_queries_mixed(self):
        """Test multiple queries with different auth requirements."""
        queries = [
            Query(crawler="codeforces", username="user1"),
            Query(crawler="vjudge", username="user2", password="pass"),
        ]
        crawlers = {
            "codeforces": {"meta": {}},
            "vjudge": {"meta": {"requires_login": True}},
        }
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is True


class TestCollectSolvedProblems:
    """Tests for collect_solved_problems function."""

    def test_normal_crawler_prefix(self):
        """Test that normal crawlers get prefixed with crawler name."""
        results = [
            {
                "crawler": "hdu",
                "success": True,
                "solved_list": ["1000", "1001", "1002"],
            }
        ]
        crawlers = {
            "hdu": {"meta": {}},
        }
        solved = collect_solved_problems(results, crawlers)
        assert solved == {"hdu-1000", "hdu-1001", "hdu-1002"}

    def test_virtual_judge_no_prefix(self):
        """Test that virtual judges use labels as-is."""
        results = [
            {
                "crawler": "vjudge",
                "success": True,
                "solved_list": ["codeforces-123A", "poj-1000"],
            }
        ]
        crawlers = {
            "vjudge": {"meta": {"is_virtual_judge": True}},
        }
        solved = collect_solved_problems(results, crawlers)
        assert solved == {"codeforces-123A", "poj-1000"}

    def test_mixed_crawlers(self):
        """Test mix of normal and virtual judges."""
        results = [
            {
                "crawler": "hdu",
                "success": True,
                "solved_list": ["1000"],
            },
            {
                "crawler": "vjudge",
                "success": True,
                "solved_list": ["codeforces-123A"],
            },
        ]
        crawlers = {
            "hdu": {"meta": {}},
            "vjudge": {"meta": {"is_virtual_judge": True}},
        }
        solved = collect_solved_problems(results, crawlers)
        assert solved == {"hdu-1000", "codeforces-123A"}

    def test_deduplication(self):
        """Test that duplicates are removed."""
        results = [
            {
                "crawler": "hdu",
                "success": True,
                "solved_list": ["1000", "1001"],
            },
            {
                "crawler": "hdu",
                "success": True,
                "solved_list": ["1000", "1002"],
            },
        ]
        crawlers = {
            "hdu": {"meta": {}},
        }
        solved = collect_solved_problems(results, crawlers)
        assert solved == {"hdu-1000", "hdu-1001", "hdu-1002"}

    def test_failed_result_ignored(self):
        """Test that failed results are ignored."""
        results = [
            {
                "crawler": "hdu",
                "success": True,
                "solved_list": ["1000"],
            },
            {
                "crawler": "poj",
                "success": False,
                "solved_list": ["1001"],
            },
        ]
        crawlers = {
            "hdu": {"meta": {}},
            "poj": {"meta": {}},
        }
        solved = collect_solved_problems(results, crawlers)
        assert solved == {"hdu-1000"}

    def test_empty_results(self):
        """Test with empty results list."""
        solved = collect_solved_problems([], {})
        assert solved == set()

    def test_empty_solved_list(self):
        """Test with empty solved_list in result."""
        results = [
            {
                "crawler": "hdu",
                "success": True,
                "solved_list": [],
            }
        ]
        crawlers = {"hdu": {"meta": {}}}
        solved = collect_solved_problems(results, crawlers)
        assert solved == set()
