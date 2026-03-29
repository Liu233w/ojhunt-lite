# ADR 0004: History Tracking via PDF Backup/Restore

## Status

Accepted

## Context

Users wanted to track their solved-problem progress over time without introducing a
server-side database. The project has two constraints: no persistent server state,
and minimal JavaScript (Python handles business logic wherever possible).

Options considered:

1. **Server-side database** — contradicts the no-database constraint; adds operational
   burden for self-hosters.
2. **localStorage only** — survives only on the same browser; history is lost on new
   devices or browsers.
3. **PDF as persistence layer** — the user already downloads a PDF report; embed history
   as machine-readable data inside that PDF. The user carries the file; the server is
   stateless.

## Decision

Use the **PDF report file as the sole persistence layer for history**.

History and settings are embedded as invisible text in the PDF's text layer so they can
be extracted on re-upload. The latest PDF is cached as base64 in `localStorage` so the
user doesn't need to re-upload on every visit.

The day boundary for history snapshots resets at **4am local time** (not midnight) to
avoid splitting a late-night contest session across two calendar days. The frontend sends
the user's IANA timezone; the backend owns all date computation and merge/dedup logic.

PDF generation uses **fpdf2** (pure Python, zero system dependencies) rather than
weasyprint (requires Pango, GLib, Cairo), so the server works in minimal container
environments.

Both PDF endpoints use **JSON bodies** with the PDF as a base64 string, matching how the
browser already stores it in `localStorage`. This avoids blob ↔ base64 conversion on the
frontend. History is never returned to the frontend — it stays entirely within the PDF
persistence layer.

When a user uploads a PDF, settings are always written to `localStorage`. If the live
query table is empty, the UI is populated immediately; otherwise a notice is shown and
the live state is left unchanged.

## Consequences

- The server remains completely stateless — no database, no persistent files.
- History survives browser changes as long as the user keeps their PDF.
- Uploading a non-OJHunt PDF is handled gracefully: the server starts fresh history
  rather than returning an error.
- Self-hosters deploying in containers benefit from fpdf2's zero system-library footprint.
