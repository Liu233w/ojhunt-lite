"""
Unit tests for cli/parser.py
"""

import pytest

from ojhunt.cli.models import Query
from ojhunt.cli.parser import parse_args, parse_crawler_login, parse_positional


class TestParsePositional:
    """Tests for parse_positional function."""

    def test_at_syntax_basic(self):
        """Test basic user@crawler syntax."""
        result = parse_positional(["tourist@codeforces"], None)
        assert result == [
            Query(crawler="codeforces", username="tourist", password=None)
        ]

    def test_at_syntax_multiple(self):
        """Test multiple user@crawler queries."""
        result = parse_positional(["tourist@codeforces", "vjudge5@poj"], None)
        assert result == [
            Query(crawler="codeforces", username="tourist", password=None),
            Query(crawler="poj", username="vjudge5", password=None),
        ]

    def test_last_at_wins(self):
        """Test that last @ is treated as separator."""
        result = parse_positional(["user@domain@codeforces"], None)
        assert result == [
            Query(crawler="codeforces", username="user@domain", password=None)
        ]

    def test_last_at_wins_multiple_ats(self):
        """Test multiple @ signs in username."""
        result = parse_positional(["a@b@c@codeforces"], None)
        assert result == [Query(crawler="codeforces", username="a@b@c", password=None)]

    def test_default_username(self):
        """Test crawler without @ uses default username."""
        result = parse_positional(["codeforces", "poj"], "tourist")
        assert result == [
            Query(crawler="codeforces", username="tourist", password=None),
            Query(crawler="poj", username="tourist", password=None),
        ]

    def test_mixed_syntax(self):
        """Test mix of @ syntax and default username."""
        result = parse_positional(
            ["user1@codeforces", "poj", "user2@hdu"], "default_user"
        )
        assert result == [
            Query(crawler="codeforces", username="user1", password=None),
            Query(crawler="poj", username="default_user", password=None),
            Query(crawler="hdu", username="user2", password=None),
        ]

    def test_no_username_no_default_error(self):
        """Test error when no username and no default."""
        with pytest.raises(ValueError) as exc_info:
            parse_positional(["codeforces"], None)
        assert "No username specified" in str(exc_info.value)

    def test_empty_username_error(self):
        """Test error when @ has empty username."""
        with pytest.raises(ValueError) as exc_info:
            parse_positional(["@codeforces"], None)
        assert "Empty username" in str(exc_info.value)

    def test_empty_crawler_error(self):
        """Test error when @ has empty crawler."""
        with pytest.raises(ValueError) as exc_info:
            parse_positional(["user@"], None)
        assert "Empty crawler" in str(exc_info.value)

    def test_empty_list(self):
        """Test empty input list."""
        result = parse_positional([], "default")
        assert result == []

    def test_default_username_with_empty_string(self):
        """Test that empty default username is treated as None."""
        with pytest.raises(ValueError):
            parse_positional(["codeforces"], "")


class TestParsePositionalWithPassword:
    """Tests for password parsing in parse_positional function."""

    def test_password_syntax_basic(self):
        """Test basic user:password@crawler syntax."""
        result = parse_positional(["user:pass@vjudge"], None)
        assert result == [Query(crawler="vjudge", username="user", password="pass")]

    def test_password_with_at_in_password(self):
        """Test password containing @ character."""
        result = parse_positional(["user:p@ss@vjudge"], None)
        assert result == [Query(crawler="vjudge", username="user", password="p@ss")]

    def test_password_with_colon_in_password(self):
        """Test password containing : character."""
        result = parse_positional(["user:pass:word@vjudge"], None)
        assert result == [
            Query(crawler="vjudge", username="user", password="pass:word")
        ]

    def test_password_with_special_chars(self):
        """Test password with @ and : characters."""
        result = parse_positional(["user:p@ss:word@vjudge"], None)
        assert result == [
            Query(crawler="vjudge", username="user", password="p@ss:word")
        ]

    def test_empty_password(self):
        """Test empty password after colon."""
        result = parse_positional(["user:@vjudge"], None)
        assert result == [Query(crawler="vjudge", username="user", password="")]

    def test_password_without_at_in_credentials(self):
        """Test user:password@crawler where password has no @."""
        result = parse_positional(["user:mypassword@vjudge"], None)
        assert result == [
            Query(crawler="vjudge", username="user", password="mypassword")
        ]

    def test_mixed_password_and_no_password(self):
        """Test mix of password and no-password queries."""
        result = parse_positional(["user:pass@vjudge", "tourist@codeforces"], None)
        assert result == [
            Query(crawler="vjudge", username="user", password="pass"),
            Query(crawler="codeforces", username="tourist", password=None),
        ]

    def test_username_with_at_without_password(self):
        """Test username containing @ but no password."""
        result = parse_positional(["user@domain@codeforces"], None)
        assert result == [
            Query(crawler="codeforces", username="user@domain", password=None)
        ]


class TestParseArgs:
    """Tests for parse_args function."""

    def test_default_username_flag(self):
        """Test -d flag sets default username."""
        args, queries, crawler_logins = parse_args(
            ["-d", "tourist", "--", "codeforces", "poj"]
        )
        assert args.default_username == "tourist"
        assert queries == [
            Query(crawler="codeforces", username="tourist", password=None),
            Query(crawler="poj", username="tourist", password=None),
        ]
        assert crawler_logins == {}

    def test_all_flag_requires_default(self):
        """Test -a flag requires -d."""
        with pytest.raises(SystemExit):
            parse_args(["-a"])

    def test_all_flag_with_default(self):
        """Test -a flag with -d returns empty queries (filled later)."""
        args, queries, crawler_logins = parse_args(["-d", "tourist", "-a"])
        assert args.all is True
        assert args.default_username == "tourist"
        assert queries == []
        assert crawler_logins == {}

    def test_positional_after_separator(self):
        """Test positional args after --."""
        args, queries, crawler_logins = parse_args(["--", "tourist@codeforces"])
        assert queries == [
            Query(crawler="codeforces", username="tourist", password=None)
        ]
        assert crawler_logins == {}

    def test_positional_without_username_no_default_error(self):
        """Test error when positional has no username and no default."""
        with pytest.raises(SystemExit):
            parse_args(["--", "tourist@codeforces", "poj"])

    def test_list_flag(self):
        """Test --list flag returns empty queries."""
        args, queries, crawler_logins = parse_args(["--list"])
        assert args.list is True
        assert queries == []
        assert crawler_logins == {}

    def test_show_problems_flag(self):
        """Test --show-problems flag."""
        args, _, _ = parse_args(
            ["--show-problems", "-d", "tourist", "--", "codeforces"]
        )
        assert args.show_problems is True

    def test_no_args_shows_help(self):
        """Test no args exits with help."""
        with pytest.raises(SystemExit):
            parse_args([])

    def test_d_short_flag(self):
        """Test -d short flag."""
        args, _, _ = parse_args(["-d", "tourist", "-a"])
        assert args.default_username == "tourist"

    def test_a_short_flag(self):
        """Test -a short flag."""
        args, _, _ = parse_args(["-d", "tourist", "-a"])
        assert args.all is True

    def test_multiple_crawlers_with_default(self):
        """Test multiple crawlers with default username."""
        args, queries, _ = parse_args(["-d", "user", "--", "codeforces", "poj", "hdu"])
        assert len(queries) == 3
        assert all(q.username == "user" for q in queries)

    def test_user_with_at_in_name(self):
        """Test user with @ in username using last @ as separator."""
        args, queries, _ = parse_args(["--", "user@domain@codeforces"])
        assert queries == [
            Query(crawler="codeforces", username="user@domain", password=None)
        ]

    def test_password_in_query(self):
        """Test password in query string."""
        args, queries, _ = parse_args(["--", "user:pass@vjudge"])
        assert queries == [Query(crawler="vjudge", username="user", password="pass")]

    def test_crawler_login_flag(self):
        """Test -l flag parses login credentials."""
        args, queries, crawler_logins = parse_args(
            ["-l", "user:pass@vjudge", "--", "target@vjudge"]
        )
        assert queries == [Query(crawler="vjudge", username="target", password=None)]
        assert crawler_logins == {"vjudge": ("user", "pass")}

    def test_multiple_crawler_logins(self):
        """Test multiple -l flags."""
        args, queries, crawler_logins = parse_args(
            [
                "-l",
                "user1:pass1@vjudge",
                "-l",
                "user2:pass2@otheroj",
                "--",
                "target1@vjudge",
                "target2@otheroj",
            ]
        )
        assert len(queries) == 2
        assert crawler_logins == {
            "vjudge": ("user1", "pass1"),
            "otheroj": ("user2", "pass2"),
        }


class TestParseCrawlerLogin:
    """Tests for parse_crawler_login function."""

    def test_basic_parsing(self):
        """Test basic user:pass@crawler parsing."""
        result = parse_crawler_login(["user:pass@vjudge"])
        assert result == {"vjudge": ("user", "pass")}

    def test_multiple_logins(self):
        """Test multiple login strings."""
        result = parse_crawler_login(["user1:pass1@vjudge", "user2:pass2@otheroj"])
        assert result == {
            "vjudge": ("user1", "pass1"),
            "otheroj": ("user2", "pass2"),
        }

    def test_password_with_special_chars(self):
        """Test password containing @ and :."""
        result = parse_crawler_login(["user:p@ss:word@vjudge"])
        assert result == {"vjudge": ("user", "p@ss:word")}

    def test_empty_list(self):
        """Test with empty list."""
        result = parse_crawler_login([])
        assert result == {}

    def test_none_input(self):
        """Test with None input."""
        result = parse_crawler_login(None)
        assert result == {}

    def test_duplicate_crawler_error(self):
        """Test error on duplicate crawler."""
        with pytest.raises(ValueError, match="Duplicate login"):
            parse_crawler_login(["user1:pass1@vjudge", "user2:pass2@vjudge"])

    def test_missing_at_error(self):
        """Test error when @ is missing."""
        with pytest.raises(ValueError, match="Invalid login format"):
            parse_crawler_login(["user:pass"])

    def test_missing_colon_error(self):
        """Test error when : is missing."""
        with pytest.raises(ValueError, match="Missing password"):
            parse_crawler_login(["userpass@vjudge"])

    def test_empty_username_error(self):
        """Test error when username is empty."""
        with pytest.raises(ValueError, match="Empty username"):
            parse_crawler_login([":pass@vjudge"])


class TestJsonFlag:
    """Tests for --json flag parsing."""

    def test_json_flag_default_false(self):
        """Test --json defaults to False."""
        args, _, _ = parse_args(["--", "tourist@codeforces"])
        assert args.json is False

    def test_json_flag_set(self):
        """Test --json flag is parsed."""
        args, _, _ = parse_args(["--json", "--", "tourist@codeforces"])
        assert args.json is True

    def test_json_with_list(self):
        """Test --json combined with --list."""
        args, _, _ = parse_args(["--list", "--json"])
        assert args.list is True
        assert args.json is True
