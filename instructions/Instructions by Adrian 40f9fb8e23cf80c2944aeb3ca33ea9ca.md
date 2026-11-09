# Instructions by Adrian

# Task: Map the Reddit landscape for dltHub distribution

## Why

We want a reusable map of every data-related subreddit where dltHub could post or engage. For each subreddit, the map should answer:

- Can we post there?
- What can we post?
- Who reads it?
- Do they fit dltHub?

An LLM should later be able to use this map to answer: *"We're launching X. Where should we post it?"*

## How we'll work

- Work in a private repo of your own until you have something useful, then hand it over. Commit the scripts, the raw data and short notes on what worked and what didn't.
- We'll go step by step and decide the next step together after each one. **Don't build ahead.**

## Step 1: Find the subreddits

List **50–60 candidate subreddits**, with at least **30 solid ones**, covering:

- Data engineering, analytics and data science
- ML/AI and LLM tooling
- Python and SQL
- Specific tools: dbt, Snowflake, Databricks, DuckDB, Postgres, Airflow, etc.
- Self-hosting and homelab

**Sources:** Reddit search, the "related subs" lists in sidebars, and LLM brainstorming. Drop subreddits that are dead or off-topic.

**Output:** A simple list with a one-line note per subreddit.

> ✅ **Check-in:** Check in with me before Step 2.
> 

## Step 2: Download the data

Write scripts that pull the following for each subreddit:

| Endpoint | What it gives us |
| --- | --- |
| `reddit.com/r/<sub>/about.json` | Subscribers, active users, description |
| `reddit.com/r/<sub>/about/rules.json` | The formal rules |
| `reddit.com/r/<sub>/new.json?limit=100` | Recent posts, for posts per week and enforcement checks |
| `reddit.com/r/<sub>/top.json?t=month&limit=50` | What performs well |

**Guidelines:**

- Use a proper User-Agent and go slowly.
- If the public JSON is blocked or rate-limited, find what does work (the official API with an app token, PRAW, a dlt REST API source, etc.) and write down the process.
- **Getting reliable data access is the main deliverable of this step.**
- When it works, tell me how big the data is.

> ✅ **Check-in:** Check in with me after Step 2.
> 

## Step 3: Decide the format (together)

Based on the data volume, we'll decide how the LLM should use it:

- **Option A (preferred if small enough):** A summarized Notion database that a large model reads in full
- **Option B:** A RAG setup, only if we need one

## Step 4: Classify each subreddit

Use an LLM over the rules and the last ~50 posts to produce the following for each subreddit:

1. **Size and activity:** Subscribers, active users, posts per week, typical upvotes and comments
2. **Promo rules:** Quote the rule, then pick one:
    - Free to post
    - Allowed with a disclaimer
    - Self-promo thread or specific days only
    - Comments only
    - No vendors
3. **Enforcement in practice:** Did vendor or blog posts stay up, get removed or get called out? Rate it **strict / loose / unenforced**, with 1–2 example links.
4. **Audience:** Top ~5 roles (data engineers, DE managers, analysts, data scientists, ML/AI engineers, hobbyists or students)
5. **Attitude toward AI:** Enthusiastic / neutral / skeptical
6. **Stack:** Classic warehouse + ELT + dbt, Python-first pipelines, AI/LLM apps, or other
7. **dltHub fit:** High / Med / Low, with a one-line reason and the dlt angle that would land (OSS library, ingestion, LLM-native pipelines, etc.)
8. **Recommended action:** Post / post with a disclaimer / self-promo thread / comment only / avoid

**Quality check:** Spot-check the LLM's output by hand on a sample of subreddits.

## Final output

- **A Notion database** with one row per subreddit and the fields above as properties
- **A summary page on top** with:
    - Top 10 subreddits to post in
    - Top 10 subreddits to comment in
    - Subreddits to avoid
    - Patterns you noticed
- **Written so an LLM can query it directly**

## Later (not now): Posting-history check

Instead of tracking by hand where we've posted, the LLM could read the posting account's history (`/user/<name>/submitted.json`) and skip subreddits we used recently. This could become a small tool the LLM calls before suggesting where to post.

> 💡 Keep this in mind while writing the Step 2 fetching code, since the tool would use the same code.
> 

## Check-ins and timeline

- **Check-ins:** After Step 1 and after Step 2
- **Timeline:** *[fill in]*

---

Adding that we should focus on databricks clickhouse and snowlfake related stuff (subs where people who discuss these are)

# dltHub subreddit list

All subreddits we've ever considered, ranked by fit.

**Fit scale:** 5 = favorite · 4 = good fit · 3 = conditional · 2 = speculative · 1 = skip · 0 = never

**About the sizes (from Notion):** March 2026 counts are solid. July 2026 figures marked "~" are rough guesses. A blank means the size was never recorded.

## Rules for every sub

- **30-day cooldown** between posts (our own subs are exempt)
- **One warehouse sub per launch**
- **Aman or Hiba reviews** every post before it goes up

## Our own subs (no cooldown)

| Subreddit | Fit | Notes |
| --- | --- | --- |
| r/dltHub | 5 | dltHub-only content, drafted for nearly every launch |
| r/agenticdatastack | 5 | Seeded Jul 2026, vendor-friendly, ~8 posts drafted |
| r/OntologyEngineering | 5 | 24 drafts, 8 posted |
| r/llmdatastack | 3 | Adrian's; looks replaced by r/agenticdatastack |
| r/PythonDataEngineering | 2 | Adrian's, unused |
| r/DataEngCircleJerk | 1 | Adrian's meme sub |

## Favorites (fit 5)

| Subreddit | Size | Posting rules and notes |
| --- | --- | --- |
| r/dataengineering | 493K members / 158K weekly | 1 self-promo + 1 big announcement a month; mod approves launches; text posts only; warm up first |
| r/PostgreSQL | ~250K | Source-side angle only ("moving data out of Postgres") |
| r/snowflake | ~40–60K | Disclose the Snowflake partnership; never name competitors |
| r/dataops | ~30–40K | Promo restricted; ops/SLA framing works |
| r/bigquery | ~20–30K (7.6K weekly) | Educational only; Brand Affiliate tag |
| r/ETL | ~15–25K | Small but obvious fit; links only in comments |
| r/AnalyticsEngineering | 4.6K (Mar) vs ~30–50K (Jul) ⚠️ check | Thought to convert best |
| r/duckdb | 3.6K (Mar) vs ~10–15K (Jul) ⚠️ check | Thought to convert best; product posts OK if transparent |

## Good fit (fit 4)

| Subreddit | Size | Posting rules and notes |
| --- | --- | --- |
| r/SQL | ~1M | Broad; value-first only |
| r/analytics | ~500K | Education-first; max 1 dltHub link per thread |
| r/BigData | ~200K | Self-promo discouraged |
| r/databases | ~200K | "Moving data out of X" angle only |
| r/databricks | 25K / 20K weekly | Was "too early", now OK |
| r/Clickhouse | ~15–25K | No hype |
| r/ApacheIceberg | <10K | Once our Iceberg offering is clear |
| r/GTM_Engineering | <10K | GTM-engineer audience |
| r/redshift | — | Used for the benchmark series |

## Conditional (fit 3)

| Subreddit | Size | Posting rules and notes |
| --- | --- | --- |
| r/Python | 1.5M / 227K weekly | Very strict; Saturday Showcase thread only |
| r/ClaudeAI | ~200K | Only posts about the AI tool itself |
| r/ChatGPTCoding | ~200K | Only posts about the AI tool itself |
| r/LLMDevs | ~80–120K | Bans commercial promo; message mods first; open-source link only |
| r/mlops | ~60–80K | Mixed verdicts |
| r/dataanalytics | 8.7K weekly | Our only post with real numbers: ~3.5K views, 15 comments |
| r/deltalake | — | — |
| r/apachespark / r/spark | — | — |

## Speculative (fit 2)

| Category | Subreddits |
| --- | --- |
| AI coding tools | r/cursor (126K, "too broad"), r/AI_Agents, r/GithubCopilot, r/aider |
| Analytics and BI | r/dataanalysis (juniors), r/datascience, r/BusinessIntelligence, r/Metabase, r/superset, r/Looker, r/PowerBI, r/tableau, r/GoogleDataStudio |
| Databases | r/MySQL, r/SQLServer, r/MongoDB, r/cassandra, r/cockroachdb, r/Supabase, r/Neon |
| Data platforms and ingestion | r/datawarehouse, r/dataplatforms, r/Meltano, r/segment, r/rudderstack, r/MotherDuck (effectively dead) |
| Other | r/RevOps, r/dataengineeringjobs, r/googlecloud, r/Netsuite |

## Skip (fit 1)

| Category | Subreddits |
| --- | --- |
| AI/RAG | r/LocalLLaMA, r/MachineLearning, r/PromptEngineering, r/Rag, r/aipromptprogramming, r/LangChain, r/LlamaIndex, r/OpenAI, r/codeium, r/CLineProjects, r/devtools |
| Orchestration | r/airflow, r/dagster, r/Prefect, r/kestra, r/MageAI, r/temporal |
| Streaming | r/apachekafka, r/apacheflink, r/RisingWave, r/Materialize |
| MLOps tools | r/ZenML, r/Kubeflow |
| Python | r/pandas, r/learnpython, r/PythonProjects, r/uv, r/pydantic |
| Hobby | r/selfhosted, r/homelab, r/datahoarder, r/Kaggle |
| Too broad | r/startups (2M), r/sideproject (648K), r/aws, r/AZURE, r/programming, r/devops, r/cscareerquestions, r/SaaS, r/IndieHackers, r/learnmachinelearning |
| Other | r/GoogleAppsScript, r/dataisbeautiful, r/dataisugly |
| Geographic | r/india, r/brasil, r/Polska, r/europe, r/de |

## Never (fit 0)

| Reason | Subreddits |
| --- | --- |
| Competitors | r/dbt, r/fivetran, r/airbyte |
| Dead | r/apachehudi, r/dataengineering2 |

---

## Feedback on this list

**Problems:**

- **Not comprehensive.** Several small and medium subreddits are missing.
- **A lot of noise.** Some subs don't fit, and some are tiny or don't allow posting (small opportunity, high effort).

**Suggested next steps:**

- Go through the existing list and **shortlist before expanding**.
- **Gemini** might have access to subreddit metadata and could help with initial discovery.
- Reference: [dltHub's Content distribution (Notion)](https://app.notion.com/p/2bd9fb8e23cf80d3bfb2d0d49089dc19?pvs=21). The posting log at the end of that page isn't needed anymore.

---

I grouped the Speculative list into categories so it's easier to scan, and flagged the two subs with conflicting March and July sizes. Every subreddit and note from the original is still in the list.