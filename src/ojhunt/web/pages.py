"""
HTML page routes for OJHunt Lite web application.
"""

import os
import secrets
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)

from ojhunt.web.legacy_db import export_user_pdf
from ojhunt.web.pdf import PdfSnapshot, extract_data, generate_pdf, merge_history
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ojhunt.crawlers import discover_crawlers
from ojhunt.web.crawler_status import get_all_status, CrawlerAvailability, CheckStatus

BUILD_TIME = os.environ.get("BUILD_TIME")
GIT_COMMIT_SHA = os.environ.get("GIT_COMMIT_SHA")
STATIC_VERSION = GIT_COMMIT_SHA or BUILD_TIME or secrets.token_hex(8)

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


@router.get("/", response_class=HTMLResponse)
async def index() -> str:
    crawlers = discover_crawlers()
    crawler_data = {
        name: {
            "title": info.meta.title,
            "description": info.meta.description,
            "isAggregator": info.meta.is_aggregator,
        }
        for name, info in sorted(crawlers.items())
    }
    template = jinja_env.get_template("index.html")
    return template.render(crawlers=crawler_data, static_version=STATIC_VERSION)


@router.get("/about", response_class=HTMLResponse)
async def about() -> str:
    template = jinja_env.get_template("about.html")
    build_time_str = None
    if BUILD_TIME:
        try:
            ts = int(BUILD_TIME)
            build_time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            build_time_str = BUILD_TIME
    return template.render(
        build_time=build_time_str,
        git_commit_sha=GIT_COMMIT_SHA,
    )


@router.get("/llms.txt", response_class=PlainTextResponse)
async def llms_txt(request: Request) -> str:
    base = str(request.base_url).rstrip("/")
    crawlers = discover_crawlers()
    crawler_names = sorted(crawlers.keys())
    template = jinja_env.get_template("llms.txt")
    return template.render(
        base=base,
        crawler_count=len(crawler_names),
        crawler_names=", ".join(crawler_names),
    )


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt(request: Request) -> str:
    base = str(request.base_url).rstrip("/")
    template = jinja_env.get_template("robots.txt")
    return template.render(base=base)


@router.get("/sitemap.xml")
async def sitemap_xml(request: Request):
    base = str(request.base_url).rstrip("/")
    template = jinja_env.get_template("sitemap.xml")
    content = template.render(base=base)
    return Response(content=content, media_type="application/xml")


@router.get("/pdf")
async def pdf_root():
    return RedirectResponse("/pdf/legacy", status_code=302)


@router.get("/pdf/legacy", response_class=HTMLResponse)
async def pdf_legacy_get() -> str:
    template = jinja_env.get_template("pdf_legacy.html")
    return template.render(
        active_page="legacy",
        legacy_available=Path("legacy.db").exists(),
    )


@router.post("/pdf/legacy")
async def pdf_legacy_post(username: str = Form(...)):
    template = jinja_env.get_template("pdf_legacy.html")
    try:
        pdf_bytes = export_user_pdf(username.strip())
    except FileNotFoundError:
        return HTMLResponse(
            template.render(
                active_page="legacy",
                legacy_available=False,
                prefill_username=username,
            )
        )
    except ValueError as e:
        return HTMLResponse(
            template.render(
                active_page="legacy",
                legacy_available=True,
                error=str(e),
                prefill_username=username,
            )
        )
    safe_name = username.strip().replace(" ", "_") or "legacy"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}_legacy.pdf"'
        },
    )


@router.get("/pdf/merge", response_class=HTMLResponse)
async def pdf_merge_get() -> str:
    template = jinja_env.get_template("pdf_merge.html")
    return template.render(active_page="merge")


@router.post("/pdf/merge")
async def pdf_merge_post(
    pdf_a: UploadFile = File(...),
    pdf_b: UploadFile = File(...),
):
    template = jinja_env.get_template("pdf_merge.html")
    try:
        bytes_a = await pdf_a.read()
        bytes_b = await pdf_b.read()
        data_a = extract_data(bytes_a)
        data_b = extract_data(bytes_b)
        history = data_a.history
        for entry in data_b.history:
            history = merge_history(history, entry)
        last = history[-1] if history else None
        snapshot = PdfSnapshot(
            totalSolved=last.totalSolved if last else 0,
            totalSubmissions=last.totalSubmissions if last else 0,
            username=data_a.settings.username,
        )
        pdf_bytes = generate_pdf(data_a.settings, history, snapshot)
    except ValueError as e:
        return HTMLResponse(template.render(active_page="merge", error=str(e)))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="merged.pdf"'},
    )


@router.get("/crawlers", response_class=HTMLResponse)
async def crawlers_page() -> str:
    crawlers = discover_crawlers()
    availability = get_all_status()
    crawler_list = []
    for name, info in sorted(crawlers.items()):
        crawler_list.append(
            {
                "name": name,
                "title": info.meta.title,
                "description": info.meta.description,
                "url": info.meta.url,
                "availability": availability.get(
                    name, CrawlerAvailability(CheckStatus.WAITING)
                ),
            }
        )
    template = jinja_env.get_template("crawlers.html")
    return template.render(crawlers=crawler_list)
