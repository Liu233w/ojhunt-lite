"""Tests for the /pdf/* page routes (pages.py).

All tests run without legacy.db and without a live server — they use FastAPI's
TestClient and mock export_user_pdf where needed.
"""

from fastapi.testclient import TestClient

from ojhunt.web.app import app
from ojhunt.web.pdf import (
    HistoryEntry,
    PdfQueryItem,
    PdfSettings,
    PdfSnapshot,
    extract_data,
    generate_pdf,
)

client = TestClient(app, follow_redirects=False)


# ---------------------------------------------------------------------------
# Helpers (mirrors pdf_test.py style)
# ---------------------------------------------------------------------------


def _history_entry(day_key: str, solved: int, username: str = "u") -> HistoryEntry:
    return HistoryEntry(
        key=day_key,
        date=f"{day_key}T12:00:00Z",
        totalSolved=solved,
        totalSubmissions=solved * 2,
        username=username,
    )


def _settings(username: str = "tourist") -> PdfSettings:
    return PdfSettings(
        username=username,
        queries=[PdfQueryItem(crawler="codeforces", username=username)],
    )


def _make_pdf(
    username: str = "tourist", day_key: str = "2026-03-28", solved: int = 42
) -> bytes:
    return generate_pdf(
        _settings(username),
        [_history_entry(day_key, solved, username)],
        PdfSnapshot(totalSolved=solved, totalSubmissions=solved * 2, username=username),
    )


# ---------------------------------------------------------------------------
# GET /pdf — redirect
# ---------------------------------------------------------------------------


def test_pdf_root_redirects_to_legacy():
    response = client.get("/pdf")
    assert response.status_code == 302
    assert response.headers["location"] == "/pdf/legacy"


# ---------------------------------------------------------------------------
# GET /pdf/legacy
# ---------------------------------------------------------------------------


def test_pdf_legacy_get_renders_form(monkeypatch):
    monkeypatch.setattr("ojhunt.web.pages.Path.exists", lambda self: True)
    response = client.get("/pdf/legacy")
    assert response.status_code == 200
    assert b'name="username"' in response.content
    assert b"acm-statistics" in response.content


# ---------------------------------------------------------------------------
# POST /pdf/legacy
# ---------------------------------------------------------------------------


def test_pdf_legacy_post_db_not_found(monkeypatch):
    def _raise(username):
        raise FileNotFoundError("legacy.db not found")

    monkeypatch.setattr("ojhunt.web.pages.export_user_pdf", _raise)
    response = client.post("/pdf/legacy", data={"username": "tourist"})
    assert response.status_code == 200
    assert "not currently available" in response.text


def test_pdf_legacy_post_user_not_found(monkeypatch):
    def _raise(username):
        raise ValueError(f"Username '{username}' not found in legacy data")

    monkeypatch.setattr("ojhunt.web.pages.export_user_pdf", _raise)
    response = client.post("/pdf/legacy", data={"username": "nobody"})
    assert response.status_code == 200
    assert "nobody" in response.text
    assert "not found" in response.text.lower()


def test_pdf_legacy_post_user_not_found_prefills_username(monkeypatch):
    def _raise(username):
        raise ValueError(f"Username '{username}' not found in legacy data")

    monkeypatch.setattr("ojhunt.web.pages.export_user_pdf", _raise)
    response = client.post("/pdf/legacy", data={"username": "ghost"})
    assert b'value="ghost"' in response.content


def test_pdf_legacy_post_returns_pdf(monkeypatch):
    pdf_bytes = _make_pdf()
    monkeypatch.setattr("ojhunt.web.pages.export_user_pdf", lambda u: pdf_bytes)
    response = client.post("/pdf/legacy", data={"username": "tourist"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"
    assert "attachment" in response.headers["content-disposition"]
    assert "tourist" in response.headers["content-disposition"]


# ---------------------------------------------------------------------------
# GET /pdf/merge
# ---------------------------------------------------------------------------


def test_pdf_merge_get_renders_form():
    response = client.get("/pdf/merge")
    assert response.status_code == 200
    assert b'name="pdf_a"' in response.content
    assert b'name="pdf_b"' in response.content


# ---------------------------------------------------------------------------
# POST /pdf/merge
# ---------------------------------------------------------------------------


def test_pdf_merge_invalid_files_returns_error():
    response = client.post(
        "/pdf/merge",
        files={
            "pdf_a": ("a.pdf", b"not a pdf", "application/pdf"),
            "pdf_b": ("b.pdf", b"not a pdf", "application/pdf"),
        },
    )
    assert response.status_code == 200
    assert b"error" in response.content.lower()


def test_pdf_merge_returns_pdf():
    pdf_a = _make_pdf(username="tourist", day_key="2026-03-27", solved=30)
    pdf_b = _make_pdf(username="tourist", day_key="2026-03-28", solved=42)
    response = client.post(
        "/pdf/merge",
        files={
            "pdf_a": ("a.pdf", pdf_a, "application/pdf"),
            "pdf_b": ("b.pdf", pdf_b, "application/pdf"),
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


def test_pdf_merge_combines_history():
    pdf_a = _make_pdf(username="tourist", day_key="2026-03-27", solved=30)
    pdf_b = _make_pdf(username="tourist", day_key="2026-03-28", solved=42)
    response = client.post(
        "/pdf/merge",
        files={
            "pdf_a": ("a.pdf", pdf_a, "application/pdf"),
            "pdf_b": ("b.pdf", pdf_b, "application/pdf"),
        },
    )
    merged = extract_data(response.content)
    keys = {e.key for e in merged.history}
    assert "2026-03-27" in keys
    assert "2026-03-28" in keys


def test_pdf_merge_uses_settings_from_pdf_a():
    settings_a = PdfSettings(
        username="alice", queries=[PdfQueryItem(crawler="codeforces", username="alice")]
    )
    settings_b = PdfSettings(
        username="bob", queries=[PdfQueryItem(crawler="atcoder", username="bob")]
    )
    pdf_a = generate_pdf(
        settings_a,
        [_history_entry("2026-03-27", 30, "alice")],
        PdfSnapshot(totalSolved=30, totalSubmissions=60, username="alice"),
    )
    pdf_b = generate_pdf(
        settings_b,
        [_history_entry("2026-03-28", 42, "bob")],
        PdfSnapshot(totalSolved=42, totalSubmissions=84, username="bob"),
    )

    response = client.post(
        "/pdf/merge",
        files={
            "pdf_a": ("a.pdf", pdf_a, "application/pdf"),
            "pdf_b": ("b.pdf", pdf_b, "application/pdf"),
        },
    )
    merged = extract_data(response.content)
    assert merged.settings.username == "alice"
    assert any(q.crawler == "codeforces" for q in merged.settings.queries)
    assert not any(q.crawler == "atcoder" for q in merged.settings.queries)


def test_pdf_merge_same_day_keeps_higher_score():
    pdf_a = _make_pdf(day_key="2026-03-28", solved=30)
    pdf_b = _make_pdf(day_key="2026-03-28", solved=50)
    response = client.post(
        "/pdf/merge",
        files={
            "pdf_a": ("a.pdf", pdf_a, "application/pdf"),
            "pdf_b": ("b.pdf", pdf_b, "application/pdf"),
        },
    )
    merged = extract_data(response.content)
    assert len(merged.history) == 1
    assert merged.history[0].totalSolved == 50


# ---------------------------------------------------------------------------
# Security response headers (SecurityHeadersMiddleware)
# ---------------------------------------------------------------------------


def test_security_headers_present_on_page():
    response = client.get("/")
    headers = response.headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert headers["strict-transport-security"] == (
        "max-age=63072000; includeSubDomains"
    )
    assert "camera=()" in headers["permissions-policy"]
    csp = headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "upgrade-insecure-requests" in csp
    # ReDoc spawns a blob: web worker; the worker-src directive must allow it.
    assert "worker-src 'self' blob:" in csp


# ---------------------------------------------------------------------------
# Interactive API docs (/docs, /redoc) — self-hosted assets, no CDN
# ---------------------------------------------------------------------------
#
# FastAPI's default Swagger UI / ReDoc load JS/CSS from cdn.jsdelivr.net, which
# the CSP (ADR 0010) blocks, leaving the pages blank. The bundles are vendored
# under static/assets/ and served same-origin instead.


def test_docs_pages_use_self_hosted_assets():
    for path in ("/docs", "/redoc"):
        response = client.get(path)
        assert response.status_code == 200, path
        body = response.text
        assert "cdn.jsdelivr.net" not in body, path
        assert "fastapi.tiangolo.com" not in body, path
        assert "/assets/" in body, path
        assert "content-security-policy" in response.headers, path


def test_docs_vendored_assets_are_served():
    for asset in (
        "/assets/swagger-ui-bundle-5.32.8.js",
        "/assets/swagger-ui-5.32.8.css",
        "/assets/redoc.standalone-2.5.3.js",
    ):
        assert client.get(asset).status_code == 200, asset
