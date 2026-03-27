# OJHunt Lite

A lightweight async Python tool for querying Online Judge (OJ) statistics across multiple platforms. Track your accepted problems and total submissions from competitive programming sites.

- Async/concurrent requests via `aiohttp`
- CLI and web interface
- Self-contained crawlers — each file can be used independently
- Only depends on `aiohttp` and `selectolax`
- BSD-2 Licensed

## Quick Example

```bash
$ uv run ojhunt.py tourist@codeforces tourist@atcoder
Querying CodeForces...
Querying AtCoder...
AtCoder done (1051 solved, 1.25s)
CodeForces done (2962 solved, 2.78s)

Total: 2962 solved / 6437 submissions

================================================================================
Crawler              Username             Solved     Submissions  Status
================================================================================
CodeForces           tourist              2962       5386         OK (2.78s)
AtCoder              tourist              1051       1051         OK (1.25s)
================================================================================
Completed: 2 OK, 0 failed (2.78s total)
```

## Installation

```bash
git clone https://github.com/Liu233w/ojhunt-lite
cd ojhunt-lite
uv sync
```

Container images are available at `ghcr.io/liu233w/ojhunt-lite` — see [docs/web.md](docs/web.md).

## Usage

### CLI

```bash
uv run ojhunt.py tourist@codeforces tourist@atcoder
uv run ojhunt.py -d tourist -- codeforces atcoder   # default username
uv run ojhunt.py --list                              # list available crawlers
```

Full CLI reference, login-required crawlers, and JSON output: **[docs/cli.md](docs/cli.md)**

### Web Interface

```bash
uv run fastapi dev web/app.py --port 8080
```

Web UI, API docs, and container setup: **[docs/web.md](docs/web.md)**

### Use Crawlers in Your Code

```python
import asyncio, aiohttp
from crawlers.codeforces import query

async def main():
    async with aiohttp.ClientSession() as session:
        result = await query(session, "tourist")
        print(result["solved"], result["submissions"], result["solved_list"])

asyncio.run(main())
```

## Supported Platforms

See the [crawlers/](./crawlers) directory. Archived crawlers (dead sites) are in [archived_crawlers/](./archived_crawlers).

## Development

Adding crawlers, running tests, templates: **[docs/development.md](docs/development.md)**

## License

BSD 2-Clause License — see individual crawler files for full license text.

## Credits

Lightweight Python rewrite of [OJHunt (acm-statistics)](https://github.com/Liu233w/acm-statistics),
originally inspired by [西北工业大学ACM查询系统](https://kidozh.com/en/) by Jiduo Zhang.

Special thanks to test account providers: @leoloveacm, @2013300262
