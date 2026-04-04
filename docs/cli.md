# CLI Reference

## Installation

**Install once, use anywhere:**

```bash
pipx install ojhunt          # recommended: isolated environment, always on PATH
uv tool install ojhunt       # same, uv-native
pip install ojhunt           # global install
```

**Run directly from a clone** (useful for development or trying it out):

```bash
git clone https://github.com/Liu233w/ojhunt-lite
cd ojhunt-lite
uv sync
uv run ojhunt tourist@codeforces
```

**Run via container** (no Python install required; `docker` and `podman` are interchangeable):

```bash
# Basic query
docker run --rm ghcr.io/liu233w/ojhunt-lite tourist@codeforces

# Login-required crawlers — use -l flag, same as local CLI
docker run --rm ghcr.io/liu233w/ojhunt-lite -l myuser:mypass@vjudge -- target@vjudge

# JSON output
docker run --rm ghcr.io/liu233w/ojhunt-lite --json tourist@codeforces
```

---

## Basic Usage

```bash
# Query single crawler
ojhunt tourist@codeforces

# Query multiple crawlers
ojhunt tourist@codeforces tourist@atcoder

# Use default username for multiple queries
ojhunt -d tourist -- codeforces atcoder

# Query all platforms
ojhunt -d tourist -a

# List available crawlers with details
ojhunt --list
```

Run `ojhunt --help` to see all available options.

## Login-Required Crawlers

Some crawlers require authentication. There are two distinct types:

### Own Account — Login to see your own data

The platform only shows your statistics when you are logged in. You must log in *as the target user* to query their stats.

```bash
# Login as myuser and query myuser's own data
ojhunt myuser:mypass@qoj
```

The `-l` flag is not applicable here — there is no way to query another user's stats from this type of platform.

### Shared Account — Login as any account to query anyone

The platform requires authentication, but once logged in you can view *any* user's statistics. A single account can query arbitrary users.

```bash
# Login as yourself, query your own stats
ojhunt myuser:mypass@vjudge

# Login as yourself, query someone else
ojhunt -l myuser:mypass@vjudge -- target_user@vjudge

# Multiple login-required crawlers
ojhunt -l user1:pass1@vjudge -l user2:pass2@otheroj -- target1@vjudge target2@otheroj
```

Use `ojhunt --list` to see which crawlers require login and their login type.

## Credential Parsing

**Format:** `user:pass@crawler`

- First `:` separates username from password
- Last `@` separates credentials from crawler name

Examples:
- `user:pass@vjudge` → username=`user`, password=`pass`, crawler=`vjudge`
- `user:p@ss:word@vjudge` → username=`user`, password=`p@ss:word`, crawler=`vjudge`

**Error cases:**
- Querying a login-required crawler without credentials → error
- Using both embedded password and `-l` flag for the same crawler → error (duplicate credentials)
- Providing credentials for a crawler that doesn't need them → error

## JSON Output

Use `--json` to get machine-readable output:

```bash
ojhunt --json tourist@codeforces tourist@atcoder
```

Progress messages are redirected to stderr when `--json` is used, so stdout contains only the JSON result.
