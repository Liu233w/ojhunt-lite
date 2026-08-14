"""
HTML page routes for OJHunt Lite web application.
"""

import os
import random
import secrets
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ojhunt.crawlers import crawlers as crawler_registry
from ojhunt.web.crawler_status import CheckStatus, CrawlerAvailability, get_all_status
from ojhunt.web.legacy_db import export_user_pdf
from ojhunt.web.pdf import PdfSnapshot, extract_data, generate_pdf, merge_history

_EASTER_EGG_PATHS = [
    "/jojo",
    "/index.html",
    "/index.php",
    "/index.jsp",
    "/admin",
    "/admin/",
    "/wp-login.php",
    "/wp-config.php",
    "/readme.html",
    "/license.txt",
    "/wp-includes/js/wplink.js",
    "/wp-admin/js/customize-controls.js",
    "/wp-admin/js/nav-menu.js",
    "/wp-includes/js/plupload",
    "/wp-includes/js/tinymce",
    "/wp-includes/js/tinymce/",
    "/README",
    "/README.md",
    "/phpMyAdmin",
    "/phpMyAdmin/",
    "/phpmyadmin",
    "/phpmyadmin/",
    "/pma",
    "/pma/",
    "/swagger/elpsycongroo",
    "/ZeroClipboard.swf",
    "/js/ZeroClipboard.swf",
    "/script/ZeroClipboard.swf",
    "/lib/ZeroClipboard.swf",
    "/api.php",
    "/config.php",
    "/config.json",
    "/composer.json",
    "/package.json",
    "/actuator",
    "/actuator/health",
    "/.env",
    "/.git/config",
    "/.htaccess",
    "/.DS_Store",
    "/.bash_history",
    "/etc/passwd",
    "/shell.php",
    "/cmd.php",
]

BUILD_TIME = os.environ.get("BUILD_TIME")
GIT_COMMIT_SHA = os.environ.get("GIT_COMMIT_SHA")
STATIC_VERSION = GIT_COMMIT_SHA or BUILD_TIME or secrets.token_hex(8)

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)
jinja_env.globals["static_version"] = STATIC_VERSION


def render_page(
    template_name: str, request: Request, *, canonical: bool = True, **context: object
) -> str:
    """Render a page template with the metadata `base.html.jinja` needs.

    Pass `canonical=False` for a page that must stay out of the search index
    (404, easter eggs) — a noindex page must not claim a canonical URL.

    The canonical URL comes from the request URL itself, not from `base_url` plus
    the path: both carry any ASGI `root_path`, so joining them repeats the mount
    prefix. `site_base` keeps `base_url`, because it is joined with a literal path.
    """
    return jinja_env.get_template(template_name).render(
        site_base=str(request.base_url).rstrip("/"),
        canonical_url=str(request.url.replace(query="")) if canonical else None,
        **context,
    )


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> str:
    crawler_data = {
        name: {
            "title": info.meta.title,
            "description": info.meta.description,
            "isAggregator": info.meta.is_aggregator,
        }
        for name, info in sorted(crawler_registry.items())
    }
    return render_page("index.html.jinja", request, crawlers=crawler_data)


@router.get("/about", response_class=HTMLResponse)
async def about(request: Request) -> str:
    build_time_str = None
    if BUILD_TIME:
        try:
            ts = int(BUILD_TIME)
            # UTC, and said so: this page is rendered server-side, so the reader's
            # zone is not available here.
            build_time_str = datetime.fromtimestamp(ts, UTC).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )
        except ValueError:
            build_time_str = BUILD_TIME
    return render_page(
        "about.html.jinja",
        request,
        build_time=build_time_str,
        git_commit_sha=GIT_COMMIT_SHA,
    )


@router.get("/llms.txt", response_class=PlainTextResponse)
async def llms_txt(request: Request) -> str:
    base = str(request.base_url).rstrip("/")
    crawler_names = sorted(crawler_registry.keys())
    template = jinja_env.get_template("llms.txt.jinja")
    return template.render(
        base=base,
        crawler_count=len(crawler_names),
        crawler_names=", ".join(crawler_names),
    )


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt(request: Request) -> str:
    base = str(request.base_url).rstrip("/")
    template = jinja_env.get_template("robots.txt.jinja")
    return template.render(base=base)


@router.get("/sitemap.xml")
async def sitemap_xml(request: Request):
    base = str(request.base_url).rstrip("/")
    template = jinja_env.get_template("sitemap.xml.jinja")
    content = template.render(base=base)
    return Response(content=content, media_type="application/xml")


@router.get("/pdf")
async def pdf_root():
    return RedirectResponse("/pdf/legacy", status_code=302)


@router.get("/statistics")
async def statistics_redirect():
    return RedirectResponse("/", status_code=302)


@router.get("/pdf/legacy", response_class=HTMLResponse)
async def pdf_legacy_get(request: Request) -> str:
    return render_page(
        "pdf_legacy.html.jinja",
        request,
        active_page="legacy",
        legacy_available=Path("legacy.db").exists(),
    )


@router.post("/pdf/legacy")
async def pdf_legacy_post(request: Request, username: str = Form(...)):
    try:
        pdf_bytes = export_user_pdf(username.strip())
    except FileNotFoundError:
        return HTMLResponse(
            render_page(
                "pdf_legacy.html.jinja",
                request,
                active_page="legacy",
                legacy_available=False,
                prefill_username=username,
            )
        )
    except ValueError as e:
        return HTMLResponse(
            render_page(
                "pdf_legacy.html.jinja",
                request,
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
async def pdf_merge_get(request: Request) -> str:
    return render_page("pdf_merge.html.jinja", request, active_page="merge")


@router.post("/pdf/merge")
async def pdf_merge_post(
    request: Request,
    pdf_a: UploadFile = File(...),
    pdf_b: UploadFile = File(...),
):
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
        return HTMLResponse(
            render_page(
                "pdf_merge.html.jinja", request, active_page="merge", error=str(e)
            )
        )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="merged.pdf"'},
    )


@router.get("/crawlers", response_class=HTMLResponse)
async def crawlers_page(request: Request, test_availability: str | None = None) -> str:
    import json

    if test_availability is not None:
        try:
            raw: dict[str, str] = json.loads(test_availability)
            availability: dict[str, CrawlerAvailability] = {
                name: CrawlerAvailability(CheckStatus(status))
                for name, status in raw.items()
                if status in {s.value for s in CheckStatus}
            }
        except (json.JSONDecodeError, ValueError):
            availability = get_all_status()
    else:
        availability = get_all_status()
    crawler_list = []
    for name, info in sorted(crawler_registry.items()):
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
    return render_page("crawlers.html.jinja", request, crawlers=crawler_list)


async def _easter_egg_handler(request: Request) -> HTMLResponse:
    easter_egg_path = random.choice(
        ["easter_egg.html.jinja", "easter_egg_rick.html.jinja"]
    )
    return HTMLResponse(
        render_page(easter_egg_path, request, canonical=False, path=request.url.path)
    )


for _path in _EASTER_EGG_PATHS:
    router.add_api_route(
        _path, _easter_egg_handler, methods=["GET"], include_in_schema=False
    )
