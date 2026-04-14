# OJHunt Lite

A lightweight async Python tool for querying Online Judge (OJ) statistics across multiple platforms. Track your accepted problems and total submissions from competitive programming sites.

- Async/concurrent requests via `aiohttp`
- CLI and web interface
- BSD-2 Licensed

## CLI

**Install once, use anywhere** (pipx, uv tool, or pip):

```bash
pipx install ojhunt
# or: uv tool install ojhunt
# or: pip install ojhunt
```

**Run directly from a clone** (no install needed):

```bash
git clone https://github.com/Liu233w/ojhunt-lite
cd ojhunt-lite
uv run ojhunt tourist@codeforces
```

**Run via container** (no Python needed):

```bash
docker run --rm ghcr.io/liu233w/ojhunt-lite tourist@codeforces
```

Example output:

```bash
$ ojhunt tourist@codeforces tourist@atcoder
Querying CodeForces...
Querying AtCoder...
AtCoder done (1051 solved, 1.25s)
CodeForces done (2962 solved, 2.78s)

Total: 2962 solved / 6437 submissions

┏━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Crawler    ┃ Username ┃ Solved ┃ Submissions ┃ Status     ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ CodeForces │ tourist  │   2962 │        5386 │ OK (2.78s) │
│ AtCoder    │ tourist  │   1051 │        1051 │ OK (1.25s) │
└────────────┴──────────┴────────┴─────────────┴────────────┘
Completed: 2 OK, 0 failed (2.78s total)
```

Full CLI reference, login-required crawlers, and JSON output: **[docs/cli.md](docs/cli.md)**

## Web Interface

The web interface is designed to be self-hosted. Clone the repo and deploy:

```bash
git clone https://github.com/Liu233w/ojhunt-lite
cd ojhunt-lite
uv sync
uv run fastapi run src/ojhunt/web/app.py --port 8080
```

Container images are available at `ghcr.io/liu233w/ojhunt-lite` — see [docs/web.md](docs/web.md).

## Use Crawlers in Your Code

Add `ojhunt` as a project dependency:

```bash
uv add ojhunt
# or: pip install ojhunt
```

**Sync (simplest):**

```python
from ojhunt.crawlers.codeforces import query
from ojhunt.crawlers import query_sync
```

```python notest
result = query_sync(query, "tourist")
print(result.solved, result.submissions, result.solved_list)
```

**Async (when you already have an event loop):**

```python
import asyncio, aiohttp
from ojhunt.crawlers.codeforces import query
from ojhunt.crawlers import CrawlerResult
```

```python notest
async def main():
    async with aiohttp.ClientSession() as session:
        result = CrawlerResult.from_dict(await query(session, "tourist"))
        print(result.solved, result.submissions, result.solved_list)

asyncio.run(main())
```

`query_sync` and `CrawlerResult` work with any crawler in `ojhunt.crawlers.*`.
Some crawlers (`nit`, `uva`) use a persistent label cache and require the full package — they cannot be used as standalone copied files.

## Supported Platforms

See the [src/ojhunt/crawlers/](./src/ojhunt/crawlers) directory. Archived crawlers (dead sites) are in [archived_crawlers/](./archived_crawlers).

## Development

Adding crawlers, running tests, templates: **[docs/development.md](docs/development.md)**

## License

BSD 2-Clause License — see individual crawler files for full license text.

## Credits

Lightweight Python rewrite of [OJHunt (acm-statistics)](https://github.com/Liu233w/acm-statistics),
originally inspired by 西北工业大学ACM查询系统 (npuacm.info) by [Jiduo Zhang](https://kidozh.com).

Special thanks to test account providers: @leoloveacm, @2013300262
