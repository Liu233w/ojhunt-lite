# Deployment & operations

## System fonts for PDF generation

PDF generation uses Unicode fonts to support non-latin usernames (CJK, Arabic, Hebrew, etc.).
The font is discovered at startup from the host system — no font files are bundled.

**Linux / Docker** — install both packages:

```bash
apt-get install fonts-noto fonts-noto-cjk-core
```

The `Containerfile` already includes this step, so production builds work out of the box.
For local Linux development, install the packages once and restart the server.

**macOS** — Arial Unicode (`/Library/Fonts/Arial Unicode.ttf`) is used automatically; no
extra steps needed.

**Neither font found** — the PDF generator falls back to Helvetica (latin-1 only). Non-latin
characters will raise an error.

## Deploying legacy.db

The `/pdf/legacy` page reads `legacy.db` from the current working directory at runtime.
The app works normally if the file is absent — the export form is simply disabled.

**Local**: place `legacy.db` in the project root.

**Docker / Podman**: mount the file at `/app/legacy.db` using an **absolute path**:
```bash
docker run -v $(pwd)/legacy.db:/app/legacy.db:ro <image>
```

The `legacy.db` file is gitignored — it contains personal data and must never be committed.
Generate it from the MySQL dump with:
```bash
uv run python scripts/import_legacy.py
```

## PDF preview

Generate preview PDFs with 1, 10, 30, and 100 history entries for visual inspection:

```bash
uv run python scripts/generate_preview_pdf.py
# Writes preview_001_entries.pdf … preview_100_entries.pdf in scripts/previews/ (gitignored)
```
