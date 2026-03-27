"""Generate preview PDFs with varying history sizes for visual inspection.

Usage: uv run python scripts/generate_preview_pdf.py
Output: preview_*.pdf files in the project root (gitignored).

Dates start from 2020-01-01 so you can upload a preview PDF to the web UI
and test the 'merge with existing history' feature against today's date (~2026).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from web.pdf import HistoryEntry, PdfCrawlerResult, PdfQueryItem, PdfSettings, PdfSnapshot, generate_pdf

ROOT = os.path.join(os.path.dirname(__file__), "previews")
os.makedirs(ROOT, exist_ok=True)

SETTINGS = PdfSettings(
    username="tourist",
    queries=[
        PdfQueryItem(crawler="codeforces", username="tourist"),
        PdfQueryItem(crawler="atcoder", username="tourist"),
        PdfQueryItem(crawler="leetcode", username="tourist"),
    ],
)


def _make_history(n: int) -> list[HistoryEntry]:
    """n days of history starting from 2020-01-01, with realistic growth."""
    from datetime import date, timedelta

    start = date(2020, 1, 1)
    base = 200
    entries = []
    for i in range(n):
        solved = base + int(80 * (1 - math.exp(-i / 30))) + (i % 7) * 2
        key = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        entries.append(
            HistoryEntry(
                key=key,
                date=f"{key}T12:00:00Z",
                totalSolved=solved,
                totalSubmissions=solved * 3,
                username="tourist",
            )
        )
    return entries


RESULTS = [
    PdfCrawlerResult(crawler="codeforces", username="tourist", solved=1200, submissions=3600),
    PdfCrawlerResult(crawler="atcoder", username="tourist", solved=300, submissions=500),
    PdfCrawlerResult(crawler="leetcode", username="tourist", solved=250, submissions=400),
]

for count in [1, 10, 30, 100, 1825]:
    history = _make_history(count)
    snapshot = PdfSnapshot(
        totalSolved=history[-1].totalSolved,
        totalSubmissions=history[-1].totalSubmissions,
        username="tourist",
        timezone="UTC",
        results=RESULTS,
    )
    pdf_bytes = generate_pdf(SETTINGS, history, snapshot)
    out = os.path.join(ROOT, f"preview_{count:03d}_entries.pdf")
    with open(out, "wb") as f:
        f.write(pdf_bytes)
    print(f"Saved → {out}  ({count} entries, last key: {history[-1].key})")
