# Fixing All Offline Crawlers

You are the **coordinator**. You pick the crawlers and run one fixer agent per crawler. You don't
fix crawlers yourself, because each fix needs its own context for probing the site.

## 1. Get the offline list

```bash
curl -s https://ojhunt.com/api/crawlers | python3 -c '
import json, sys
for name, c in json.load(sys.stdin)["data"].items():
    if c["status"] == "offline":
        print(name, "|", c["statusError"])'
```

The server checks each crawler with its `test_username` once every 2 hours, so a status can be
up to 2 hours old. `waiting` means the check has not run yet. It is not a failure.

## 2. Pick the crawlers worth fixing

Skip a crawler when:

- **It is in the "Offline but kept" table in `archived_crawlers/README.md`.** It fails only from
  the ojhunt.com server.
- **Its error is `Login credentials not configured`.** That is server configuration, not code.

Show the user the remaining list with each error before you spawn anything.

## 3. Run one fixer agent per crawler, at most 3 at a time

- **Keep at most 3 fixers running at once**, unless the user gives another number. Start the
  next fixer only when a running one reports back. More fixers at once hit the sites and the
  rate limits harder and make the results harder to review.
- **Spawn each fixer with `isolation: "worktree"`.** Parallel fixers in one checkout would
  overwrite each other's `.doit/test-crawler.log` and git index.
- **Spawn fixers in the background.** You are notified when each one finishes. Don't poll.

Give each fixer this prompt, with the placeholders filled in:

```text
Fix the <name> crawler. ojhunt.com reports it offline with: <statusError>

1. Run `git reset --hard <coordinator's current branch>` first. The worktree may start on
   another branch.
2. Invoke the ojhunt-crawlers skill and follow "Debugging a Broken Crawler". Spawn your own
   background agents for site probing as that section says.
3. Run `./doit.sh test-crawler <name>` before you change anything. If it already passes,
   don't change code. Report that it passes locally.
4. Do one of these:
   - Fix the crawler and get all its tests to pass.
   - If the test user is gone, pick a live user and update `test_username`.
   - If the site is dead or WAF-blocked, archive the crawler (docs/dev/crawlers.md,
     "Archived crawlers", and the Step 6 checklist).
   Don't try to get past a WAF challenge (`cf-mitigated: challenge`), and don't ask
   probe agents to. Use another public page, or archive.
5. Run `./doit.sh lint` and `./doit.sh test-unit`. Then invoke the ojhunt-commit skill and
   commit in this worktree. Don't push. Skills report the main checkout as their base
   directory, so pin every `git -C` to this worktree's root (`pwd` at the start) instead.
6. Report: the outcome (fixed / test user changed / archived / passes locally / not fixed),
   the cause in one sentence, and the commit's short SHA.
```

## 4. Collect the results

- **Cherry-pick each fixer's commit onto your branch**, using the short SHA it reported.
  Archive commits often conflict on the crawler counts in `docs/BACKLOG.md` and
  `docs/library.md`. After the last cherry-pick, run `./doit.sh gen-docs`, `lint` and
  `test-unit`, and run `./doit.sh test-crawler <name>` again for each fixed crawler.
  Put corrections in `fixup!` commits.
- **Collect findings outside each fixer's task.** Ask the user whether to fix each one now
  or add it to `docs/BACKLOG.md`.
- **"Passes locally" means the failure is probably only on the server.** Ask the user whether
  to add the crawler to the "Offline but kept" table.
- **Report a table to the user**: crawler, outcome, cause.
