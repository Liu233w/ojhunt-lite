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

Full reference — every crawler, its login requirements and arguments: **[docs/library.md](docs/library.md)**. The same text is available from a Python prompt:

```python
from ojhunt.crawlers import crawlers
```

```python notest
help(crawlers["cses"])   # what it queries, login, arguments
help(crawlers.cses)      # the same crawler, as an attribute
```

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

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars.githubusercontent.com/u/126860030?v=4" width="100px;" alt=""/><br /><sub><a href="https://github.com/nopostpone"><b>==</b></a><a href="https://github.com/nopostpone">🔗</a></sub><br /><a href="https://github.com/Liu233w/ojhunt-lite/issues?q=author%3Anopostpone" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars0.githubusercontent.com/u/22635759?v=4" width="100px;" alt=""/><br /><sub><a href="https://www.cometeme.tech"><b>Adelard Collins</b></a><a href="https://github.com/cometeme">🔗</a></sub><br /><a href="https://github.com/Liu233w/ojhunt-lite/issues?q=author%3Acometeme" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars1.githubusercontent.com/u/64258212?v=4" width="100px;" alt=""/><br /><sub><a href="https://github.com/BackSlashDelta"><b>BackSlashDelta</b></a><a href="https://github.com/BackSlashDelta">🔗</a></sub><br /><a href="https://github.com/Liu233w/ojhunt-lite/issues?q=author%3ABackSlashDelta" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars0.githubusercontent.com/u/35862184?v=4" width="100px;" alt=""/><br /><sub><a href="https://github.com/bodhisatan"><b>Bodhisatan_Yao</b></a><a href="https://github.com/bodhisatan">🔗</a></sub><br /><a href="https://github.com/Liu233w/ojhunt-lite/issues?q=author%3Abodhisatan" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars.githubusercontent.com/u/81847?v=4" width="100px;" alt=""/><br /><sub><a href="https://anthropic.com/claude-code"><b>Claude</b></a><a href="https://github.com/claude">🔗</a></sub><br /><a href="https://github.com/Liu233w/ojhunt-lite/commits?author=claude" title="Code">💻</a> <a href="#infra-claude" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="https://github.com/Liu233w/ojhunt-lite/commits?author=claude" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars3.githubusercontent.com/u/25352156?v=4" width="100px;" alt=""/><br /><sub><a href="https://github.com/Geekxiong"><b>Geekxiong</b></a><a href="https://github.com/Geekxiong">🔗</a></sub><br /><a href="#ideas-Geekxiong" title="Ideas, Planning, & Feedback">🤔</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars2.githubusercontent.com/u/39403985?v=4" width="100px;" alt=""/><br /><sub><a href="https://github.com/settings/profile"><b>Halorv</b></a><a href="https://github.com/Halorv">🔗</a></sub><br /><a href="#ideas-Halorv" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars3.githubusercontent.com/u/11661760?v=4" width="100px;" alt=""/><br /><sub><a href="https://kidozh.com"><b>Kido Zhang</b></a><a href="https://github.com/kidozh">🔗</a></sub><br /><a href="#infra-kidozh" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="#ideas-kidozh" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars2.githubusercontent.com/u/16333687?v=4" width="100px;" alt=""/><br /><sub><a href="https://liu233w.github.io"><b>Liu233w</b></a><a href="https://github.com/Liu233w">🔗</a></sub><br /><a href="https://github.com/Liu233w/ojhunt-lite/commits?author=Liu233w" title="Code">💻</a> <a href="#ideas-Liu233w" title="Ideas, Planning, & Feedback">🤔</a> <a href="#infra-Liu233w" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="https://github.com/Liu233w/ojhunt-lite/commits?author=Liu233w" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars1.githubusercontent.com/u/55663936?v=4" width="100px;" alt=""/><br /><sub><a href="https://github.com/Meulsama"><b>Meulsama</b></a><a href="https://github.com/Meulsama">🔗</a></sub><br /><a href="#ideas-Meulsama" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars3.githubusercontent.com/u/50655871?v=4" width="100px;" alt=""/><br /><sub><a href="https://github.com/UserUnknownX"><b>Michael Xiang</b></a><a href="https://github.com/UserUnknownX">🔗</a></sub><br /><a href="https://github.com/Liu233w/ojhunt-lite/issues?q=author%3AUserUnknownX" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars1.githubusercontent.com/u/11994295?v=4" width="100px;" alt=""/><br /><sub><a href="http://zhao.wtf"><b>Zhao</b></a><a href="https://github.com/2512821228">🔗</a></sub><br /><a href="https://github.com/Liu233w/ojhunt-lite/issues?q=author%3A2512821228" title="Bug reports">🐛</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars.githubusercontent.com/u/19774268?v=4" width="100px;" alt=""/><br /><sub><a href="https://dreamer.blue/"><b>bLue</b></a><a href="https://github.com/dreamerblue">🔗</a></sub><br /><a href="https://github.com/Liu233w/ojhunt-lite/commits?author=dreamerblue" title="Code">💻</a></td>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars.githubusercontent.com/u/49401963?v=4" width="100px;" alt=""/><br /><sub><a href="https://github.com/bluebear4"><b>bluebear4</b></a><a href="https://github.com/bluebear4">🔗</a></sub><br /><a href="https://github.com/Liu233w/ojhunt-lite/issues?q=author%3Abluebear4" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars3.githubusercontent.com/u/22322656?v=4" width="100px;" alt=""/><br /><sub><a href="https://github.com/ctuu"><b>ct</b></a><a href="https://github.com/ctuu">🔗</a></sub><br /><a href="https://github.com/Liu233w/ojhunt-lite/issues?q=author%3Actuu" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars2.githubusercontent.com/u/9880740?v=4" width="100px;" alt=""/><br /><sub><a href="https://github.com/flylai"><b>flylai</b></a><a href="https://github.com/flylai">🔗</a></sub><br /><a href="https://github.com/Liu233w/ojhunt-lite/commits?author=flylai" title="Code">💻</a> <a href="https://github.com/Liu233w/ojhunt-lite/issues?q=author%3Aflylai" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars3.githubusercontent.com/u/36151020?v=4" width="100px;" alt=""/><br /><sub><a href="https://github.com/fzu-h4cky"><b>fzu-h4cky</b></a><a href="https://github.com/fzu-h4cky">🔗</a></sub><br /><a href="https://github.com/Liu233w/ojhunt-lite/issues?q=author%3Afzu-h4cky" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars.githubusercontent.com/u/42441490?v=4" width="100px;" alt=""/><br /><sub><a href="https://github.com/wwawwaww"><b>wwawwaww</b></a><a href="https://github.com/wwawwaww">🔗</a></sub><br /><a href="https://github.com/Liu233w/ojhunt-lite/issues?q=author%3Awwawwaww" title="Bug reports">🐛</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="16.66%"><img src="https://avatars2.githubusercontent.com/u/43291744?v=4" width="100px;" alt=""/><br /><sub><a href="https://github.com/zby0327"><b>zby</b></a><a href="https://github.com/zby0327">🔗</a></sub><br /><a href="#ideas-zby0327" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/Liu233w/ojhunt-lite/issues?q=author%3Azby0327" title="Bug reports">🐛</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!