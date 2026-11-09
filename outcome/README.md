# Outcome: Reddit landscape for dltHub launches

Data as of **9 Nov 2026**. How it was made: [`../plan/reddit_landscape_plan.html`](../plan/reddit_landscape_plan.html).

## What's here

- [`reddit_landscape.md`](reddit_landscape.md): one row per subreddit. Size, weekly visitors, activity, how strict the mods are, top post, our last post and when the 30-day cooldown ends.
- [`subs/<sub>.md`](subs/): one page per subreddit. Current rules, our posts there, why posts get removed, last 50 posts, top 20 posts of the last 30 days, and their full text.

**In numbers:** 78 subreddits (Adrian's fit 3–5 plus new candidates guessed at fit 2–5), 69 active and 9 not active. 36,785 posts (65 MB raw). Weekly visitors and current rules for all 69 active subs: 43 have rules of their own, 26 have none.

## Key subs at a glance

The 16 active subs with fit 4–5 that aren't ours, by weekly visitors.

| Sub | Weekly visitors | Posts live / mod-removed | Promotion rule (current) | Our last post (score) | Free from |
| --- | --- | --- | --- | --- | --- |
| r/dataengineering | 90K | 16% / 6% | Self-promotion once a month, Brand Affiliate flair, every link reviewed | 17 Sep, held by AutoMod (the June post: 551) | now |
| r/SQL | 51K | 61% / 11% | None; removes beginner questions and tutorials | never | now |
| r/mcp | 50K | 67% / 0% | No waitlists, no astroturfing, no AI slop; use the showcase tag | never | now |
| r/analytics | 40K | 59% / 29% | No blog spam or advertising; new accounts auto-removed | 27 Oct, spam-filtered | 26 Nov |
| r/PostgreSQL | 30K | 75% / 13% | None | 17 Jun (1) | now |
| r/databricks | 21K | 89% / 3% | Mark self-promotion as brand affiliate; moving it to a weekly megathread | 6 Nov (5) | 6 Dec |
| r/MicrosoftFabric | 20K | 86% / 2% | No sales activity or solicitation | never | now |
| r/snowflake | 10K | 81% / 6% | No vendor astroturfing; linked content must be free | 17 Jul (14) | now |
| r/gtmengineering | 7.4K | 75% / 2% | Product pitches only in the weekly pitch post | 20 May (11) | now |
| r/DuckDB | 3.0K | 80% / 0% | No rules of its own | 22 Jun (10) | now |
| r/ETL | 2.3K | 81% / 2% | No rules of its own | 31 Jul (1) | now |
| r/bigquery | 2.0K | 66% / 4% | No rules of its own | 13 Oct (1) | 12 Nov |
| r/Clickhouse | 1.2K | 80% / 8% | No rules of its own | Dec 2025 (1) | now |
| r/bigdata | 691 | 54% / 8% | No unsolicited self-promotion; disclose commercial interest | Dec 2025 (3) | now |
| r/analyticsengineering | 590 | 80% / 0% | No rules of its own | 21 Jul (1) | now |
| r/ApacheIceberg | 125 | 82% / 4% | No rules of its own | never | now |

Cooldowns are based on u/Thinker_Assignment and u/Original_Response925, which still need confirming with Adrian.

## What stands out

1. **Biggest reach, hardest door: r/dataengineering.** 90K weekly visitors, but only 16% of posts go live. In 30 days, 164 posts were removed for AI-generated content (rule 9). Our June post got 551 upvotes once approved; the September one was held by AutoModerator and never approved.
2. **Posts must read as human-written.** 14 of the 43 subs with rules ban or limit AI-generated posts, including r/dataengineering, r/mcp, r/Python, r/opensource and r/LLMDevs.
3. **Big, open, never tried:** r/mcp (50K visitors, no mod removals), r/SQL (51K) and r/MicrosoftFabric (20K, a warehouse sub). Each has one rule to respect (see the table).
4. **Where our posts land:** r/snowflake (14, 10), r/DuckDB (24, 10) and r/gtmengineering (11) respond. r/bigquery (last three posts all scored 1), r/ETL, r/analyticsengineering and r/Clickhouse barely do, despite fit 5 in Adrian's list.
5. **Promotion has its own place in some subs:** r/gtmengineering's weekly pitch post, r/databricks' self-promotion megathread, r/ChatGPTCoding's weekly self-promotion thread and r/Python's showcase rules.
6. **Strict about new accounts:** r/analytics auto-removed 45 posts in 30 days from accounts new to the sub.
7. **Dead from the original list:** r/dataops, r/databases and r/redshift, plus our own r/agenticdatastack and r/llmdatastack.

## Still open

- Confirm dltHub's Reddit accounts with Adrian (needed for the cooldown columns).
- Check in with Adrian on this Step 2 result, then decide the format (Step 3) and run the LLM classification per sub (Step 4).
- Removal reasons are only public when mods comment; vendor posts are mostly removed silently. The top 20 of the four largest subs covers fewer than 30 days.
