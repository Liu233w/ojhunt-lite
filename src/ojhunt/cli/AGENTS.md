# AGENTS.md - CLI

## Login-Required Crawlers (CLI Usage)

For `shared_account` crawlers, tests read credentials from `.env` automatically — no need to extract them manually. If `.env` doesn't exist, create it first with the relevant credentials.

The CLI test pattern for shared-account crawlers:
```bash
uv run ojhunt -l username:password@<crawler> -- target_user@<crawler>
```

To discover which crawlers require login:
```bash
uv run ojhunt --list --json | jq 'with_entries(select(.value.login_type | contains("account")))'
```
