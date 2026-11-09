"""Discover candidate subreddits via GummySearch 'Similar Subreddits' snowball + brainstorm verification.
Writes discovery.json and discovery.md to the scratchpad."""
import csv, json, re, time, html as htmlmod
from pathlib import Path
import urllib.request, urllib.error

OUT = Path(__file__).parent
CSV = Path("/Users/keepcalm/Library/CloudStorage/Dropbox/Map_reddit_landscape/subreddits.csv")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
DELAY = 0.7

# ---- known subs from the CSV ----
known = {}  # lower -> (name, fit)
with CSV.open(newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        cell = row["Subreddit"]
        for part in cell.split("/ r/"):
            name = re.sub(r"^\s*r/", "", part).strip()  # don't use lstrip: it ate the 'r' of 'redshift'
            if name:
                known[name.lower()] = (name, row["Fit"].strip())

seeds = [n for n, (_, fit) in known.items() if fit in ("4", "5")]
seeds += ["apachespark", "mlops", "llmdevs", "dataanalytics", "deltalake"]
seeds = [s for s in seeds if s not in {"dlthub", "agenticdatastack", "ontologyengineering"}]

BRAINSTORM = """MicrosoftFabric AzureDataPlatforms AzureSynapse AzureDataFactory Alteryx Teradata oracle Dremio trino prestodb StarRocks
Firebolt SingleStore TimescaleDB influxdb questdb apachedruid apachepinot elasticsearch OpenSearch grafana observability OpenTelemetry
PostHog datadog splunk dataengineersindia datamodeling DataQuality DataGovernance MasterDataManagement dataarchitecture data datasets
opendata webscraping scrapy api APIs automation n8n zapier Airtable nocode lowcode Backend softwarearchitecture microservices Database
Polars FastAPI PySpark apachearrow lakehouse mcp modelcontextprotocol ClaudeCode vibecoding LLM LocalLLM OpenSourceAI aiagents LangGraph
LLMOps Lightdash streamlit plotly salesforce hubspot GoogleAnalytics shopify stripe SAP DataScienceJobs opensource coolgithubprojects
github learndataengineering DataEngineers semanticweb ontology KnowledgeGraph KnowledgeGraphs DataMesh Informatica Talend SSIS snowflakedb
Matillion Fabric powerplatform dataengineeringmemes developersIndia analyticsengineers SQLOptimization PLSQL dynamics365 marketingops
salesops MarketingAutomation growthhacking SaaSSales startupdata Dagster_io datascienceproject learndatascience DataScienceIndia""".split()

def fetch(name):
    url = f"https://gummysearch.com/r/{name}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, ""

def to_int(s):
    s = s.strip().replace(",", "")
    m = re.match(r"([\d.]+)\s*([kKmM]?)", s)
    if not m: return None
    v = float(m.group(1)); u = m.group(2).lower()
    return int(v * (1000 if u == "k" else 1_000_000 if u == "m" else 1))

def parse(page):
    """Return (self_name, members, growth, [(name, members, growth), ...])"""
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

cache = {}
def get(name):
    key = name.lower()
    if key in cache: return cache[key]
    status, page = fetch(name)
    time.sleep(DELAY)
    if status == 200 and page:
        cache[key] = parse(page)
    else:
        cache[key] = (None, None, None, None)  # not indexed
    return cache[key]

cands = {}  # lower -> dict(name, members, growth, referrers=set())
def note(name, members, growth, referrer):
    key = name.lower()
    c = cands.setdefault(key, {"name": name, "members": members, "growth": growth, "referrers": set()})
    if members is not None: c["members"] = members
    if growth is not None: c["growth"] = growth
    if referrer: c["referrers"].add(referrer)

# ---- hop 1 ----
seed_info = {}
for s in seeds:
    self_name, members, growth, sims = get(s)
    seed_info[s] = {"indexed": sims is not None, "members": members}
    print(f"seed r/{s}: {'ok' if sims is not None else 'not indexed'} members={members} sims={len(sims or [])}", flush=True)
    for (n, m, g) in (sims or []):
        note(n, m, g, s)

# ---- hop 2: expand the strongest new candidates ----
new_after_hop1 = [k for k in cands if k not in known]
new_after_hop1.sort(key=lambda k: (-len(cands[k]["referrers"]), -(cands[k]["members"] or 0)))
hop2 = [k for k in new_after_hop1 if (cands[k]["members"] or 0) >= 800][:35]
print(f"hop2 expanding {len(hop2)} subs", flush=True)
for k in hop2:
    self_name, members, growth, sims = get(cands[k]["name"])
    if members is not None: cands[k]["members"] = members
    if growth is not None: cands[k]["growth"] = growth
    for (n, m, g) in (sims or []):
        note(n, m, g, cands[k]["name"])

# ---- brainstorm verification ----
brain = {}
for b in BRAINSTORM:
    if b.lower() in known: continue
    self_name, members, growth, sims = get(b)
    brain[b] = {"indexed": sims is not None, "members": members, "growth": growth, "already_candidate": b.lower() in cands}
    print(f"brainstorm r/{b}: {'ok' if sims is not None else 'not indexed'} members={members}", flush=True)
    if sims is not None:
        note(self_name or b, members, growth, None)
        for (n, m, g) in sims:
            note(n, m, g, b)

# ---- output ----
rows = []
for k, c in cands.items():
    if k in known: continue
    rows.append({"name": c["name"], "members": c["members"], "growth_pct_yr": c["growth"],
                 "votes": len(c["referrers"]), "referrers": sorted(c["referrers"]),
                 "from_brainstorm": k in {b.lower() for b in brain}})
rows.sort(key=lambda r: (-r["votes"], -(r["members"] or 0)))
json.dump({"seeds": seed_info, "brainstorm": brain, "candidates": rows}, (OUT / "discovery.json").open("w"), indent=1)

with (OUT / "discovery.md").open("w") as f:
    f.write("| Subreddit | Members | Growth %/yr | Votes | Referred by |\n|---|---|---|---|---|\n")
    for r in rows:
        f.write(f"| r/{r['name']} | {r['members']} | {r['growth_pct_yr']} | {r['votes']} | {', '.join(r['referrers'])} |\n")
    f.write("\n\n## Brainstorm check\n\n| Subreddit | Indexed | Members | Growth |\n|---|---|---|---|\n")
    for b, v in brain.items():
        f.write(f"| r/{b} | {v['indexed']} | {v['members']} | {v['growth']} |\n")
print(f"done: {len(rows)} new candidates, {sum(1 for v in brain.values() if v['indexed'])}/{len(brain)} brainstorm subs indexed")
