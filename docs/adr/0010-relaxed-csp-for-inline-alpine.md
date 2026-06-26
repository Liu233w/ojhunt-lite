# ADR 0010 — Relaxed Content-Security-Policy to Support Inline Alpine.js

**Status:** Accepted

## Context

A security review against the [specification.website](https://specification.website/llms.txt)
checklist found that the live site (ojhunt.com, behind Cloudflare) emitted **none** of the
recommended security response headers — Cloudflare adds none by default. TLS 1.3, the
HTTP→HTTPS redirect, DNSSEC, and `/.well-known/security.txt` were already in place, and the
app sets no cookies.

The missing headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
`Permissions-Policy`, `Strict-Transport-Security`, and `Content-Security-Policy`) were added
in `SecurityHeadersMiddleware` (`src/ojhunt/web/app.py`). Five of them are uncontroversial.
The **CSP** required a deliberate trade-off, recorded here.

The home page (`index.html.jinja`) drives its UI with **67 inline Alpine.js expressions**
(`x-data`, `@click`, `x-show`, `x-text`, …). Alpine's standard build evaluates these via the
`Function()` constructor, which a strict CSP blocks unless `script-src` includes
`'unsafe-eval'`. The page also has inline `<script>` blocks and a `window.__CRAWLERS__` data
block, which require `'unsafe-inline'`.

## Options Considered

### Option A: Strict `script-src 'self'` by externalizing inline scripts

Move the inline `<script>` blocks to files and serve `__CRAWLERS__` as a JSON data block.

**Rejected because:** it removes `'unsafe-inline'` but not `'unsafe-eval'` — Alpine's standard
build still needs `Function()`, so the page would break under `script-src 'self'`. It solves
only half the problem.

### Option B: Full strict CSP via the `@alpinejs/csp` build

Swap in Alpine's CSP-compliant build (no `eval`), add nonce + `strict-dynamic`, and rewrite
all 67 inline expressions into the CSP build's restricted syntax (no property assignments,
arrow functions, template literals, destructuring, spread, or direct global access).

**Rejected because:** a large, high-risk refactor of every interactive element on the home
page, plus per-request nonce plumbing through `template.render(...)` (which is called
ad-hoc per route, with no central render helper). The XSS surface here is low — the app has
no auth, no cookies, and renders only server-controlled data — so the cost/risk is not
justified for the current threat model.

### Option C: Relaxed `script-src 'self' 'unsafe-inline' 'unsafe-eval'` (chosen)

Ship a CSP that constrains every other directive tightly (`default-src 'self'`,
`object-src 'none'`, `frame-ancestors 'none'`, `base-uri 'self'`, `form-action 'self'`,
`upgrade-insecure-requests`, Google Fonts the only third-party origin) while allowing inline
and eval in `script-src` only.

## Decision

**Option C.** The CSP is intentionally relaxed in `script-src` to accommodate the standard
Alpine.js build. This is **load-bearing**: tightening `script-src` to `'self'` (or removing
`'unsafe-eval'`) will silently break every Alpine-driven page. Do not tighten it without
first migrating to the `@alpinejs/csp` build (Option B).

The policy still delivers the primary hardening goals: clickjacking protection
(`frame-ancestors 'none'`), MIME-sniffing protection, referrer leakage control, capability
lockdown (`Permissions-Policy`), HSTS, and mixed-content upgrade.

## Consequences

- `SecurityHeadersMiddleware` in `src/ojhunt/web/app.py` is the single source of truth for the
  header set — values are not duplicated in prose docs.
  `tests/web/pages_test.py::test_security_headers_present_on_page` guards them.
- The CSP cannot be tightened in `script-src` without the Alpine CSP-build migration (Option
  B remains open for a future PR).
- **Interactive API docs are self-hosted.** FastAPI's default `/docs` (Swagger UI) and
  `/redoc` load their JS/CSS from `cdn.jsdelivr.net` and a favicon from `fastapi.tiangolo.com`,
  all blocked by this CSP — the pages rendered blank. The bundles are now vendored under
  `static/assets/` and served same-origin (matching the vendored Alpine.js), so the tight CSP
  needs no CDN origins. ReDoc renders inside a `blob:` web worker, so the policy includes
  `worker-src 'self' blob:`. `tests/web/pages_test.py` and `tests/e2e/test_docs_page.py` guard
  this. The vendored `redoc.standalone-*.js` hard-codes one `https://cdn.redoc.ly/redoc/logo-mini.svg`
  branding URL (blocked by `img-src 'self' data:`); it is patched to the vendored
  `/assets/redoc-logo-mini.svg`. **When re-vendoring ReDoc, re-apply that single string
  replacement** — the e2e test fails on the CSP violation if it is missed.

### Infrastructure follow-ups (out of repo — Cloudflare/DNS)

- **CAA records** — ojhunt.com currently has none. Add CAA entries restricting certificate
  issuance to the CA Cloudflare uses for the domain (e.g. Let's Encrypt / Google Trust
  Services) to prevent unauthorized issuance.
- **HSTS preload (optional)** — the header omits `preload` because it is a near-irreversible
  commitment affecting all subdomains. To enable, add `preload` to the
  `Strict-Transport-Security` value in `app.py` and submit at https://hstspreload.org.
