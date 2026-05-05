# Archived Crawlers

These crawlers have been archived due to:

1. **Dead sites** - The OJ platform is no longer operational
2. **Bot protection** - The site blocks automated requests (Cloudflare, etc.)
3. **Unfixable issues** - API changes that cannot be worked around
4. **Authentication required** - User profiles require login

## Archived Crawlers

| Crawler | Reason |
|---------|--------|
| acdream | Domain dead (DNS does not resolve) |
| bzoj | Cerberus JS PoW challenge (bot protection); use darkbzoj crawler instead |
| csacademy | SPA uses WebSocket for data, not scrapable via HTTP |
| dashiye (HYSBZ) | Site dead (2010-2020) |
| eljudge (EIJudge) | Domain repurposed (acm.mipt.ru is now MIPT CS department homepage, OJ no longer exists) |
| fzu | Site dead (2012-2021) |
| baekjoon | Platform shut down (acmicpc.net terminated service 2026-04-28; solved.ac API also returns 403) |
| hihocoder | Server-side PHP fatal error on all user profile pages (avatarUrl() on null); ssl=False bypasses expired cert but application data is unavailable |
| hit | Site unreachable |
| hrbust | Site unreachable |
| jisuanke | Alibaba Cloud WAF blocks all automated requests (HTTP 405 for all paths) |
| leetcode_cn | Cloudflare bot protection |
| openjudge | Requires authentication; user data is group-scoped with no global stats (group-based OJ) |
| qoj | Cloudflare bot protection (JS challenge); profile page is public but requires browser rendering (UOJ-based) |
| scu | Temporary system maintenance shutdown (server alive but OJ intentionally offline) |
| spoj | Cloudflare bot protection |
| szkopul | Platform does not expose public user profiles |
| topcoder | Arena shut down July 2024 |
| usaco | Contest-based platform with no "problems solved" count; no public user profiles by username; per-contest scores only accessible via 50+ contest result pages after login |
| uvalive | Site dead |
| zoj | Migrated to pintia.cn, requires authentication |
| ztrening | Site dead (connection refused) |
| hackerearth | Cloudflare WAF blocks all non-browser automated requests; profile page is a React SPA with API calls blocked by Cloudflare bot protection |
| hackerrank | Akamai WAF blocks all non-browser automated requests (403 Forbidden); API is accessible via real browser but not aiohttp |
| uestc (CDOJ) | Migrated from Lutece to Hydro at cdoj.site; old oj.uestc.edu.cn is dead; Cerberus JS PoW challenge likely protects API endpoints |
| dmoj | Anti-bot protection — API and submissions page both return HTTP 403 (same pattern as hackerrank) |
| kattis | Not solved/submission based — uses a difficulty-score system instead of problem count |

These crawlers are kept for reference and may be restored if the issues are resolved.
