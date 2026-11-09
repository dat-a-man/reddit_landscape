# Reddit data sources: what works as of 2026-11-06

Adrian's Step 2 says "if the public JSON is blocked, find what works and write down the process". This is that write-up. Everything below was tested from Aman's Mac on 5–6 Nov 2026.

## Summary

| Need | Source | Cost | Status |
| --- | --- | --- | --- |
| Posts, comments, post history per subreddit or account | **Arctic Shift** API | Free, rate-limited | Works, verified |
| Removals and moderator actions | **Arctic Shift** (`removed_by_category`, 36 h second pass) | Free | Works, with the caveat below |
| Subscriber count | Arctic Shift (`subreddit_subscribers` on each post) or GummySearch snapshot | Free | Works |
| Rules, sidebar description | **Apify** `truefetch/reddit-community-profile` | ~$0.05 per sub | Not yet run |
| Top posts with live scores | Apify post scraper, or skip | ~$0.10–4 per 1,000 posts | Optional |
| Similar-subreddit discovery | GummySearch snapshot (taken 6 Nov 2026) | Free | Site closes 1 Dec 2026 |
| Reddit's own API or `.json` endpoints | — | — | Closed to us |

## Reddit itself: closed

- Unauthenticated `.json` endpoints: 403 on www, login redirect on old.reddit (since 30 May 2026). Subreddit HTML pages serve a JavaScript challenge to scripts.
- New OAuth apps need manual approval since Nov 2025. On 30 Sep 2026 Reddit announced the public Data API retirement: no new access after 31 Oct 2026, RSS ends 13 Nov 2026, everything ends March 2027 except written partner agreements.
- Reddit removed member and online counts from subreddit headers around Sep 2025; the UI shows weekly visitors instead.
- Do not scrape with the dltHub posting account's logged-in session.

## Arctic Shift (primary source for posts)

Public Reddit archive run by one developer (Arthur Heitmann), successor to Pushshift. Open source, donation funded. Site: `https://arctic-shift.photon-reddit.com`, code and API docs: `github.com/ArthurHeitmann/arctic_shift` (`api/README.md`).

**How it collects.** Through Reddit's official API. Every public post and comment is captured within seconds of creation (median 20 s in our sample), then fetched again ~36 hours later. The second pass updates `score`, `num_comments`, `upvote_ratio` and a few flags, and records deletions in `_meta` (`was_deleted_later`, `removal_type`). Nothing is refreshed after that. Monthly dumps exist for bulk use. Private and quarantined subs are excluded.

**API.** `GET /api/posts/search` and `/api/comments/search` with `subreddit`, `author`, `after`, `before`, `limit` (max 100), `sort`, plus text search (`title`, `selftext`, `query`, `body`; only together with `subreddit` or `author`). `/api/posts/ids` fetches up to 500 by id. Returns full Reddit objects incl. `removed_by_category`, `removed_by`, `banned_by`, `mod_reason_title`, `link_flair_text`, `domain`, `subreddit_subscribers`, `retrieved_on`. Rate limits are dynamic ("Timeout. Maybe slow down a bit" on the first call; 4–6 s between calls was fine). Do not pass `fields=` with arbitrary names, it 400s. Paginate by setting `before` to the oldest `created_utc` seen minus 1.

**Validation on r/dataengineering, 7 Oct–6 Nov 2026 (564 posts).**

| `removed_by_category` | Posts | With score ≥ 5 or comments ≥ 5 after 36 h | Reading |
| --- | --- | --- | --- |
| None | 34 | 31 | Live from the start, median score 30 |
| automod_filtered | 367 | 54 | Held by AutoModerator at submission; ~15 % were later approved and got traction, the rest mostly never went live |
| reddit | 124 | 12 | Site-wide spam filter; a few restored |
| moderator | 37 | 0 | Human removal, reliable signal |
| deleted / content_takedown | 2 | 0 | Author or legal |

So `removed_by_category` is the state ~20 s after posting, not the final state. Rules for Step 4's "enforcement in practice":
- `moderator` = removed by mods, trust it. Examples in this window: a ClickHouse-alternative launch, a Snowflake/Databricks benchmark, a semantic layer product, "Introducing Conduto".
- `automod_filtered` or `reddit` with score ≥ 5 or comments ≥ 5 = went live.
- `automod_filtered` with score 1 and no comments = most likely never approved; count as "filtered" not "removed".
- r/dataengineering filters nearly everything and approves a minority. Posts with `None` are from trusted or flaired accounts. That matches Adrian's note "mod approves launches".

**How to use it for the enforcement field.** Per subreddit: pull 90 days of posts; count by category; list link posts by `domain` and posts with showcase/open-source flairs or launch-style titles; check their fate; keep 1–2 permalinks as examples. Per brand: query `author=<vendor account>` and see which posts in which subs are `moderator` removed. For "called out": search comments for `self-promo`, `vendor`, `rule`, keep the ones with `distinguished = moderator`.

**Subreddit-level endpoints.** `/api/subreddits/search?subreddit=<name>` returns the about record (description, created, type, subscribers, lifetime post/comment totals), `/api/subreddits/rules?subreddits=a,b` the rules, `/api/subreddits/wikis` the wiki. About and rules are a one-off crawl from Jan–Feb 2025 (r/snowflake shows 15K there vs 27K today), so: take **sizes from `subreddit_subscribers` on recent posts**, use the 2025 rules as a draft and refresh before Step 4. Lifetime totals in `_meta` are current.

**Sizes and activity check, 6 Nov 2026** (a one-off script, since replaced by `scripts/landscape/`; 63 subs GummySearch missed plus 5 controls; controls matched GummySearch within 1 %):
- Own subs: r/OntologyEngineering 6,964 members / 51 posts in 90 d; r/dltHub 375 / 5; r/agenticdatastack 31 / 0 (last post Aug 2026); r/llmdatastack 8; r/PythonDataEngineering 1; r/DataEngCircleJerk 3.
- r/GTM_Engineering does not exist in the archive; **r/gtmengineering** has 18,502 members and 100+ posts per quarter.
- Dead or near-dead: r/redshift (268, last post 2018), r/MotherDuck (7), r/Meltano, r/segment, r/rudderstack, r/superset, r/Dremio (5), r/trino (12), r/Polars (75), r/Teradata (restricted, 2020), r/SSIS (restricted, 2022), r/AzureDataFactory (9), r/OpenSearch (176, 2022), r/plotly (1,176, 2024), r/learndataengineering (753, 2025), r/opendata (12K but restricted, no posts).
- Alive but small: r/Metabase 790 / 15 posts, r/cockroachdb 1,231 / 5, r/questdb 197 / 3, r/Matillion 190 / 2, r/devtools 2,443 / 100+, r/pandas 16,167 / 14, r/dbt 3,431 / 19.
- Not found at all: r/RisingWave, r/uv, r/apachehudi, r/dataengineering2, r/StarRocks, r/TimescaleDB, r/datamodeling, r/MasterDataManagement. r/Clickhouse and r/MageAI queries failed on rate limit (Clickhouse is 4K per GummySearch).

**Risks.** Single maintainer; depends on Reddit's API which ends March 2027; fair-use expectation (60 subs weekly is fine, daily hammering is not). Keep the fetch code source-agnostic so Apify can replace it. Content people deleted stays in the archive: keep what we store internal, never republish.

## Apify (rules, descriptions, optional live scores)

- `truefetch/reddit-community-profile`: 67 fields per subreddit incl. subscribers, description, rules, submission settings. No Reddit login. ~$0.0375–0.05 per result plus $0.01 per run. 60 subs ≈ $3, refresh monthly at most. Updated Aug 2026.
- Post scrapers (e.g. `trudax/reddit-scraper`): from $0.10 per 1,000 results, pay per event, returns `url` so a post can be re-checked. No moderation fields. Only needed if Adrian wants live top-post scores.
- Avoid RSS-based actors (RSS ends 13 Nov 2026).

## GummySearch (sizes and similar subreddits, closing)

- `gummysearch.com/r/<Name>`: members, yearly growth, ~10 similar subreddits, updated daily. Slug is case-sensitive. Small subs (< ~1K) often not indexed.
- Shutting down 1 Dec 2026. Snapshot taken 6 Nov 2026 for all 116 CSV subs + 66 candidates + 23 unindexed names: `scripts/discovery/sizes_gummysearch_2026-11-06.csv` (146 found, 59 not indexed).
- Discovery pass results: `discovery_candidates.md`.

## Dead ends

- `subredditstats.com` API answers but froze in Dec 2023.
- GummySearch's listed alternatives (BuzzAbout, Adlicio, RedReach, ReplyAgent, SubredditSignals, PainOnSocial, IdeaFast, Postpone): paid lead-gen or auto-reply tools, no public per-subreddit data. ReplyAgent and IdeaFast auto-post, which gets accounts banned in our subs.
- thehiveindex, videodubber, reddit.sentinel-team.org: 404 or unrelated.
- Reveddit: JavaScript app, depends on Pushshift for subreddit views; user views may still work manually.

## Scripts

- `scripts/landscape/`: `arctic_shift.py` (archive client, removal reading) and `build_landscape.py` (the full run; see `plan/`).
- `scripts/discovery/`: Step 1 one-off runs. `discover.py`, `discover2.py` (GummySearch snowball) and `snapshot_gummysearch.py` (sizes snapshot) read Adrian's list from a `subreddits.csv` that has since been removed (the list is in `instructions/`), so they don't run as-is any more. Their output is kept.
