# ADR 0017 — The Cached Report Is One Record: Remove Before Write, All or Nothing on Read

**Status:** Accepted

## Context

The home page keeps the loaded report in `localStorage` under three keys: the PDF bytes
(`ojhunt-report-pdf`), the day key of its newest history entry (`ojhunt-report-date`) and the
filename to show and to download (`ojhunt-report-filename`). The three describe one report.
`localStorage` writes one key at a time, so nothing makes the three writes atomic.

Two failure modes follow, and both were live defects:

- **A fragment.** A rejected write, an eviction or another tab leaves some keys behind. Bytes
  without a date still merged into the next report while the panel showed nothing, so the user
  could not see, download or clear them.
- **A mismatch.** `setItem` throws *before* it stores, so the previous value survives a rejected
  write. Replacing report A with report B, with the write for the bytes rejected, left A's bytes
  beside B's date and filename. The panel then offered A's bytes named `B.pdf`, and merged A's
  history under B's date.

The report is also small — about 59 KiB, and twelve history entries add under 1 KiB — so a
rejected write means a browser that is out of space for other reasons, not a growing report.

## Options Considered

### Option A: Roll back a rejected write

Write the keys in order. On a rejection, remove every key already written, plus the key that
was rejected, because its old value survives.

**Rejected because:** it repairs a mismatch after the fact and depends on catching every write
site. It also cannot cover a fragment that our own code never made, such as one key evicted
under storage pressure.

### Option B: Keep the previous record when a write is rejected

Treat the stored record as a cache of last resort: if the new report cannot be stored, leave the
report that is already there.

**Rejected because:** the surviving record comes back after a reload as the current report, with
no sign that it is older than what the user loaded. Losing a report is acceptable, presenting the
wrong one as the latest is not.

### Option C: Remove before write, all or nothing on read (chosen)

`cacheReport()` removes all three keys, then writes all three. A rejected write therefore needs
no handling: the removal already happened, so the store holds nothing rather than a mismatch.
`readCachedReport()` returns the record only when all three keys are present, and removes all
three otherwise.

## Decision

**Option C.** The removal at the start of `cacheReport()` is **load-bearing** — it is what makes
the empty `catch` correct. Do not "optimise" it into a plain overwrite: the write would then keep
the replaced report on a rejection, which is Option B.

State follows storage: `cachedReport` is one object (`{b64, date, filename}`) or `null`. It holds
the bytes, so the session serves the loaded report from memory and never depends on what storage
accepted. The panel needs no second flag for "stored".

The user is not told that a write was rejected. There is no honest, unintrusive way to say it,
and the drop is the message: the report is gone at the next load, which is what browser storage
promises anyway.

## Consequences

- `app.js` holds one reader (`readCachedReport`), one writer (`cacheReport`) and one remover
  (`clearStoredReport`). The `$watch` on `cachedReport` is the only caller of the last two.
- A `null` date means no report: a PDF without history carries settings only, so an upload
  applies the crawler list and stores no record.
- The three keys stay as they are, so a report cached by an earlier version still loads.
- `tests/e2e/test_pdf_workflow.py` asserts each rule: a fragment is dropped whichever key is
  missing, a rejected replace leaves nothing, and an unstored report lasts for the session.
