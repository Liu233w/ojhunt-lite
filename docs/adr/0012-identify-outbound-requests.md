# ADR 0012 — Identify OJHunt's Outbound Requests to Online Judges

**Status:** Accepted

## Context

OJHunt queries many online judges (OJs) on behalf of users, and the hosted site runs a
background availability checker that polls every OJ periodically. Until now those requests
were anonymous: a queried OJ's maintainers had no way to tell who was hitting them or how to
reach the project — to ask questions, request rate limits, or opt out. This surfaced while
fixing the POJ crawler (ADR 0011), where POJ had disabled an endpoint, plausibly in response
to unattributed scraping.

We want every outbound crawler request to identify OJHunt and link to `ojhunt.com`, subject
to constraints:

- **Global, not per-crawler.** The crawlers in `src/ojhunt/crawlers/*.py` are meant to be
  copy-pasteable/reusable. Identification must NOT live in those files, or a copied crawler
  would carry OJHunt branding into unrelated projects.
- **Reach maintainers even when we masquerade.** Maintainers read the `User-Agent` from
  access logs, so an OJHunt UA is the most visible signal. But some OJs block non-browser
  UAs, so a crawler may override the UA with a browser string to avoid blocking (`poj`,
  `vjudge` already do). We must stay identifiable in that case too.

## Options Considered

### Option A: Custom header only (`X-OJHunt`)

Send only a custom identification header.

**Rejected as insufficient alone:** standard web-server access logs record `User-Agent`, not
arbitrary request headers, so a custom header would usually be invisible to the very
maintainers it targets.

### Option B: `User-Agent` only

Set an OJHunt UA globally and nothing else.

**Rejected as insufficient alone:** the two crawlers that must masquerade as a browser to
avoid bot-blocking override the UA per request, so those OJs would see a browser UA with no
trace of OJHunt.

### Option C: Both — OJHunt `User-Agent` + always-on `X-OJHunt` header (chosen)

Set a default OJHunt UA (visible in logs) AND a custom `X-OJHunt` header. Because no crawler
sets the `X-OJHunt` key, aiohttp's per-request header merge keeps it on every request — even
when a crawler overrides `User-Agent`.

## Decision

**Option C.** A shared factory `create_session()` in `src/ojhunt/core/session.py` seeds every
session with:

- `User-Agent: OJHunt/<version> (+https://ojhunt.com)` — the primary, log-visible signal.
- `X-OJHunt: <message + https://ojhunt.com + support@ojhunt.com>` — always sent (no crawler
  overrides this key), so masquerading crawlers stay identifiable.

Scope and behaviour:

- **Web + CLI only.** The web app (`web/http_client.py`, which also serves the background
  availability checker) and the CLI batch runner (`__main__.py`) build their session via
  `create_session()`. The programmatic `query_sync` library wrapper
  (`crawlers/__init__.py`) is left as a bare session — a library caller embedding OJHunt
  should not broadcast `ojhunt.com`.
- **Always on, hosted and self-hosted alike.** No env-gated "hosted only" flag: a flag baked
  into the container image reaches self-hosters anyway, so gating adds complexity without a
  real separation. Every OJHunt instance identifies itself.
- **UA overrides remain the crawler's escape hatch.** A crawler that gets blocked by the
  OJHunt UA may set a browser `User-Agent` per request (the `poj`/`vjudge` pattern). This is
  the one sanctioned reason to set headers inside a crawler file; `X-OJHunt` still flows.

## Consequences

- `create_session()` is the single source of truth for identity headers. Do not construct
  bare `aiohttp.ClientSession()` on the web/CLI paths — route through the factory.
- Crawler network tests build their session through `create_session(trust_env=True)`
  (`tests/crawlers/conftest.py`, `tests/crawlers/vjudge_test.py`), so the suite exercises the
  production headers and surfaces any UA-based blocking. `tests/core/session_test.py` guards
  the header contents and the per-request merge (that `X-OJHunt` survives a UA override).
- A crawler blocked by the new UA is fixed by adding a per-request browser UA, not by
  dropping the identity.
- The version in the UA comes from `importlib.metadata.version("ojhunt")`, falling back to
  `"0"` when the package metadata is unavailable.
