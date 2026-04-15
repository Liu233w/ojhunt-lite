"""Unit tests for core/stats.py — collect_solved_problems()."""

from types import SimpleNamespace

from ojhunt.core.stats import collect_solved_problems


def _result(*, success, solved_list, name="oj", is_aggregator=False):
    return SimpleNamespace(
        success=success,
        solved_list=solved_list,
        crawler=SimpleNamespace(
            name=name,
            meta=SimpleNamespace(is_aggregator=is_aggregator),
        ),
    )


def test_empty_input():
    assert collect_solved_problems([]) == set()


def test_non_aggregator_prefixes_problems():
    r = _result(success=True, solved_list=["1000", "1001"], name="hdu")
    assert collect_solved_problems([r]) == {"hdu-1000", "hdu-1001"}


def test_aggregator_uses_labels_as_is():
    r = _result(
        success=True, solved_list=["codeforces-1A", "hdu-1000"], is_aggregator=True
    )
    assert collect_solved_problems([r]) == {"codeforces-1A", "hdu-1000"}


def test_failed_result_skipped():
    r = _result(success=False, solved_list=["1000"], name="hdu")
    assert collect_solved_problems([r]) == set()


def test_none_solved_list_skipped():
    r = _result(success=True, solved_list=None, name="hdu")
    assert collect_solved_problems([r]) == set()


def test_deduplication_across_aggregator_and_non_aggregator():
    # vjudge (aggregator) labels its problems as "hdu-1000"
    # hdu (non-aggregator) prefixes its own "1000" as "hdu-1000"
    # The two should collapse into one entry
    agg = _result(success=True, solved_list=["hdu-1000"], is_aggregator=True)
    non_agg = _result(success=True, solved_list=["1000"], name="hdu")
    assert collect_solved_problems([agg, non_agg]) == {"hdu-1000"}


def test_mix_success_and_failure():
    good = _result(success=True, solved_list=["1A"], name="cf")
    bad = _result(success=False, solved_list=["2B"], name="cf")
    assert collect_solved_problems([good, bad]) == {"cf-1A"}
