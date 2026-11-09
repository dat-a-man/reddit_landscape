# Step 1 discovery: new subreddit candidates

Written 2026-11-06. Candidates **not** in Adrian's list of 116 (in `instructions/`), found by snowballing GummySearch's "Similar Subreddits" lists from our fit 4–5 subs, plus a brainstormed list verified the same way. Sizes are GummySearch member counts as of 2026-11-05/06. Fit guesses are mine and unverified; rules and enforcement come in Step 2/4.

## How to find more (the method)

Reddit's own discovery surfaces (search, sidebars, `about.json`) are closed to scripts, so use these instead:

1. **Snowball on GummySearch.** `gummysearch.com/r/<Name>` lists ~10 similar subreddits with member counts, updated daily, free, no login. Start from the fit 4–5 subs, collect their neighbours, then expand the data-relevant neighbours one more hop. Slugs are **case-sensitive** (`/r/DuckDB` works, `/r/duckdb` is a 404), so try the Reddit casing first.
   ⚠️ **GummySearch is shutting down on 1 December 2026** (no new signups since 30 Nov 2025; it lost its Reddit API negotiation). The pages still work as of 6 Nov 2026 and the data here is dated 5 Nov 2026. `scripts/discovery/snapshot_gummysearch.py` saves sizes and neighbour lists for all our subs before it goes. After December, size and discovery data has to come from Apify (Step 2) or manual browsing.
2. **Brainstorm, then verify.** List tool names, roles and adjacent topics (warehouses, source systems, Python libs, AI tooling), then check each on GummySearch for existence, size and growth. Not indexed does not mean dead: small subs (under ~1K) are often missing. Those need a manual look.
3. **Follow the tool mentions.** For the Databricks / ClickHouse / Snowflake focus, find where the tool is *discussed*, not just its home sub. One directory (reddgrow.ai) lists ClickHouse mentions in r/PostgreSQL, r/Observability and r/devopsish besides r/Clickhouse. Apify's data in Step 2 can do this properly by keyword over posts.
4. **Manual, in the browser (logged in).** Reddit search → "Communities" tab for keywords like `data pipeline`, `ELT`, `lakehouse`, `iceberg`, `snowflake`, `databricks`, `clickhouse`; the "similar communities" widget and sidebar links on r/dataengineering, r/databricks, r/snowflake, r/Clickhouse. This is the only way to see small subs GummySearch skips.
5. **Noise filter.** GummySearch similarity is user overlap, so it also returns jobs, careers, regional and generic programming subs. Drop anything whose audience doesn't build or buy data pipelines.

Scripts: `scripts/discovery/discover.py` (seed snowball + brainstorm) and `discover2.py` (casing retries + curated expansion). Raw output: 434 new names before curation.

## Shortlist: new candidates worth adding

Fit guess scale as in the CSV (5 best). "Signal" = which known subs' similar-lists pointed here.

### Warehouse and platform (Adrian's focus area)

| Subreddit | Members | Growth/yr | Signal | Fit guess | Note |
| --- | --- | --- | --- | --- | --- |
| r/MicrosoftFabric | 29K | — | AzureDataPlatforms; its own neighbours are databricks, snowflake, dataengineering | 4 | Fabric buyers are warehouse buyers; Microsoft staff active, check vendor tolerance |
| r/AzureDataPlatforms | 1K | +13% | snowflake, databricks, bigquery, MicrosoftFabric | 3 | Tiny but exactly the Synapse/Databricks/Snowflake crowd |
| r/Databricks_eng | 2K | — | brainstorm neighbour | 3 | Second Databricks sub; check it is alive |
| r/PySpark | 3K | — | brainstorm | 3 | Databricks-adjacent Python users |
| r/DatabaseAdministators (sic) | 6K | — | Clickhouse, DuckDB, PostgreSQL | 3 | DBAs; "moving data out of X" angle |
| r/Database | 91K | — | PostgreSQL, SQL, DuckDB | 3 | Generic but large; source-side angle only |
| r/Alteryx | 7K | +12% | snowflake | 3 | Legacy ETL users, migration angle; likely promo-hostile |
| r/informatica | 7K | — | brainstorm | 2 | Same angle as Alteryx |
| r/SAP | 64K | — | SQL, oracle | 2 | SAP extraction is a classic pain; speculative |
| r/oracle | 35K | — | brainstorm | 2 | Source-side only |
| r/learnSQL | 72K | +39% | Database, bigquery, snowflake, dataengineer | 2 | Juniors, education-first, comment only |
| r/Streamlit | 3K | — | brainstorm | 2 | Snowflake-owned tool, data app builders |
| r/AzureSynapseAnalytics | 936 | — | brainstorm | 2 | Too small unless Synapse content |
| r/Observability | 7K | +190% | OpenTelemetry, grafana | 2 | Where ClickHouse gets discussed outside its sub; logs not ELT |
| r/grafana | 27K | +23% | OpenTelemetry, datadog | 1 | ClickHouse-adjacent, weak for dlt |

### Data engineering and analytics communities

| Subreddit | Members | Growth/yr | Signal | Fit guess | Note |
| --- | --- | --- | --- | --- | --- |
| r/dataengineersindia | 25K | +125% | dataengineer, developersIndia | 3 | DE-specific despite being regional; fast growing |
| r/dataengineer | 4K | — | brainstorm | 3 | Small sibling of r/dataengineering |
| r/DataEngineeringPH | 7K | — | dataengineer | 2 | Philippines DE community |
| r/datasets | 224K | +8% | data | 2 | People hunting for data; "pull API X into DuckDB" angle |
| r/data | 54K | — | datasets | 2 | Generic |
| r/dataanalyst | 59K | +42% | analytics, dataanalytics, MicrosoftFabric | 2 | Analysts, not builders |
| r/businessanalysis | 120K | — | analytics | 1 | BA audience |
| r/semanticweb | 10K | — | KnowledgeGraph | 3 | For the OntologyEngineering content stream |
| r/KnowledgeGraph | 6K | — | semanticweb, Neo4j | 3 | Same |
| r/Ontology | 3K | — | brainstorm | 2 | Same, small |
| r/Neo4j | 6K | +15% | KnowledgeGraph | 2 | Graph DB users |
| r/datagovernance | 2K | — | brainstorm | 2 | Small |
| r/gtmengineering | 18K | — | brainstorm | 3 | ⚠️ Different from r/GTM_Engineering (fit 4, <10K in CSV). Check which is the live one |

### Python-first builders and OSS launch channels

| Subreddit | Members | Growth/yr | Signal | Fit guess | Note |
| --- | --- | --- | --- | --- | --- |
| r/webscraping | 105K | — | scrapy, mcp | 3 | Scrape-to-warehouse pipelines; vendor-tolerant |
| r/scrapingtheweb | 10K | +366% | scrapy, webscraping | 2 | Smaller sibling |
| r/coolgithubprojects | 134K | +116% | opensource, OpenSourceAI | 3 | OSS launch channel; links allowed |
| r/opensource | 399K | +33% | mcp, aiagents, coolgithubprojects | 3 | OSS launch channel; strict on promo tone |
| r/madeinpython | 28K | +13% | FastAPI, datascienceproject | 3 | Showcase sub, launches allowed |
| r/PythonProjects2 | 61K | — | webscraping | 2 | Showcase sub, lower quality |
| r/FastAPI | 34K | — | microservices | 2 | Python backend devs |
| r/Backend | 73K | +117% | FastAPI, learnSQL, dataanalyst | 2 | Architecture posts land sometimes |
| r/softwarearchitecture | 123K | +44% | FastAPI, microservices | 2 | Same |

### AI, agents and LLM-native pipelines

| Subreddit | Members | Growth/yr | Signal | Fit guess | Note |
| --- | --- | --- | --- | --- | --- |
| r/mcp | 128K | +70% | ClaudeCode, LangGraph, opensource, elasticsearch | 4 | dltHub's MCP work fits directly; neighbours are AI_Agents, ClaudeAI, cursor |
| r/modelcontextprotocol | 25K | — | brainstorm | 3 | Smaller MCP sub |
| r/MCPservers | 31K | +121% | mcp, aiagents | 3 | MCP server launches |
| r/ClaudeCode | 483K | +1061% | mcp, aiagents, LangGraph | 3 | Same rule as r/ClaudeAI: only posts about the tool itself |
| r/aiengineering | 14K | — | Backend | 3 | "AI engineer" audience, pipelines for LLM apps |
| r/aiagents | 127K | +122% | AgentsOfAI, LangGraph, LocalLLM | 2 | Promo-saturated; r/AI_Agents (477K) already in CSV at fit 2 |
| r/AgentsOfAI | 134K | +83% | mcp, mlops | 2 | Same |
| r/llmops | 3K | — | brainstorm | 2 | Small but on-topic |
| r/LLM | 60K | — | brainstorm | 1 | Generic |
| r/LocalLLM | 260K | +182% | ClaudeCode | 1 | Hobbyist local models |
| r/OpenSourceAI | 35K | +660% | LLM, aiagents, mcp | 2 | OSS AI launches |

### Automation and source systems ("moving data out of X")

| Subreddit | Members | Growth/yr | Signal | Fit guess | Note |
| --- | --- | --- | --- | --- | --- |
| r/n8n | 262K | +52% | Airtable, automation | 2 | Huge, vendor-tolerant, but no-code audience |
| r/automation | 241K | +66% | n8n, zapier | 2 | Same |
| r/salesforce | 118K | — | snowflake | 2 | Source-side angle |
| r/hubspot | 25K | +60% | Airtable, zapier | 2 | Source-side angle |
| r/GoogleAnalytics | 42K | — | bigquery | 2 | GA4 → BigQuery export is a real ingestion topic |
| r/shopify | 385K | — | stripe | 1 | Merchants, not devs |
| r/stripe | 29K | — | brainstorm | 1 | Source-side, speculative |
| r/servicenow | 40K | — | SAP | 1 | Source-side, speculative |

## Dropped as noise

Jobs and careers (r/jobs, r/dataanalysisCareers, r/DataScienceJobs, r/cscareerquestionsEU…), regional (r/developersIndia, r/developersPak, r/bangalore…), generic programming (r/coding, r/webdev, r/learnprogramming), finance/BA (r/Accounting, r/FPandA), marketing and sales (r/b2bmarketing, r/CRM, r/MarketingAutomation, r/SalesOperations…), infra (r/sre, r/kubernetes, r/Terraform, r/platformengineering), vibe-coding (r/vibecoding, r/lovable, r/replit), and anything unrelated that user overlap dragged in (r/piano, r/tattoo, r/cats).

## Not on GummySearch: resolved via Arctic Shift (6 Nov 2026)

Subscriber counts come from the newest archived post in each sub; activity is posts in the last 90 days. Details in `data_sources.md`.

| Subreddit | Members | Posts / 90 d | Verdict |
| --- | --- | --- | --- |
| r/gtmengineering | 18,502 | 100+ | **This is the live GTM sub.** r/GTM_Engineering (fit 4 in the CSV) does not exist in the archive |
| r/redshift | 268 | 0 (last post 2018) | Dead. Drop from fit 4 |
| r/Metabase | 790 | 15 | Alive, tiny |
| r/cockroachdb | 1,231 | 5 | Alive, tiny |
| r/pandas | 16,167 | 14 | Alive, low activity |
| r/dbt | 3,431 | 19 | Competitor sub per Adrian, listed for completeness |
| r/devtools | 2,443 | 100+ | Alive |
| r/questdb | 197 | 3 | Tiny |
| r/Matillion | 190 | 2 | Tiny |
| r/Polars | 75 | 12 | Tiny |
| r/trino | 12 | 2 | Dead |
| r/MotherDuck, r/Meltano, r/segment, r/rudderstack, r/superset, r/Dremio, r/Firebolt, r/SingleStore, r/DataQuality, r/Lightdash, r/AzureDataFactory | 1–41 | 0 | Dead |
| r/Teradata, r/SSIS, r/apachedruid, r/opendata (12K) | — | 0 | Restricted, no posts |
| r/OpenSearch, r/plotly, r/learndataengineering, r/PythonProjects | 176–1,176 | 0 | Dormant |
| r/RisingWave, r/uv, r/StarRocks, r/TimescaleDB, r/datamodeling, r/MasterDataManagement, r/apachehudi, r/dataengineering2 | — | — | Not in the archive at all |

Also found but effectively dead on GummySearch: r/DeltaLake (350), r/dagster (365), r/datamesh (495), r/ApachePinot (150), r/clouddatalake (59).

Our own subs: r/OntologyEngineering 6,964 members / 51 posts per 90 d; r/dltHub 375 / 5; r/agenticdatastack 31 / 0 (last post Aug 2026); r/llmdatastack 8; r/PythonDataEngineering 1; r/DataEngCircleJerk 3.

## Sizes observed for subs already in the CSV (GummySearch, Nov 2026)

Resolves the two ⚠️ rows and corrects several "~" guesses.

| Subreddit | CSV size | Now |
| --- | --- | --- |
| r/AnalyticsEngineering | 4.6K vs ~30–50K ⚠️ | 6K |
| r/duckdb | 3.6K vs ~10–15K ⚠️ | 6K |
| r/dataengineering | 493K | 485K |
| r/PostgreSQL | ~250K | 90K |
| r/snowflake | ~40–60K | 27K |
| r/dataops | ~30–40K | 549 |
| r/bigquery | ~20–30K | 21K |
| r/ETL | ~15–25K | 14K |
| r/SQL | ~1M | 293K |
| r/analytics | ~500K | 287K |
| r/BigData | ~200K ("does not exist" remark) | 76K, exists |
| r/databases | ~200K | 2K |
| r/databricks | 25K | 37K |
| r/Clickhouse | ~15–25K | 4K |
| r/ApacheIceberg | <10K | 1K |
| r/Python | 1.5M | 1.5M |
| r/ClaudeAI | ~200K | 1.3M |
| r/ChatGPTCoding | ~200K | 409K |
| r/LLMDevs | ~80–120K | 180K |
| r/mlops | ~60–80K | 41K |
| r/dataanalytics | 8.7K weekly | 49K |
| r/deltalake | — | 350 |
| r/apachespark | — | 20K |
| r/cursor | 126K | 161K |
| r/AI_Agents | — | 477K |
| r/LangChain | — | 110K |
| r/dataanalysis | — | 233K |
| r/datascience | — | 2.8M |
| r/SQLServer | — | 68K |
| r/MySQL | — | 50K |
| r/MongoDB | — | 30K |
| r/Supabase | — | 45K |
| r/cassandra | — | 3K |
| r/AZURE | — | 218K |
| r/opensource | — | 399K |
