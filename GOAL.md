# OJHunt Lite - Project Vision

## Background

OJHunt Lite is a simplified async Python rewrite of [acm-statistics](https://github.com/liu233w/acm-statistics), focusing on the core functionality: querying accepted problems (AC) and submission counts across multiple Online Judge platforms.

## Design Philosophy

### Lightweight
- **Minimal dependencies**: Only `aiohttp` library for HTTP operations
- **No heavy parsing libraries**: Use standard library (`xml.dom.minidom`, `json`, regex) instead of BeautifulSoup or lxml
- **Simple, readable code**: Easy to understand, maintain, and modify
- **Fast startup**: No complex framework initialization

### Async by Design
- **Built on asyncio**: All crawlers use `async/await` for efficient concurrent execution
- **Non-blocking I/O**: Query multiple platforms simultaneously without thread overhead
- **Future-proof**: Ready for FastAPI integration and web service deployment
- **Better performance**: Especially when querying many platforms at once

### Maintainable
- **Consistent interfaces**: All crawlers follow the same pattern
- **Self-contained modules**: Each crawler can work independently
- **Comprehensive tests**: pytest-asyncio tests for each crawler ensure reliability
- **Clear documentation**: Both code-level and user-facing docs

### Flexible
- **Multiple use cases**: Support standalone modules, CLI, and future web interface
- **Easy to extend**: Adding new crawlers follows a simple template
- **BSD-2 License**: Encourages reuse and modification

## Use Cases

### 1. Self-Contained Crawler Modules ✅ (Current)

**Goal**: Each crawler can be downloaded and used independently in any Python project.

**Requirements**:
- ✅ Each module depends only on `aiohttp`
- ✅ BSD-2 license header (2026) in every file
- ✅ Uniform function interface: `async def query(username: str) -> dict`
- ✅ Metadata embedded in `__crawler_meta__` variable
- ✅ pytest-asyncio tests in `test_<crawler>.py` files

**Usage Example**:
```python
import asyncio
from crawlers.codeforces import query

async def main():
    result = await query("tourist")
    print(f"Solved: {result['solved']}")

asyncio.run(main())
```

### 2. Command-Line Tool ✅ (Current)

**Goal**: Clone the repository and use it as a command-line tool to query multiple platforms concurrently.

**Requirements**:
- ✅ Single entrypoint: `ojhunt.py`
- ✅ Auto-discovery of all crawlers in the package
- ✅ Concurrent execution using `asyncio.gather()`
- ✅ Flexible query options:
  - Query all platforms with one username
  - Query specific platforms with specific usernames
  - Mix and match: use 2 accounts for the same platform
- ✅ Clear output formatting

**Usage Example**:
```bash
# Query all platforms concurrently
python ojhunt.py --username myname --all

# Query specific platforms
python ojhunt.py \
  --crawler codeforces --username tourist \
  --crawler poj --username vjudge5

# All requests execute concurrently with async
```

### 3. Web Application 🔮 (Future)

**Goal**: Deploy as a web service with REST API and HTMX frontend.

**Requirements** (To be implemented):
- ⏳ FastAPI backend with async endpoints
- ⏳ Leverage existing async crawlers (no refactoring needed!)
- ⏳ HTMX frontend for progressive enhancement
- ⏳ Real-time streaming of crawler results as they complete
- ⏳ Retry functionality for failed requests
- ⏳ Summary report with AC/Submissions per account-crawler pair
- ⏳ PDF export via browser print functionality
- ⏳ Proper PDF naming for archival purposes (sortable by date)

**Design Principles**:
- **Stateless architecture**: No server-side user data storage
- **Client-side ownership**: Users store their own PDF records
- **Privacy-focused**: No user accounts or tracking
- **Ephemeral comparisons**: Compare users in real-time without storing data
- **PDF-based archival**: Users maintain their own historical records on their devices

## Current Status

**Phase 1: Core Crawlers & CLI** (Completed ✅)
- [x] Project structure and documentation
- [x] Migrate all 28 crawlers from JavaScript to async Python with BeautifulSoup4
- [x] Create comprehensive pytest-asyncio tests
- [x] Implement async CLI with concurrent execution
- [x] End-to-end testing

**Phase 2: Web Interface** (Planned)
- [ ] FastAPI backend implementation
- [ ] HTMX frontend development
- [ ] Streaming responses for progressive display
- [ ] Deployment documentation
- [ ] Docker containerization

**Phase 3: Simple & Stateless Features** (Future)
- [ ] In-memory caching for repeated requests (no database)
- [ ] API rate limiting (in-memory only)
- [ ] Monitoring and observability (metrics, not user data)
- [ ] Ephemeral user comparison (compare multiple users without storing)
- [ ] Advanced PDF formatting options (let users customize their exports)
- [ ] Batch export functionality (multiple users → single PDF)

## Technical Decisions

### Why Python?
- Better for web scraping and data processing
- Rich standard library reduces dependencies
- Native async/await support for concurrent operations
- Better ecosystem for data visualization (future)
- FastAPI integration is seamless with async code

### Why Async/Await?
- **Performance**: Query 29 platforms concurrently in seconds, not minutes
- **Scalability**: FastAPI web service can handle many concurrent users
- **Resource efficient**: Non-blocking I/O uses far less memory than threads
- **Modern**: Python's async ecosystem is mature and well-supported

### Why aiohttp over requests?
- Native async support (requests is synchronous)
- Better performance for concurrent requests
- Lower memory footprint
- Standard choice for async HTTP in Python

### Why BeautifulSoup4 for HTML Parsing?
- **Maintainability**: Self-documenting code vs cryptic regex
- **Robustness**: Handles malformed HTML gracefully
- **Simplicity**: `soup.find('tag')` vs `re.search(r'<tag[^>]*>(.*?)</tag>')`
- **Still lightweight**: Pure Python, ~100KB, no C compilation
- **Industry standard**: Used by thousands of projects
- **Trade-off**: One more dependency, but worth it for long-term maintainability

### Why Minimal Dependencies (Just 2)?
- Faster installation and startup
- Fewer security vulnerabilities
- Easier to understand and debug
- More portable across different environments
- Each crawler still self-contained (only aiohttp + beautifulsoup4)

### Why BSD-2 License?
- Permissive license encourages reuse
- Compatible with most projects
- Simple and well-understood terms

## Contributing

When adding new crawlers:
1. Follow the template in existing crawlers
2. Use only `aiohttp` for HTTP operations (with async/await)
3. For HTML parsing, use `beautifulsoup4` (not regex) for maintainability
4. Use standard library for JSON parsing, simple validation
5. Include comprehensive pytest-asyncio tests with real usernames
6. Add metadata from config.yml to `__crawler_meta__`
7. Document any platform-specific quirks
8. Ensure proper error handling (ValueError for user not found, RuntimeError for other errors)

## Success Criteria

The project is successful when:
1. ✅ All 28 crawlers are migrated and working with async + BeautifulSoup4
2. ✅ CLI tool can query any combination of platforms concurrently
3. ✅ Each crawler can be used standalone in other projects
4. ✅ Code is maintainable with BeautifulSoup4 (no fragile regex)
5. ⏳ Web interface provides easy access for non-technical users
6. ⏳ Active community contributes new crawlers
7. ⏳ Tool is used by competitive programmers worldwide

## Performance Benefits

Async implementation provides significant advantages:

**Sequential (old requests-based):**
- Query 10 platforms: ~30-60 seconds (3-6s each)
- Blocked waiting for each response

**Concurrent (async aiohttp):**
- Query 10 platforms: ~5-10 seconds (all at once)
- Limited only by slowest platform
- 3-6x faster in practice

This becomes even more dramatic when querying all 29 platforms!
