"""PDF generation and data extraction for OJHunt Lite progress reports."""

import io
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from fpdf import FPDF, XPos, YPos
from pydantic import BaseModel
from pypdf import PdfReader

matplotlib.use("Agg")  # non-interactive backend, safe for server use

DATA_BEGIN = "OJHUNT_DATA_v1_BEGIN"
DATA_END = "OJHUNT_DATA_v1_END"

# ---------------------------------------------------------------------------
# Font setup — use a Unicode font instead of the built-in Helvetica (which
# only covers latin-1).  We use NotoSans as the primary font (covers Latin,
# Greek, Cyrillic, Arabic, Hebrew, Thai, …) and NotoSansCJK as a fallback
# (Chinese, Japanese, Korean) via fpdf2's set_fallback_fonts().
#
# On macOS, Arial Unicode covers all scripts in a single file, so no fallback
# is needed.  On Linux/Docker, install both font packages:
#   apt-get install fonts-noto fonts-noto-cjk-core
# ---------------------------------------------------------------------------

# Each entry: (regular_path, bold_path | None)
# bold_path=None → reuse the regular file (no visual weight difference, but
# at least the characters render).
_PRIMARY_CANDIDATES = [
    # Linux — from fonts-noto
    (
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    ),
    # macOS — Arial Unicode covers all scripts; no CJK fallback needed
    ("/Library/Fonts/Arial Unicode.ttf", None),
    ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None),
]

_CJK_FALLBACK_CANDIDATES = [
    (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    ),
    (
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    ),
]


def _first_existing(candidates: list[tuple[str, str | None]]) -> tuple[str, str] | None:
    for regular, bold in candidates:
        if Path(regular).exists():
            bold_resolved = bold if bold and Path(bold).exists() else regular
            return regular, bold_resolved
    return None


_PRIMARY_FONT = _first_existing(_PRIMARY_CANDIDATES)
_CJK_FONT = _first_existing(_CJK_FALLBACK_CANDIDATES)

# Font name constant used in all set_font() calls
_FONT = "UniFont" if _PRIMARY_FONT else "Helvetica"
_CJK_FONT_NAME = "UniCJK"


class PdfQueryItem(BaseModel):
    crawler: str
    username: str


class PdfSettings(BaseModel):
    username: str
    queries: List[PdfQueryItem]


class PdfCrawlerResult(BaseModel):
    crawler: str
    username: str
    solved: int
    submissions: int


class PdfSnapshot(BaseModel):
    totalSolved: int
    totalSubmissions: int
    username: str
    timezone: str  # IANA name
    results: List[PdfCrawlerResult] = []


class HistoryEntry(BaseModel):
    key: str  # YYYY-MM-DD
    date: str  # ISO datetime
    totalSolved: int
    totalSubmissions: int
    username: str


class PdfEmbeddedData(BaseModel):
    version: int
    exportedAt: str
    settings: PdfSettings
    history: List[HistoryEntry]


def compute_day_key(iana_timezone: str) -> str:
    """Return the current YYYY-MM-DD day key using the user's local timezone.

    The day resets at 4am (not midnight) to avoid splitting a late-night session
    across two calendar days.
    """
    try:
        tz = ZoneInfo(iana_timezone)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
    now = datetime.now(tz)
    if now.hour < 4:
        now -= timedelta(days=1)
    return now.strftime("%Y-%m-%d")


def extract_data(pdf_bytes: bytes) -> PdfEmbeddedData:
    """Extract embedded OJHunt JSON from a PDF's text layer.

    Raises ValueError if the PDF cannot be read or contains no embedded data.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc

    match = re.search(
        rf"{DATA_BEGIN}\s*(\{{.*?\}})\s*{DATA_END}",
        text,
        re.DOTALL,
    )
    if not match:
        raise ValueError("No embedded OJHunt data found in this PDF")
    # pypdf injects control characters at PDF line-wrap boundaries; strip them.
    json_str = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", match.group(1))
    return PdfEmbeddedData.model_validate(json.loads(json_str))


def merge_history(
    existing: List[HistoryEntry],
    new_entry: HistoryEntry,
) -> List[HistoryEntry]:
    """Upsert new_entry into existing history by key (YYYY-MM-DD day key).

    For the same day, keeps the entry with the higher totalSolved.
    Returns a list sorted ascending by key.
    """
    by_key = {e.key: e for e in existing}
    if (
        new_entry.key not in by_key
        or new_entry.totalSolved >= by_key[new_entry.key].totalSolved
    ):
        by_key[new_entry.key] = new_entry
    return sorted(by_key.values(), key=lambda e: e.key)


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

# Layout constants (mm)
_MARGIN = 15
_PAGE_W = 210  # A4
_CONTENT_W = _PAGE_W - 2 * _MARGIN
_GRAY = (180, 180, 180)
_BLUE = (0, 102, 204)
_LIGHT_BLUE = (232, 245, 233)
_TEXT = (34, 34, 34)


class _Report(FPDF):
    # Set to True before writing invisible embedded data so that any
    # page-break header/footer text is not injected into the text layer
    # (which would corrupt JSON extraction by pypdf).
    suppress_decorations: bool = False

    def header(self) -> None:
        if self.suppress_decorations:
            return
        self.set_font(_FONT, "B", 14)
        self.set_text_color(*_TEXT)
        self.cell(
            0, 8, "OJHunt Lite - Progress Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT
        )
        self.set_draw_color(120, 120, 120)
        self.set_line_width(0.4)
        y = self.get_y() + 1
        self.line(_MARGIN, y, _PAGE_W - _MARGIN, y)
        self.set_line_width(0.2)  # reset to default
        self.ln(4)

    def footer(self) -> None:
        if self.suppress_decorations:
            return
        self.set_y(-12)
        self.set_font(_FONT, "", 8)
        self.set_text_color(*_GRAY)
        self.cell(0, 5, f"Page {self.page_no()}", align="C")


def _section(pdf: _Report, title: str) -> None:
    pdf.set_font(_FONT, "B", 10)
    pdf.set_text_color(*_TEXT)
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(0, 6, title, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)


def _render_chart_png(history: List[HistoryEntry]) -> bytes:
    """Render a solved-over-time line chart for all history entries, return PNG bytes."""
    dates = [datetime.strptime(e.key, "%Y-%m-%d") for e in history]
    solved = [e.totalSolved for e in history]

    fig, ax = plt.subplots(figsize=(7.09, 1.8))  # ~180 mm wide at 96 dpi
    ax.plot(dates, solved, color="#0066cc", linewidth=1.5, marker="o", markersize=3)
    ax.fill_between(dates, solved, alpha=0.1, color="#0066cc")

    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.AutoDateFormatter(ax.xaxis.get_major_locator()))
    fig.autofmt_xdate(rotation=30, ha="right")

    ax.set_ylabel("Solved", fontsize=7)
    ax.tick_params(labelsize=6)
    ax.grid(True, alpha=0.3, linewidth=0.5)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(pad=0.4)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_pdf(
    settings: PdfSettings,
    history: List[HistoryEntry],
    snapshot: PdfSnapshot,
) -> bytes:
    """Build an OJHunt PDF report and return the bytes."""
    pdf = _Report(orientation="P", unit="mm", format="A4")
    pdf.set_margins(_MARGIN, 18, _MARGIN)
    pdf.set_auto_page_break(auto=True, margin=15)
    if _PRIMARY_FONT:
        regular, bold = _PRIMARY_FONT
        pdf.add_font(_FONT, style="", fname=regular)
        pdf.add_font(_FONT, style="B", fname=bold)
        if _CJK_FONT:
            cjk_regular, cjk_bold = _CJK_FONT
            pdf.add_font(_CJK_FONT_NAME, style="", fname=cjk_regular)
            pdf.add_font(_CJK_FONT_NAME, style="B", fname=cjk_bold)
            pdf.set_fallback_fonts([_CJK_FONT_NAME])
    pdf.add_page()

    pdf.set_font(_FONT, "", 9)
    pdf.set_text_color(100, 100, 100)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    pdf.cell(
        0,
        5,
        f"Generated: {generated_at}    Username: {snapshot.username}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(3)

    _section(pdf, "Current Results")
    pdf.set_font(_FONT, "B", 22)
    pdf.set_text_color(*_BLUE)
    pdf.cell(_CONTENT_W / 2, 12, str(snapshot.totalSolved), align="C")
    pdf.cell(
        _CONTENT_W / 2,
        12,
        str(snapshot.totalSubmissions),
        align="C",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.set_font(_FONT, "", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(_CONTENT_W / 2, 5, "unique problems solved", align="C")
    pdf.cell(
        _CONTENT_W / 2,
        5,
        "total submissions",
        align="C",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(5)

    if settings.queries:
        _section(pdf, "Tracked Platforms")
        results_by_key = {(r.crawler, r.username): r for r in snapshot.results}
        has_results = bool(snapshot.results)

        # Column widths (mm): platform, username, solved, submissions
        cw = (
            [50.0, 70.0, 30.0, 30.0]
            if has_results
            else [_CONTENT_W / 2, _CONTENT_W / 2]
        )
        row_h = 5

        pdf.set_font(_FONT, "B", 8)
        pdf.set_text_color(*_TEXT)
        headers = (
            ["Platform", "Username", "Solved", "Submissions"]
            if has_results
            else ["Platform", "Username"]
        )
        for j, (w, h) in enumerate(zip(cw, headers)):
            is_last = j == len(cw) - 1
            pdf.cell(
                w,
                row_h,
                h,
                border="B",
                new_x=XPos.LMARGIN if is_last else XPos.RIGHT,
                new_y=YPos.NEXT if is_last else YPos.TOP,
            )

        pdf.set_font(_FONT, "", 8)
        for i, q in enumerate(settings.queries):
            fill = i % 2 == 0
            pdf.set_fill_color(238, 238, 238)
            r = results_by_key.get((q.crawler, q.username))
            row = [q.crawler, q.username]
            if has_results:
                row += [str(r.solved) if r else "-", str(r.submissions) if r else "-"]
            for j, (w, val) in enumerate(zip(cw, row)):
                is_last = j == len(cw) - 1
                pdf.cell(
                    w,
                    row_h,
                    val,
                    fill=fill,
                    new_x=XPos.LMARGIN if is_last else XPos.RIGHT,
                    new_y=YPos.NEXT if is_last else YPos.TOP,
                )

        if has_results:
            pdf.set_font(_FONT, "B", 8)
            pdf.set_fill_color(*_LIGHT_BLUE)
            pdf.cell(cw[0] + cw[1], row_h, "Total (deduplicated)", fill=True)
            pdf.cell(cw[2], row_h, str(snapshot.totalSolved), fill=True)
            pdf.cell(
                cw[3],
                row_h,
                str(snapshot.totalSubmissions),
                fill=True,
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
        pdf.ln(5)

    if history:
        _section(pdf, f"Progress History ({len(history)} entries)")
        chart_png = _render_chart_png(history)
        pdf.image(io.BytesIO(chart_png), x=_MARGIN, w=_CONTENT_W)
        pdf.ln(3)

    # Embedded data — white text on white background, invisible to readers.
    # suppress_decorations prevents the page header/footer from being written
    # into the PDF text layer on overflow pages, which would otherwise corrupt
    # JSON extraction by pypdf (it injects visible text at page boundaries).
    embedded = PdfEmbeddedData(
        version=1,
        exportedAt=datetime.now(timezone.utc).isoformat(),
        settings=settings,
        history=history,
    ).model_dump_json()
    payload = f"{DATA_BEGIN}\n{embedded}\n{DATA_END}"

    pdf.suppress_decorations = True
    pdf.set_font(_FONT, "", 1)
    pdf.set_text_color(255, 255, 255)  # white — invisible, but in text layer
    pdf.multi_cell(0, 1, payload)

    return bytes(pdf.output())
