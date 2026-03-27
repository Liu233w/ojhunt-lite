# CLI Reference

## Basic Usage

```bash
# Query single crawler
uv run ojhunt.py tourist@codeforces

# Query multiple crawlers
uv run ojhunt.py tourist@codeforces tourist@atcoder

# Use default username for multiple queries
uv run ojhunt.py -d tourist -- codeforces atcoder

# Query all platforms
uv run ojhunt.py -d tourist -a

# List available crawlers with details
uv run ojhunt.py --list
```

Run `uv run ojhunt.py --help` to see all available options.

## Login-Required Crawlers

Some crawlers require authentication. There are two distinct types:

### Own Account — Login to see your own data

The platform only shows your statistics when you are logged in. You must log in *as the target user* to query their stats.

```bash
# Login as myuser and query myuser's own data
uv run ojhunt.py myuser:mypass@qoj
```

The `-l` flag is not applicable here — there is no way to query another user's stats from this type of platform.

### Shared Account — Login as any account to query anyone

The platform requires authentication, but once logged in you can view *any* user's statistics. A single account can query arbitrary users.

```bash
# Login as yourself, query your own stats
uv run ojhunt.py myuser:mypass@vjudge

# Login as yourself, query someone else
uv run ojhunt.py -l myuser:mypass@vjudge -- target_user@vjudge

# Multiple login-required crawlers
uv run ojhunt.py -l user1:pass1@vjudge -l user2:pass2@otheroj -- target1@vjudge target2@otheroj
```

Use `uv run ojhunt.py --list` to see which crawlers require login and their login type.

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
uv run ojhunt.py --json tourist@codeforces tourist@atcoder
```

Progress messages are redirected to stderr when `--json` is used, so stdout contains only the JSON result.
