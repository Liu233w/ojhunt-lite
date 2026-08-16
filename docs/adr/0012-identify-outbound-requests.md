# ADR 0012 — Identify OJHunt's Outbound Requests to Online Judges

**Status:** Accepted

## Context

OJHunt queries many online judges (OJs) on behalf of users, and the hosted site runs a
background availability checker that polls every OJ periodically. Until now those requests
were anonymous: a queried OJ's maintainers had no way to tell who was hitting them or how to
reach the project — to ask questions, request rate limits, or opt out. This surfaced while
fixing the POJ crawler (ADR 0011), where POJ had disabled an endpoint, plausibly in response
to unattributed scraping.

We want every outbound crawler request to identify OJHunt and link to the project, subject
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

- `User-Agent: OJHunt/<version> (+<repo URL>)` — the primary, log-visible signal.
- `X-OJHunt: <message + repo URL + support@ojhunt.com>` — always sent (no crawler
  overrides this key), so masquerading crawlers stay identifiable.

Scope and behaviour:

- **Every entry point.** The web app (`web/http_client.py`, which also serves the background
  availability checker), the CLI batch runner (`__main__.py`) and the programmatic
  `query_sync` wrapper (`crawlers/__init__.py`) all build their session via
  `create_session()`. A judge deserves to know who is calling whichever way OJHunt was
  invoked.
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

## Update — which URL the identity carries

The identity first hardcoded `https://ojhunt.com`. Third-party deployments of OJHunt then
appeared in search results, and each one told the judges it queried that it was the hosted
site. A maintainer reading an access log saw the wrong operator.

The identity now names the **repository**, which is true of every instance. An operator adds
their own deployment on top by setting `OJHUNT_INSTANCE_URL`, which appends to both headers.
The contact address stays `support@ojhunt.com` in either case.

This does not reopen the "no env-gated flag" clause above. The variable only *adds* the
operator to the identity. Nothing turns identification off.

### Rejected: derive the URL from the request `Host`

Reading `request.base_url` per web request looks like it removes the configuration, but:

- **The traffic that most needs attribution has no request.** The availability checker
  (`web/crawler_status.py`) polls every judge from a `lifespan` loop, and the CLI and
  `query_sync` have no request either. A configured value is needed regardless, so detection
  cannot replace it.
- **`Host` is client-controlled.** `ProxyHeadersMiddleware` runs with `trusted_hosts="*"` and
  there is no `TrustedHostMiddleware`, so a crafted `Host` would land verbatim in a request to
  a third-party judge. Every instance becomes a relay for planting text in someone else's
  access log. Closing that needs a hostname allowlist — configuration again.
- **The session is process-global.** Headers are frozen at construction
  (`web/http_client.py`), and crawlers call `client.get()` on it directly. A per-request value
  could only reach them through crawler files, which the decision above forbids.
