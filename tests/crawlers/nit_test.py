"""
Tests for NIT crawler
"""

import pytest
from selectolax.lexbor import LexborHTMLParser

from ojhunt.crawlers.nit import __crawler_meta__, _extract_number_from_cell, query

pytestmark = pytest.mark.network

TEST_USERNAME = __crawler_meta__["test_username"]
NOT_EXIST_USERNAME = "fmv84zcq3hwu"


def test_extract_number_from_cell_with_link():
    html = '<table><tr><td class="span3"><a href="status.php?showname=teito">7741</a></td></tr></table>'
    doc = LexborHTMLParser(html)
    cell = doc.css_first("td")
    result = _extract_number_from_cell(cell)
    assert result == 7741


def test_extract_number_from_cell_without_link():
    html = "<table><tr><td>123</td></tr></table>"
    doc = LexborHTMLParser(html)
    cell = doc.css_first("td")
    result = _extract_number_from_cell(cell)
    assert result == 123


def test_extract_number_from_cell_empty():
    html = "<table><tr><td></td></tr></table>"
    doc = LexborHTMLParser(html)
    cell = doc.css_first("td")
    result = _extract_number_from_cell(cell)
    assert result == 0


@pytest.mark.asyncio
async def test_user_not_exist(session):
    """Test that non-existent user raises ValueError"""
    with pytest.raises(ValueError, match="The user does not exist"):
        await query(session, NOT_EXIST_USERNAME)


@pytest.mark.asyncio
async def test_username_with_space(session):
    """Test that username with space is handled correctly"""
    with pytest.raises(ValueError, match="The user does not exist"):
        await query(session, " " + NOT_EXIST_USERNAME)


@pytest.mark.asyncio
async def test_valid_user(session):
    """Test that valid user returns correct data structure"""
    result = await query(session, TEST_USERNAME)

    assert "solved" in result
    assert "submissions" in result
    assert "solved_list" in result

    assert isinstance(result["solved"], int)
    assert isinstance(result["submissions"], int)
    assert isinstance(result["solved_list"], list)

    assert result["solved"] > 0
    assert result["submissions"] > 0
    assert result["submissions"] >= result["solved"]

    assert len(result["solved_list"]) > 0, (
        "solved_list holds the unique problems solved on NIT, and its length can "
        "differ from the count the profile page reports"
    )
    assert len(result["solved_list"]) <= result["solved"]

    assert "nit-100" in result["solved_list"], (
        "NIT lists problems from other judges alongside its own"
    )
    assert "hdu-2181" in result["solved_list"], "NIT problem 2097 maps to hdu-2181"
