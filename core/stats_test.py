"""
Unit tests for core module.
"""

from core.models import CrawlerInfo, CrawlerMeta, NullCrawler, QueryResult
from core.stats import collect_solved_problems


def _make_crawler(name: str, **meta_kwargs) -> CrawlerInfo:
    """Helper to create a CrawlerInfo with a stub query function."""

    async def _stub_query(*args, **kwargs):
        return {}

    return CrawlerInfo(
        name=name,
        meta=CrawlerMeta(**meta_kwargs),
        query=_stub_query,
    )


def _make_result(
    crawler: CrawlerInfo,
    username: str,
    success: bool,
    solved_list: list = None,
    **kwargs,
) -> QueryResult:
    """Helper to create a QueryResult."""
    return QueryResult(
        crawler=crawler,
        username=username,
        success=success,
        solved_list=solved_list,
        **kwargs,
    )


class TestCrawlerMeta:
    """Tests for CrawlerMeta dataclass."""

    def test_defaults(self):
        """Test default values."""
        meta = CrawlerMeta(title="Test")
        assert meta.title == "Test"
        assert meta.description == ""
        assert meta.url == ""
        assert meta.is_virtual_judge is False
        assert meta.requires_login is False
        assert meta.requires_password is False

    def test_all_fields(self):
        """Test with all fields set."""
        meta = CrawlerMeta(
            title="VJudge",
            description="Virtual Judge",
            url="https://vjudge.net",
            is_virtual_judge=True,
            requires_login=True,
        )
        assert meta.title == "VJudge"
        assert meta.is_virtual_judge is True
        assert meta.requires_login is True


class TestNullCrawler:
    """Tests for NullCrawler class."""

    def test_null_crawler(self):
        """Test NullCrawler creation."""
        crawler = NullCrawler("unknown")
        assert crawler.name == "unknown"
        assert crawler.meta.title == "unknown"


class TestQueryResult:
    """Tests for QueryResult dataclass."""

    def test_success_result(self):
        """Test successful result."""
        crawler = _make_crawler("codeforces", title="CodeForces")
        result = QueryResult(
            crawler=crawler,
            username="tourist",
            success=True,
            solved=100,
            submissions=200,
            solved_list=["1A", "1B"],
            duration=1.5,
        )
        assert result.success is True
        assert result.solved == 100
        assert result.solved_list == ["1A", "1B"]
        assert result.error is None

    def test_error_result(self):
        """Test error result."""
        crawler = _make_crawler("codeforces", title="CodeForces")
        result = QueryResult(
            crawler=crawler,
            username="nonexistent",
            success=False,
            error="User not found",
        )
        assert result.success is False
        assert result.error == "User not found"
        assert result.solved == 0


class TestCollectSolvedProblems:
    """Tests for collect_solved_problems function."""

    def test_normal_crawler_prefix(self):
        """Test that normal crawlers get prefixed with crawler name."""
        crawler = _make_crawler("hdu", title="HDU")
        results = [
            _make_result(crawler, "user", True, solved_list=["1000", "1001", "1002"])
        ]
        solved = collect_solved_problems(results)
        assert solved == {"hdu-1000", "hdu-1001", "hdu-1002"}

    def test_virtual_judge_no_prefix(self):
        """Test that virtual judges use labels as-is."""
        crawler = _make_crawler("vjudge", title="VJudge", is_virtual_judge=True)
        results = [
            _make_result(
                crawler, "user", True, solved_list=["codeforces-123A", "poj-1000"]
            )
        ]
        solved = collect_solved_problems(results)
        assert solved == {"codeforces-123A", "poj-1000"}

    def test_mixed_crawlers(self):
        """Test mix of normal and virtual judges."""
        hdu = _make_crawler("hdu", title="HDU")
        vjudge = _make_crawler("vjudge", title="VJudge", is_virtual_judge=True)
        results = [
            _make_result(hdu, "user1", True, solved_list=["1000"]),
            _make_result(vjudge, "user2", True, solved_list=["codeforces-123A"]),
        ]
        solved = collect_solved_problems(results)
        assert solved == {"hdu-1000", "codeforces-123A"}

    def test_deduplication(self):
        """Test that duplicates are removed."""
        crawler = _make_crawler("hdu", title="HDU")
        results = [
            _make_result(crawler, "user1", True, solved_list=["1000", "1001"]),
            _make_result(crawler, "user2", True, solved_list=["1000", "1002"]),
        ]
        solved = collect_solved_problems(results)
        assert solved == {"hdu-1000", "hdu-1001", "hdu-1002"}

    def test_failed_result_ignored(self):
        """Test that failed results are ignored."""
        crawler = _make_crawler("hdu", title="HDU")
        results = [
            _make_result(crawler, "user1", True, solved_list=["1000"]),
            _make_result(crawler, "user2", False, solved_list=["1001"], error="Failed"),
        ]
        solved = collect_solved_problems(results)
        assert solved == {"hdu-1000"}

    def test_empty_results(self):
        """Test with empty results list."""
        solved = collect_solved_problems([])
        assert solved == set()

    def test_empty_solved_list(self):
        """Test with empty solved_list in result."""
        crawler = _make_crawler("hdu", title="HDU")
        results = [_make_result(crawler, "user", True, solved_list=[])]
        solved = collect_solved_problems(results)
        assert solved == set()

    def test_none_solved_list(self):
        """Test with None solved_list in result."""
        crawler = _make_crawler("hdu", title="HDU")
        results = [_make_result(crawler, "user", True, solved_list=None)]
        solved = collect_solved_problems(results)
        assert solved == set()
