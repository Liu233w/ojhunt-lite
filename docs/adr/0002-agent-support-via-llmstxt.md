# ADR 0002: Agent Support via llms.txt

## Status

Accepted

## Context

AI agents (LLM-based tools) can interact with web services, but need machine-readable
documentation to discover and use APIs correctly. Several approaches were considered:

**`/query-all` endpoint (fan-out server-side):** A single endpoint that queries all
platforms and returns merged results. Rejected because: server load scales with every
agent call; the frontend already fans out client-side for progressive display and we
do not want to duplicate that path; a 5–10s blocking response is hostile to both agents
and human users.

**`POST /cli` proxy:** Accept CLI arguments via HTTP and run them through the CLI parser.
Rejected because: credentials in request bodies/URLs are logged by proxies and servers;
Rich terminal formatting (tables, progress bars) produces ANSI codes or stripped text in
HTTP responses; it is still a new endpoint type to maintain; the CLI is designed for
interactive human use.

**MCP server:** Expose crawlers as Model Context Protocol tools. Rejected for now because
it requires MCP-compatible clients; curl-based instructions in `llms.txt` work for any
agent with HTTP or shell access and require no client-side integration.

**Two-phase: agent crawls, server merges:** Agents call per-crawler endpoints individually
(in parallel if capable), then POST collected results to `POST /api/merge` for
deduplication. This offloads crawling entirely to the agent — the server does only the
cheap merge step. Chosen.

## Decision

1. **Expose `GET /llms.txt` as a dynamic FastAPI route** documenting:
   - The existing per-crawler endpoints
   - The `POST /api/merge` endpoint (from ADR 0001)
   - A shell script template agents can adapt: parallel `curl` calls followed by a merge request
   - A note that VJudge and CSES require server-side credentials — agents call those
     endpoints normally and the server handles authentication transparently

2. **Keep all existing endpoints unchanged.** Users who script against
   `GET /api/crawlers/{crawler}/{username}` are unaffected.

3. **Do not add a separate "agent endpoint."** The existing REST API plus `llms.txt`
   documentation is sufficient. Three endpoint types (REST, agent, CLI proxy) would
   create maintenance burden; two types (REST + docs) do not.

## Consequences

- Agents with shell access can use the shell script template directly.
- Agents with only HTTP access can call per-crawler endpoints sequentially (documented
  as a fallback pattern in `llms.txt`).
- Server load from agent usage is proportional to the crawlers called — same as a human
  using the web UI.
- Login-required crawlers (VJudge, CSES) work transparently for agents: the server holds
  shared credentials, so no credential management is needed on the agent side.
- The crawler list and base URL in `llms.txt` are rendered dynamically from live server
  state, so they never go stale. The prose (endpoint descriptions, shell template) must
  be kept in sync manually if endpoint signatures change.
