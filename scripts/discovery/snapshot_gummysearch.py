"""One-off snapshot of GummySearch data (members, yearly growth, similar subreddits, last-updated date)
for every subreddit in subreddits.csv plus the curated candidates in discovery_candidates.md.
GummySearch shuts down on 2026-12-01, so this preserves what we used.
Output: gummysearch_snapshot_<date>.json and sizes_gummysearch_<date>.csv next to this script."""
import csv, json, re, time, html as htmlmod, datetime
from pathlib import Path
import urllib.request, urllib.error

HERE = Path(__file__).parent
CSV = HERE.parent.parent / "subreddits.csv"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
DELAY = 0.7
TODAY = datetime.date.today().isoformat()

CANDIDATES = """MicrosoftFabric AzureDataPlatforms Databricks_eng PySpark DatabaseAdministators Database Alteryx informatica SAP oracle
learnSQL Streamlit AzureSynapseAnalytics Observability grafana dataengineersindia dataengineer DataEngineeringPH datasets data
dataanalyst businessanalysis semanticweb KnowledgeGraph Ontology Neo4j datagovernance gtmengineering webscraping scrapingtheweb
coolgithubprojects opensource madeinpython PythonProjects2 FastAPI Backend softwarearchitecture mcp modelcontextprotocol MCPservers
ClaudeCode aiengineering aiagents AgentsOfAI llmops LLM LocalLLM OpenSourceAI n8n automation salesforce hubspot GoogleAnalytics
shopify stripe servicenow SQLOptimization Splunk elasticsearch OpenTelemetry Talend PowerPlatform Dynamics365 DeltaLake dagster""".split()

UNINDEXED_RETRY = """GTM_Engineering redshift Polars Teradata Dremio trino StarRocks Firebolt SingleStore TimescaleDB questdb apachedruid
OpenSearch datamodeling DataQuality MasterDataManagement opendata Lightdash plotly learndataengineering SSIS Matillion AzureDataFactory""".split()

ALIASES = {"duckdb": ["DuckDB"], "deltalake": ["DeltaLake"], "clickhouse": ["Clickhouse", "ClickHouse"], "bigdata": ["bigdata"],
           "redshift": ["redshift", "Redshift", "AmazonRedshift"], "spark": ["apachespark"], "postgresql": ["PostgreSQL"],
           "etl": ["ETL"], "sql": ["SQL"], "apacheiceberg": ["ApacheIceberg"], "llmdevs": ["LLMDevs"], "mysql": ["mysql", "MySQL"],
           "mongodb": ["mongodb", "MongoDB"], "sqlserver": ["SQLServer"], "powerbi": ["PowerBI"], "azure": ["AZURE"],
           "aws": ["aws"], "python": ["Python"], "claudeai": ["ClaudeAI"], "chatgptcoding": ["ChatGPTCoding"], "rag": ["Rag"],
           "ai_agents": ["AI_Agents"], "localllama": ["LocalLLaMA"], "machinelearning": ["MachineLearning"], "langchain": ["LangChain"],
           "llamaindex": ["LlamaIndex"], "openai": ["OpenAI"], "airflow": ["airflow", "apache_airflow"], "dagster": ["dagster"],
           "prefect": ["Prefect"], "apachekafka": ["apachekafka"], "apacheflink": ["apacheflink"], "selfhosted": ["selfhosted"],
           "homelab": ["homelab"], "datahoarder": ["DataHoarder"], "kaggle": ["Kaggle"], "googlecloud": ["googlecloud"],
           "netsuite": ["Netsuite"], "dbt": ["dbt"], "fivetran": ["fivetran"], "airbyte": ["airbyte"], "metabase": ["Metabase"],
           "superset": ["superset"], "looker": ["Looker"], "tableau": ["tableau"], "googledatastudio": ["GoogleDataStudio"],
           "cassandra": ["cassandra"], "cockroachdb": ["cockroachdb"], "supabase": ["Supabase"], "neon": ["Neon"],
           "datawarehouse": ["datawarehouse"], "dataplatforms": ["dataplatforms"], "meltano": ["Meltano"], "segment": ["segment"],
           "rudderstack": ["rudderstack"], "motherduck": ["MotherDuck"], "revops": ["RevOps"], "dataengineeringjobs": ["dataengineeringjobs"],
           "cursor": ["cursor"], "githubcopilot": ["GithubCopilot"], "aider": ["aider"], "dataanalysis": ["dataanalysis"],
           "datascience": ["datascience"], "businessintelligence": ["BusinessIntelligence"], "gtm_engineering": ["GTM_Engineering"],
           "analyticsengineering": ["analyticsengineering", "AnalyticsEngineering"]}

def fetch(name):
    req = urllib.request.Request(f"https://gummysearch.com/r/{name}", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""

def to_int(s):
    m = re.match(r"([\d.]+)\s*([kKmM]?)", s.strip().replace(",", ""))
    if not m: return None
    v = float(m.group(1)); u = m.group(2).lower()
    return int(v * (1000 if u == "k" else 1_000_000 if u == "m" else 1))

def parse(page):
    text = htmlmod.unescape(page)
    m = re.search(r"r/<!-- -->([A-Za-z0-9_]+)", text); slug = m.group(1) if m else None
    m = re.search(r"is a subreddit with ([\d.,]+[kKmM]?) members", text); members = to_int(m.group(1)) if m else None
    m = re.search(r"Yearly\s*</[^>]+>\s*<[^>]+>\s*([+-]?\s*[\d.,]+[kKmM]?) members \(([-\d.]+)%\)", text); growth = float(m.group(2)) if m else None
    m = re.search(r"Last updated: ([A-Za-z]+ \d{1,2}, \d{4})", text); updated = m.group(1) if m else None
    sims = []
    i = text.find("Similar Subreddits")
    if i != -1:
        block = text[i:]; j = block.find("Last updated"); block = block[: j if j != -1 else None]
        for mm in re.finditer(r'href="/r/([A-Za-z0-9_]+)/">r/<!-- -->[A-Za-z0-9_]+</a></h3><div[^>]*><div>([\d.,]+[kKmM]?)<!-- --> members</div>(?:<div[^>]*>.*?<span>([-\d.]+)<!-- -->% / yr</span>)?', block, re.S):
            sims.append({"name": mm.group(1), "members": to_int(mm.group(2)), "growth_pct_yr": float(mm.group(3)) if mm.group(3) else None})
    return {"slug": slug, "members": members, "growth_pct_yr": growth, "last_updated": updated, "similar": sims}

def variants(name):
    v = [name] + ALIASES.get(name.lower(), []) + [name.lower(), name.capitalize()]
    out = []
    for x in v:
        if x not in out: out.append(x)
    return out

def lookup(name):
    """status 'ok' | 'not indexed' (clean 404 on every variant) | 'timeout' (site not answering; do not trust)."""
    for v in variants(name):
        status, page = None, ""
        for attempt in range(4):                       # a timeout (status 0) means the site is down, not that the sub is missing
            status, page = fetch(v); time.sleep(DELAY)
            if status != 0: break
            print(f"    timeout on r/{v}, waiting 60s (attempt {attempt + 1}/4)", flush=True); time.sleep(60)
        if status == 0:
            return {"slug": None, "members": None, "growth_pct_yr": None, "last_updated": None, "similar": [], "tried": v, "status": "timeout"}
        if status == 200 and page:
            d = parse(page); d["tried"] = v; d["status"] = "ok"; return d
    return {"slug": None, "members": None, "growth_pct_yr": None, "last_updated": None, "similar": [], "tried": variants(name), "status": "not indexed"}

targets = []  # (name, source, fit)
with CSV.open(newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        for part in row["Subreddit"].split("/ r/"):
            name = re.sub(r"^\s*r/", "", part).strip()
            if name: targets.append((name, "csv", row["Fit"].strip()))
targets += [(n, "candidate", "") for n in CANDIDATES]
targets += [(n, "unindexed_retry", "") for n in UNINDEXED_RETRY]

results = []
for i, (name, source, fit) in enumerate(targets, 1):
    d = lookup(name); d.update({"subreddit": name, "source": source, "fit": fit}); results.append(d)
    print(f"[{i}/{len(targets)}] r/{name}: {d['status']} members={d['members']} updated={d['last_updated']}", flush=True)

json.dump({"snapshot_date": TODAY, "results": results}, (HERE / f"gummysearch_snapshot_{TODAY}.json").open("w"), indent=1)
with (HERE / f"sizes_gummysearch_{TODAY}.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["subreddit", "source", "fit", "gummysearch_slug", "members", "growth_pct_yr", "last_updated", "similar_subreddits", "status"])
    for d in results:
        w.writerow([f"r/{d['subreddit']}", d["source"], d["fit"], d["slug"] or "", d["members"] if d["members"] is not None else "",
                    d["growth_pct_yr"] if d["growth_pct_yr"] is not None else "", d["last_updated"] or "",
                    "; ".join(f"r/{s['name']} ({s['members']})" for s in d["similar"]), d["status"]])
ok = sum(1 for d in results if d["status"] == "ok")
print(f"\ndone: {ok}/{len(results)} found on GummySearch. Files: gummysearch_snapshot_{TODAY}.json, sizes_gummysearch_{TODAY}.csv")
