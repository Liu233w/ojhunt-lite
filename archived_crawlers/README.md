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
| csu | OJ backend gone: every `vlab.csu.edu.cn/oj/` page returns nginx 502 Bad Gateway since the portal was rebuilt (Nov 2026); no new OJ location found |
| dashiye (HYSBZ) | Site dead (2010-2020) |
| eljudge (EIJudge) | Domain repurposed (acm.mipt.ru is now MIPT CS department homepage, OJ no longer exists) |
| fzu | Site dead (2012-2021) |
| baekjoon | Platform shut down (acmicpc.net terminated service 2026-04-28; solved.ac API also returns 403) |
| hihocoder | Two PHP fatal errors block all data: `/user/{id}` crashes before stats render (null avatarUrl); `/api/*` crashes on missing Duoshuo vendor class (Duoshuo shut down 2017). No working endpoint. |
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
| vnoj | Cloudflare bot protection (managed challenge, `cf-mitigated: challenge`) on every path, including the profile page and `/api/v2` |
| beecrowd | Cloudflare bot protection (managed challenge, `cf-mitigated: challenge`) on judge.beecrowd.com |
| binarysearch | Domain dead (binarysearch.com does not resolve) |
| codecracker | Site gone: codecracker.arhn.in serves a 404 page on every path, including `/` |
| codedrills | Domain dead (codedrills.io has no A record, `www` does not resolve) |
| coj | Domain dead (coj.uci.cu does not resolve) |
| contest.bsuir.by | OJ backend gone: 502 Bad Gateway on http and https |
| eluminatis | Origin down: judge.eluminatis-of-lu.com returns Cloudflare 521 |
| it-edu.mipt.ru | Site gone: `/` and `/api/` return 404 "File not found." |
| prepbytes | Domain dead (mycode.prepbytes.com does not resolve) |
| acm.bsu.by | Requires authentication: problem and profile pages redirect to `/login/`; only contest standings are public |
| adventofcode | No public profiles; private leaderboards need a session cookie, and progress is counted in stars, not problems |
| algotester | Requires authentication: `/en/Account/Display/<id>` redirects to the login page |
| codeany | No public user pages found; profiles appear to require login |
| codearena.uz | Requires authentication: every path redirects to `/accounts/login/` |
| coderun (Yandex) | Requires authentication: `/profile` redirects to Yandex Passport; no public profile or API |
| informatics.mccme.ru | Moodle public profile shows only country, city and school; submissions and solved problems need login |
| projecteuler | Profiles require login; the public `/profile/<user>.txt` and `.png` carry no solved count as text |
| pythoncode.club | Only `/login` exists; no public user pages found |
| supecoder | Google login only; no public user pages or API found |
| techgig | No public profile page; `/myprofile` is the only profile route |
| usaco.guide | Progress is stored per logged-in user; no public profile |

These crawlers are kept for reference and may be restored if the issues are resolved.

## Offline but kept

These crawlers show offline on https://ojhunt.com/crawlers, but they are not archived because
they can still work from other networks (for example the CLI on a user's machine). Don't try to
fix them.

| Crawler | Reason |
|---------|--------|
| poj | POJ blocks requests from the ojhunt.com server. The crawler can still work from the CLI ([ADR 0011](../docs/adr/0011-poj-status-log-fallback.md)) |
