"""
Statistics calculation functions.
"""

from ojhunt.core.models import QueryResult


def collect_solved_problems(results: list[QueryResult]) -> set[str]:
    """
    Collect all solved problems with deduplication.

    For normal crawlers: prefix with crawler name (e.g., 'hdu-1000')
    For virtual judges: use labels as-is (already prefixed like 'codeforces-123A')

    Args:
        results: List of QueryResult objects from crawler queries

    Returns:
        Set of unique problem identifiers
    """
    all_solved: set[str] = set()
    for result in results:
        if not result.success or not result.solved_list:
            continue
        is_virtual = result.crawler.meta.is_aggregator
        for problem in result.solved_list:
            if is_virtual:
                all_solved.add(problem)
            else:
                all_solved.add(f"{result.crawler.name}-{problem}")
    return all_solved


def get_unique_solved(results: list[QueryResult]) -> int:
    """
    Total unique solved across all crawlers.
    """
    deduped = len(collect_solved_problems(results))
    listless = sum(r.solved for r in results if r.success and not r.solved_list)
    return deduped + listless
