"""Pass 2: retry not-indexed seeds/brainstorm names with casing variants + aliases, and expand a curated
set of data-relevant neighbours. Merges into discovery.json -> discovery2.json / discovery2.md."""
import csv, json, re, time, html as htmlmod
from pathlib import Path
import urllib.request, urllib.error

OUT = Path(__file__).parent
CSV = Path("/Users/keepcalm/Library/CloudStorage/Dropbox/Map_reddit_landscape/subreddits.csv")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
DELAY = 0.7

known = {}
with CSV.open(newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        for part in row["Subreddit"].split("/ r/"):
            name = re.sub(r"^\s*r/", "", part).strip()
            if name:
                known[name.lower()] = (name, row["Fit"].strip())

prev = json.load(open(OUT / "discovery.json"))

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
    m = re.search(r"r/<!-- -->([A-Za-z0-9_]+)", text)
    self_name = m.group(1) if m else None
    m = re.search(r"is a subreddit with ([\d.,]+[kKmM]?) members", text)
    members = to_int(m.group(1)) if m else None
    m = re.search(r"Yearly\s*</[^>]+>\s*<[^>]+>\s*([+-]?\s*[\d.,]+[kKmM]?) members \(([-\d.]+)%\)", text)
    growth = float(m.group(2)) if m else None
    sims = []
    i = text.find("Similar Subreddits")
    if i != -1:
        block = text[i:]
        j = block.find("Last updated")
        block = block[: j if j != -1 else None]
        for mm in re.finditer(r'href="/r/([A-Za-z0-9_]+)/">r/<!-- -->[A-Za-z0-9_]+</a></h3><div[^>]*><div>([\d.,]+[kKmM]?)<!-- --> members</div>(?:<div[^>]*>.*?<span>([-\d.]+)<!-- -->% / yr</span>)?', block, re.S):
            sims.append((mm.group(1), to_int(mm.group(2)), float(mm.group(3)) if mm.group(3) else None))
    return self_name, members, growth, sims

def get(name):
    status, page = fetch(name)
    time.sleep(DELAY)
    return parse(page) if status == 200 and page else (None, None, None, None)

ALIASES = {
 "postgresql": ["PostgreSQL"], "etl": ["ETL"], "duckdb": ["DuckDB"], "sql": ["SQL"], "clickhouse": ["Clickhouse", "ClickHouse"],
 "apacheiceberg": ["ApacheIceberg"], "gtm_engineering": ["GTM_Engineering"], "edshift": ["redshift", "Redshift", "AmazonRedshift", "AWSRedshift"],
 "llmdevs": ["LLMDevs"], "deltalake": ["DeltaLake"], "Polars": ["polars"], "streamlit": ["Streamlit", "StreamlitOfficial"],
 "Fabric": ["MicrosoftFabric"], "powerplatform": ["PowerPlatform"], "dynamics365": ["Dynamics365"], "salesops": ["SalesOperations"],
 "growthhacking": ["GrowthHacking"], "Informatica": ["informatica"], "SSIS": ["ssis"], "PLSQL": ["plsql"], "Matillion": ["matillion"],
 "Lightdash": ["lightdash"], "plotly": ["Plotly"], "LLMOps": ["llmops"], "lakehouse": ["Lakehouse", "DataLakehouse"],
 "apachearrow": ["ApacheArrow"], "DataMesh": ["datamesh"], "learndataengineering": ["LearnDataEngineering"],
 "DataEngineers": ["dataengineers", "dataengineer"], "ontology": ["Ontology"], "KnowledgeGraphs": ["knowledgegraphs"],
 "snowflakedb": ["SnowflakeDB"], "Dagster_io": ["dagster"], "DataScienceIndia": ["datascienceindia"],
 "AzureSynapse": ["azuresynapse", "AzureSynapseAnalytics"], "AzureDataFactory": ["azuredatafactory"], "Teradata": ["teradata"],
 "Dremio": ["dremio"], "trino": ["Trino", "TrinoDB"], "prestodb": ["PrestoDB", "presto"], "StarRocks": ["starrocks"],
 "Firebolt": ["firebolt"], "SingleStore": ["singlestore", "memsql"], "TimescaleDB": ["timescaledb", "Timescale"],
 "influxdb": ["InfluxDB"], "questdb": ["QuestDB"], "apachedruid": ["ApacheDruid", "druid"], "apachepinot": ["ApachePinot"],
 "OpenSearch": ["opensearch"], "PostHog": ["posthog"], "datamodeling": ["DataModeling", "datamodelling"],
 "DataQuality": ["dataquality"], "DataGovernance": ["datagovernance"], "MasterDataManagement": ["masterdatamanagement", "MDM"],
 "dataarchitecture": ["DataArchitecture"], "opendata": ["OpenData"], "api": ["API", "APIs"], "APIs": ["api"],
}

def variants(name):
    v = [name, name.lower(), name.capitalize(), name.upper()] + ALIASES.get(name, []) + ALIASES.get(name.lower(), [])
    seen, out = set(), []
    for x in v:
        if x not in seen:
            seen.add(x); out.append(x)
    return out

# ---- candidates store seeded from pass 1 ----
cands = {r["name"].lower(): {"name": r["name"], "members": r["members"], "growth": r["growth_pct_yr"], "referrers": set(r["referrers"])}
         for r in prev["candidates"]}
def note(name, members, growth, referrer):
    key = name.lower()
    c = cands.setdefault(key, {"name": name, "members": members, "growth": growth, "referrers": set()})
    if members is not None: c["members"] = members
    if growth is not None: c["growth"] = growth
    if referrer: c["referrers"].add(referrer)

resolved = {}   # original -> (slug, members, growth, n_sims)
neighbors = {}  # slug -> [(name, members, growth)]

def resolve(orig):
    for v in variants(orig):
        self_name, members, growth, sims = get(v)
        if sims is not None:
            slug = self_name or v
            resolved[orig] = (slug, members, growth, len(sims))
            neighbors[slug] = sims
            if slug.lower() not in known:
                note(slug, members, growth, None)
            for (n, m, g) in sims:
                note(n, m, g, slug)
            return True
    resolved[orig] = None
    return False

print("== retry seeds ==", flush=True)
for s, v in prev["seeds"].items():
    if not v["indexed"]:
        ok = resolve(s)
        print(f"  {s}: {resolved[s] if ok else 'still not indexed'}", flush=True)

print("== retry brainstorm misses ==", flush=True)
for b, v in prev["brainstorm"].items():
    if not v["indexed"]:
        ok = resolve(b)
        print(f"  {b}: {resolved[b] if ok else 'still not indexed'}", flush=True)

CURATED_EXPAND = """MicrosoftFabric AzureDataPlatforms learnSQL dataanalyst Database dataengineersindia dataengineer DataEngineeringPH DataCamp
mcp MCPservers modelcontextprotocol aiengineering LargeLanguageModels OpenSourceAI coolgithubprojects webscraping scrapingtheweb
Observability grafana OpenTelemetry Neo4j semanticweb KnowledgeGraph nosql MSSQL redis elasticsearch Alteryx Talend SQLOptimization
PySpark FastAPI madeinpython PythonProjects2 datasets data datavisualization businessanalysis businessanalyst salesforce hubspot
GoogleAnalytics MarketingAutomation SalesOperations n8n automation nocode lowcode rpa serverless platformengineering sre
ArtificialInteligence LocalLLM LLM datascienceproject learndatascience DataScienceJobs Splunk datadog""".split()

print("== curated expansion ==", flush=True)
for name in CURATED_EXPAND:
    if name in neighbors: continue
    self_name, members, growth, sims = get(name)
    if sims is None:
        print(f"  r/{name}: not indexed", flush=True); continue
    slug = self_name or name
    neighbors[slug] = sims
    if slug.lower() not in known:
        note(slug, members, growth, None)
    for (n, m, g) in sims:
        note(n, m, g, slug)
    print(f"  r/{slug}: {members} members, {len(sims)} neighbours", flush=True)

rows = []
for k, c in cands.items():
    if k in known: continue
    rows.append({"name": c["name"], "members": c["members"], "growth_pct_yr": c["growth"], "votes": len(c["referrers"]), "referrers": sorted(c["referrers"])})
rows.sort(key=lambda r: (-r["votes"], -(r["members"] or 0)))
json.dump({"resolved": resolved, "neighbors": neighbors, "candidates": rows}, (OUT / "discovery2.json").open("w"), indent=1)

print("\n== neighbour lists for key seeds ==")
for slug in ["snowflake", "databricks", "Clickhouse", "ClickHouse", "dataengineering", "analyticsengineering", "DuckDB", "duckdb", "PostgreSQL", "ETL", "SQL", "bigquery", "apachespark", "ApacheIceberg", "DeltaLake", "deltalake", "redshift", "MicrosoftFabric", "AzureDataPlatforms", "mcp", "webscraping", "Database", "learnSQL", "dataanalyst"]:
    if slug in neighbors:
        print(f"  r/{slug} -> " + ", ".join(f"r/{n} ({m})" for n, m, g in neighbors[slug]))
print(f"\nTOTAL new candidates now: {len(rows)}")
