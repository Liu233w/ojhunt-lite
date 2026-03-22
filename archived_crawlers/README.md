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
| cses | Requires numeric user ID; no public solved count |
| dashiye (HYSBZ) | Site dead (2010-2020) |
| eljudge (EIJudge) | Domain repurposed (acm.mipt.ru is now MIPT CS department homepage, OJ no longer exists) |
| fzu | Site dead (2012-2021) |
| hihocoder | Site dead (HTTPS SSL certificate expired, connection fails) |
| hit | Site unreachable |
| hrbust | Site unreachable |
| jisuanke | Alibaba Cloud WAF blocks all automated requests (HTTP 405 for all paths) |
| leetcode_cn | Cloudflare bot protection |
| lightoj | **Revived** — moved to active crawlers (`crawlers/lightoj.py`); public REST API available |
| nod (51Nod) | **Revived** — moved to active crawlers (`crawlers/nod.py`); requires numeric userId (no public username lookup) |
| openjudge | Requires authentication; user data is group-scoped with no global stats (group-based OJ) |
| poj | Site dead (connection refused) |
| qoj | Cloudflare bot protection (JS challenge); profile page is public but requires browser rendering (UOJ-based) |
| scu | Temporary system maintenance shutdown (server alive but OJ intentionally offline) |
| spoj | Cloudflare bot protection |
| szkopul | Platform does not expose public user profiles |
| topcoder | Arena shut down July 2024 |
| usaco | No public user profiles |
| uvalive | Site dead |
| zoj | Migrated to pintia.cn, requires authentication |
| ztrening | Site dead (connection refused) |
| hackerrank | Akamai WAF blocks all non-browser automated requests (403 Forbidden); API is accessible via real browser but not aiohttp |
| nbut | SSL certificate expired on ac.2333.moe, site neglected |
| uestc (CDOJ) | Migrated from Lutece to Hydro at cdoj.site; old oj.uestc.edu.cn is dead; Cerberus JS PoW challenge likely protects API endpoints |

These crawlers are kept for reference and may be restored if the issues are resolved.
