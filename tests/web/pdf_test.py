"""Tests for PDF generation and data extraction (web/pdf.py and /api/pdf/* routes)."""

import base64
from datetime import datetime as _datetime
from datetime import timezone as _timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from fpdf import FPDF

from ojhunt.web.app import app
from ojhunt.web.pdf import (
    HistoryEntry,
    PdfQueryItem,
    PdfSettings,
    PdfSnapshot,
    compute_day_key,
    extract_data,
    generate_pdf,
    merge_history,
)


def _mock_now(fixed_utc: _datetime):
    """Return a side_effect for datetime.now(tz) that converts a fixed UTC instant."""
    return lambda tz=None: fixed_utc.astimezone(tz) if tz else fixed_utc


client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _history_entry(
    day_key: str, solved: int, submissions: int = 0, username: str = "u"
) -> HistoryEntry:
    return HistoryEntry(
        key=day_key,
        date=f"{day_key}T12:00:00Z",
        totalSolved=solved,
        totalSubmissions=submissions,
        username=username,
    )


def _settings(username: str = "tourist") -> PdfSettings:
    return PdfSettings(
        username=username,
        queries=[PdfQueryItem(crawler="codeforces", username=username)],
    )


def _generate(
    snapshot: dict, settings: PdfSettings, previous_pdf_bytes: bytes | None = None
) -> object:
    """Call POST /api/pdf/generate with JSON body. Returns the response."""
    body: dict = {"snapshot": snapshot, "settings": settings.model_dump()}
    if previous_pdf_bytes is not None:
        body["previous_pdf_b64"] = base64.b64encode(previous_pdf_bytes).decode()
    return client.post("/api/pdf/generate", json=body)


def _extract(pdf_bytes: bytes) -> object:
    """Call POST /api/pdf/extract with JSON body. Returns the response."""
    return client.post(
        "/api/pdf/extract", json={"pdf_b64": base64.b64encode(pdf_bytes).decode()}
    )


def _make_blank_pdf(text: str = "no data here") -> bytes:
    """Minimal valid PDF with no embedded OJHunt data."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, text)
    return bytes(pdf.output())


# ---------------------------------------------------------------------------
# compute_day_key
# ---------------------------------------------------------------------------


def test_compute_day_key_after_4am():
    fixed = _datetime(2026, 3, 29, 10, 0, tzinfo=_timezone.utc)
    with patch("ojhunt.web.pdf.datetime") as mock_dt:
        mock_dt.now.side_effect = _mock_now(fixed)
        assert compute_day_key("UTC") == "2026-03-29"


def test_compute_day_key_before_4am_returns_previous_day():
    fixed = _datetime(2026, 3, 29, 2, 30, tzinfo=_timezone.utc)
    with patch("ojhunt.web.pdf.datetime") as mock_dt:
        mock_dt.now.side_effect = _mock_now(fixed)
        assert compute_day_key("UTC") == "2026-03-28"


def test_compute_day_key_exactly_4am_is_current_day():
    fixed = _datetime(2026, 3, 29, 4, 0, tzinfo=_timezone.utc)
    with patch("ojhunt.web.pdf.datetime") as mock_dt:
        mock_dt.now.side_effect = _mock_now(fixed)
        assert compute_day_key("UTC") == "2026-03-29"


def test_compute_day_key_invalid_timezone_falls_back_to_utc():
    fixed = _datetime(2026, 3, 29, 10, 0, tzinfo=_timezone.utc)
    with patch("ojhunt.web.pdf.datetime") as mock_dt:
        mock_dt.now.side_effect = _mock_now(fixed)
        assert compute_day_key("Not/A/Zone") == "2026-03-29"


def test_compute_day_key_timezone_before_4am_local():
    # 03:00 America/New_York (EDT, UTC-4) = 07:00 UTC — before 4am locally
    fixed = _datetime(2026, 3, 29, 7, 0, tzinfo=_timezone.utc)
    with patch("ojhunt.web.pdf.datetime") as mock_dt:
        mock_dt.now.side_effect = _mock_now(fixed)
        assert compute_day_key("America/New_York") == "2026-03-28"


def test_compute_day_key_dst_spring_forward():
    # 2024-03-10 is US "spring forward" day (clocks jump 2am EST → 3am EDT at 07:00 UTC).
    # 07:30 UTC = 03:30 EDT — inside the spring-forward gap, still before 4am local.
    # Day key should roll back to the previous day, not produce an incorrect date.
    fixed = _datetime(2024, 3, 10, 7, 30, tzinfo=_timezone.utc)
    with patch("ojhunt.web.pdf.datetime") as mock_dt:
        mock_dt.now.side_effect = _mock_now(fixed)
        assert compute_day_key("America/New_York") == "2024-03-09"


def test_compute_day_key_dst_spring_forward_after_4am():
    # 08:00 UTC on spring-forward day = 04:00 EDT — exactly 4am, so current day.
    fixed = _datetime(2024, 3, 10, 8, 0, tzinfo=_timezone.utc)
    with patch("ojhunt.web.pdf.datetime") as mock_dt:
        mock_dt.now.side_effect = _mock_now(fixed)
        assert compute_day_key("America/New_York") == "2024-03-10"


# ---------------------------------------------------------------------------
# merge_history
# ---------------------------------------------------------------------------


def test_merge_adds_new_entry():
    existing = [_history_entry("2026-03-27", 30)]
    result = merge_history(existing, _history_entry("2026-03-28", 42))
    assert len(result) == 2
    assert result[-1].key == "2026-03-28"


def test_merge_upserts_same_day_higher_score():
    existing = [_history_entry("2026-03-28", 30)]
    result = merge_history(existing, _history_entry("2026-03-28", 42))
    assert len(result) == 1
    assert result[0].totalSolved == 42


def test_merge_keeps_existing_if_higher():
    existing = [_history_entry("2026-03-28", 50)]
    result = merge_history(existing, _history_entry("2026-03-28", 30))
    assert result[0].totalSolved == 50


def test_merge_sorts_by_key():
    existing = [_history_entry("2026-03-28", 42), _history_entry("2026-03-26", 30)]
    result = merge_history(existing, _history_entry("2026-03-27", 35))
    keys = [e.key for e in result]
    assert keys == sorted(keys)


def test_merge_empty_existing():
    result = merge_history([], _history_entry("2026-03-28", 42))
    assert len(result) == 1


# ---------------------------------------------------------------------------
# generate_pdf + extract_data roundtrip
# ---------------------------------------------------------------------------


def test_roundtrip_settings_and_history():
    settings = _settings()
    history = [_history_entry("2026-03-28", 42, submissions=100)]
    snapshot = PdfSnapshot(
        totalSolved=42, totalSubmissions=100, username="tourist", timezone="UTC"
    )
    pdf_bytes = generate_pdf(settings, history, snapshot)

    extracted = extract_data(pdf_bytes)
    assert extracted.settings == settings
    assert len(extracted.history) == 1
    assert extracted.history[0].key == "2026-03-28"
    assert extracted.history[0].totalSolved == 42


def test_extract_data_invalid_pdf():
    with pytest.raises(ValueError, match="Could not read PDF"):
        extract_data(b"not a pdf")


def test_extract_data_pdf_without_embedded_data():
    with pytest.raises(ValueError, match="No embedded OJHunt data"):
        extract_data(_make_blank_pdf())


# ---------------------------------------------------------------------------
# API: POST /api/pdf/extract
# ---------------------------------------------------------------------------


def test_api_extract_missing_body():
    response = client.post("/api/pdf/extract")
    assert response.status_code == 422


def test_api_extract_invalid_base64():
    response = client.post("/api/pdf/extract", json={"pdf_b64": "!!!not-base64!!!"})
    assert response.status_code == 422


def test_api_extract_invalid_pdf():
    b64 = base64.b64encode(b"not a pdf").decode()
    response = client.post("/api/pdf/extract", json={"pdf_b64": b64})
    assert response.status_code == 422
    assert "Could not read PDF" in response.json()["detail"]


def test_api_extract_pdf_without_data():
    response = _extract(_make_blank_pdf("no data"))
    assert response.status_code == 422
    assert "No embedded OJHunt data" in response.json()["detail"]


def test_api_extract_returns_settings_and_report_date():
    settings = _settings()
    history = [_history_entry("2026-03-28", 42)]
    snapshot = PdfSnapshot(
        totalSolved=42, totalSubmissions=100, username="tourist", timezone="UTC"
    )
    pdf_bytes = generate_pdf(settings, history, snapshot)

    response = _extract(pdf_bytes)
    assert response.status_code == 200
    data = response.json()
    assert data["settings"]["username"] == "tourist"
    assert data["settings"]["queries"] == [
        {"crawler": "codeforces", "username": "tourist"}
    ]
    assert data["report_date"] == "2026-03-28"
    assert "history" not in data


# ---------------------------------------------------------------------------
# API: POST /api/pdf/generate
# ---------------------------------------------------------------------------


def test_api_generate_returns_base64_pdf():
    snapshot = {
        "totalSolved": 42,
        "totalSubmissions": 100,
        "username": "tourist",
        "timezone": "UTC",
    }
    response = _generate(snapshot, _settings())
    assert response.status_code == 200
    data = response.json()
    assert "pdf_b64" in data
    assert "date" in data
    pdf_bytes = base64.b64decode(data["pdf_b64"])
    assert pdf_bytes[:4] == b"%PDF"


def test_api_generate_missing_snapshot():
    response = client.post(
        "/api/pdf/generate", json={"settings": _settings().model_dump()}
    )
    assert response.status_code == 422


def test_api_generate_merges_previous_pdf():
    snapshot1 = {
        "totalSolved": 42,
        "totalSubmissions": 100,
        "username": "tourist",
        "timezone": "UTC",
    }
    snapshot2 = {
        "totalSolved": 50,
        "totalSubmissions": 120,
        "username": "tourist",
        "timezone": "UTC",
    }
    settings = _settings()

    r1 = _generate(snapshot1, settings)
    assert r1.status_code == 200
    pdf1 = base64.b64decode(r1.json()["pdf_b64"])
    date1 = r1.json()["date"]

    r2 = _generate(snapshot2, settings, previous_pdf_bytes=pdf1)
    assert r2.status_code == 200
    pdf2 = base64.b64decode(r2.json()["pdf_b64"])

    r3 = _extract(pdf2)
    assert r3.status_code == 200
    # report_date should be the most recent entry (date from r2 since it ran after r1)
    assert r3.json()["report_date"] is not None
    # Both day keys must appear in embedded history
    extracted = extract_data(pdf2)
    keys = {e.key for e in extracted.history}
    assert date1 in keys
    assert r2.json()["date"] in keys


def test_api_generate_same_day_upserts_highest_score():
    """Two generates on the same day keep one entry with the higher score."""
    snapshot_low = {
        "totalSolved": 30,
        "totalSubmissions": 80,
        "username": "tourist",
        "timezone": "UTC",
    }
    snapshot_high = {
        "totalSolved": 50,
        "totalSubmissions": 120,
        "username": "tourist",
        "timezone": "UTC",
    }
    settings = _settings()

    with patch("ojhunt.web.api.compute_day_key", return_value="2026-03-29"):
        r1 = _generate(snapshot_low, settings)
        assert r1.status_code == 200
        pdf1 = base64.b64decode(r1.json()["pdf_b64"])

        r2 = _generate(snapshot_high, settings, previous_pdf_bytes=pdf1)
        assert r2.status_code == 200

    extracted = extract_data(base64.b64decode(r2.json()["pdf_b64"]))
    assert len(extracted.history) == 1
    assert extracted.history[0].key == "2026-03-29"
    assert extracted.history[0].totalSolved == 50


def test_api_generate_different_day_appends_entry():
    """Two generates on different days produce two distinct history entries."""
    snapshot1 = {
        "totalSolved": 30,
        "totalSubmissions": 80,
        "username": "tourist",
        "timezone": "UTC",
    }
    snapshot2 = {
        "totalSolved": 50,
        "totalSubmissions": 120,
        "username": "tourist",
        "timezone": "UTC",
    }
    settings = _settings()

    with patch("ojhunt.web.api.compute_day_key", return_value="2026-03-28"):
        r1 = _generate(snapshot1, settings)
        assert r1.status_code == 200
    pdf1 = base64.b64decode(r1.json()["pdf_b64"])

    with patch("ojhunt.web.api.compute_day_key", return_value="2026-03-29"):
        r2 = _generate(snapshot2, settings, previous_pdf_bytes=pdf1)
        assert r2.status_code == 200
    extracted = extract_data(base64.b64decode(r2.json()["pdf_b64"]))

    assert len(extracted.history) == 2
    keys = [e.key for e in extracted.history]
    assert "2026-03-28" in keys
    assert "2026-03-29" in keys


@pytest.mark.parametrize("n", [100, 1825])
def test_generate_large_history_roundtrip(n):
    """PDFs with large histories (100 days, 5 years) roundtrip without losing entries."""
    from datetime import date, timedelta

    settings = _settings()
    start = date(2020, 1, 1)
    history = [
        _history_entry((start + timedelta(days=i)).strftime("%Y-%m-%d"), 200 + i)
        for i in range(n)
    ]
    snapshot = PdfSnapshot(
        totalSolved=200 + n, totalSubmissions=1000, username="tourist", timezone="UTC"
    )
    pdf_bytes = generate_pdf(settings, history, snapshot)

    extracted = extract_data(pdf_bytes)
    assert len(extracted.history) == n
    assert extracted.history[0].key == history[0].key
    assert extracted.history[-1].key == history[-1].key


def test_api_generate_non_ojhunt_pdf_treated_as_first_time():
    other_pdf = _make_blank_pdf("some other pdf")

    snapshot = {
        "totalSolved": 42,
        "totalSubmissions": 100,
        "username": "tourist",
        "timezone": "UTC",
    }
    response = _generate(snapshot, _settings(), previous_pdf_bytes=other_pdf)
    assert response.status_code == 200

    pdf_bytes = base64.b64decode(response.json()["pdf_b64"])
    extracted = extract_data(pdf_bytes)
    assert len(extracted.history) == 1
