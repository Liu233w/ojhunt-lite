"""Convert relevant tables from legacy-db.sql (MySQL dump) into legacy.db (SQLite).

Run once from the project root:
    uv run python scripts/import_legacy.py

Output: legacy.db  (gitignored)
"""

import re
import sqlite3
import sys
from pathlib import Path

DUMP_PATH = Path("legacy-db.sql")
DB_PATH = Path("legacy.db")

# Maps MySQL table name -> (sqlite table name, {mysql_col: sqlite_col})
# Only columns we actually need are listed; the rest are discarded.
TABLE_MAP = {
    "AbpUsers": (
        "users",
        {
            "Id": "id",
            "UserName": "username",
            "EmailAddress": "email",
        },
    ),
    "AbpSettings": (
        "user_settings",
        {
            "UserId": "user_id",
            "Name": "name",
            "Value": "value",
        },
    ),
    "DefaultQueries": (
        "default_queries",
        {
            "Id": "id",
            "UserId": "user_id",
            "MainUsername": "main_username",
            "UsernamesInCrawlers": "usernames_in_crawlers",
            "IsDeleted": "is_deleted",
        },
    ),
    "QueryHistories": (
        "query_histories",
        {
            "Id": "id",
            "UserId": "user_id",
            "MainUsername": "main_username",
            "CreationTime": "creation_time",
        },
    ),
    "QuerySummaries": (
        "query_summaries",
        {
            "Id": "id",
            "QueryHistoryId": "history_id",
            "GenerateTime": "generate_time",
            "Solved": "solved",
            "Submission": "submission",
        },
    ),
    "QueryCrawlerSummaries": (
        "crawler_summaries",
        {
            "Id": "id",
            "QuerySummaryId": "summary_id",
            "CrawlerName": "crawler",
            "Solved": "solved",
            "Submission": "submission",
        },
    ),
    "UsernameInCrawler": (
        "username_in_crawler",
        {
            "Id": "id",
            "QueryCrawlerSummaryId": "crawler_summary_id",
            "FromCrawlerName": "from_crawler",
            "Username": "username",
        },
    ),
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER,
    name TEXT NOT NULL,
    value TEXT
);
CREATE INDEX IF NOT EXISTS idx_user_settings_user ON user_settings(user_id, name);

CREATE TABLE IF NOT EXISTS default_queries (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    main_username TEXT NOT NULL,
    usernames_in_crawlers TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS query_histories (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    main_username TEXT NOT NULL,
    creation_time TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_qh_user ON query_histories(user_id);
CREATE INDEX IF NOT EXISTS idx_qh_main ON query_histories(main_username);

CREATE TABLE IF NOT EXISTS query_summaries (
    id INTEGER PRIMARY KEY,
    history_id INTEGER NOT NULL,
    generate_time TEXT NOT NULL,
    solved INTEGER NOT NULL,
    submission INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_qs_history ON query_summaries(history_id);

CREATE TABLE IF NOT EXISTS crawler_summaries (
    id INTEGER PRIMARY KEY,
    summary_id INTEGER NOT NULL,
    crawler TEXT NOT NULL,
    solved INTEGER NOT NULL,
    submission INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cs_summary ON crawler_summaries(summary_id);

CREATE TABLE IF NOT EXISTS username_in_crawler (
    id INTEGER PRIMARY KEY,
    crawler_summary_id INTEGER NOT NULL,
    from_crawler TEXT,
    username TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_uic_cs ON username_in_crawler(crawler_summary_id);
"""


def _unescape_mysql(s: str) -> str:
    """Convert MySQL string escapes to Python string."""
    return (
        s.replace("\\0", "\0")
        .replace("\\'", "'")
        .replace('\\"', '"')
        .replace("\\b", "\b")
        .replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\t", "\t")
        .replace("\\Z", "\x1a")
        .replace("\\\\", "\\")
    )


def _tokenize_mysql_values(text: str):
    """Yield individual SQL value tokens from a MySQL VALUES list.

    Handles: NULL, numbers, single-quoted strings with MySQL escaping.
    Yields tokens as Python objects (None, int, float, str).
    Yields '(' and ')' as row delimiters.
    """
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in " \t\n\r,":
            i += 1
        elif c == "(":
            yield "("
            i += 1
        elif c == ")":
            yield ")"
            i += 1
        elif c == ";":
            break
        elif text[i : i + 4] == "NULL":
            yield None
            i += 4
        elif c == "'":
            # Collect string until unescaped closing quote
            j = i + 1
            buf = []
            while j < n:
                ch = text[j]
                if ch == "\\" and j + 1 < n:
                    buf.append(text[j : j + 2])
                    j += 2
                elif ch == "'":
                    if j + 1 < n and text[j + 1] == "'":
                        # SQL standard double-quote escape
                        buf.append("''")
                        j += 2
                    else:
                        j += 1
                        break
                else:
                    buf.append(ch)
                    j += 1
            raw = "".join(buf)
            yield _unescape_mysql(raw)
            i = j
        elif c in "0123456789-":
            j = i + 1
            while j < n and text[j] in "0123456789.-":
                j += 1
            tok = text[i:j]
            try:
                yield int(tok)
            except ValueError:
                try:
                    yield float(tok)
                except ValueError:
                    yield tok
            i = j
        else:
            # skip unexpected chars
            i += 1


def _parse_insert_line(line: str, col_map: dict) -> list[dict]:
    """Parse a MySQL INSERT line, returning only the requested columns.

    col_map: {mysql_col_name: sqlite_col_name}
    Returns list of {sqlite_col: value} dicts.
    """
    # Extract column list: INSERT INTO `Table` (`col1`, `col2`) VALUES ...
    col_match = re.match(r"INSERT INTO `\w+` \(([^)]+)\) VALUES (.*)", line, re.DOTALL)
    if not col_match:
        return []

    raw_cols = col_match.group(1)
    values_str = col_match.group(2)

    # Parse column names
    all_cols = [c.strip().strip("`") for c in raw_cols.split(",")]

    # Find indices of the columns we want
    wanted_indices = {}
    for mysql_col, sqlite_col in col_map.items():
        if mysql_col in all_cols:
            wanted_indices[all_cols.index(mysql_col)] = sqlite_col

    if not wanted_indices:
        return []

    rows = []
    current_row = []
    in_row = False

    for tok in _tokenize_mysql_values(values_str):
        if tok == "(":
            in_row = True
            current_row = []
        elif tok == ")":
            if in_row and current_row:
                row = {
                    sqlite_col: current_row[idx]
                    for idx, sqlite_col in wanted_indices.items()
                    if idx < len(current_row)
                }
                rows.append(row)
            in_row = False
            current_row = []
        elif in_row:
            current_row.append(tok)

    return rows


def main() -> None:
    if not DUMP_PATH.exists():
        print(
            f"ERROR: {DUMP_PATH} not found. Run from the project root.", file=sys.stderr
        )
        sys.exit(1)

    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing {DB_PATH}")

    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA_SQL)
    con.commit()

    insert_sql: dict[str, tuple] = {}
    for mysql_table, (sqlite_table, col_map) in TABLE_MAP.items():
        cols = list(col_map.values())
        placeholders = ", ".join("?" * len(cols))
        sql = f"INSERT INTO {sqlite_table} ({', '.join(cols)}) VALUES ({placeholders})"
        insert_sql[mysql_table] = (sql, cols, col_map)

    counts: dict[str, int] = {t: 0 for t in TABLE_MAP}

    print(f"Reading {DUMP_PATH} ({DUMP_PATH.stat().st_size // 1_048_576} MB)...")

    with DUMP_PATH.open("r", encoding="utf-8", errors="replace") as f:
        for lineno, line in enumerate(f, 1):
            line = line.rstrip("\n")
            # Detect INSERT INTO `TableName`
            m = re.match(r"INSERT INTO `(\w+)`", line)
            if not m:
                continue
            mysql_table = m.group(1)
            if mysql_table not in TABLE_MAP:
                continue

            sql, cols, col_map = insert_sql[mysql_table]
            print(
                f"  Parsing {mysql_table} (line {lineno}, {len(line) // 1024} KB)...",
                end="",
                flush=True,
            )

            rows = _parse_insert_line(line, col_map)

            with con:
                con.executemany(sql, [[row.get(c) for c in cols] for row in rows])

            counts[mysql_table] += len(rows)
            print(f" {len(rows):,} rows")

    con.close()

    print("\nDone. Row counts:")
    for mysql_table, (sqlite_table, _) in TABLE_MAP.items():
        print(f"  {sqlite_table}: {counts[mysql_table]:,}")


if __name__ == "__main__":
    main()
