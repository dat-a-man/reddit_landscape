"""Build the Reddit landscape table for dltHub launches from the Arctic Shift archive.

Reads   landscape_subs.csv     which subs, fit, warehouse flag, weekly visitors (filled by hand)
        our_accounts.txt       dltHub's Reddit usernames (for the 30-day cooldown)
Writes  data/raw/<date>/<sub>.json         posts and counts as the archive returned them (slimmed)
        data/raw/<date>/_our_accounts.json our accounts' posts in the last 365 days
        outcome/reddit_landscape.md        one row per subreddit
        outcome/subs/<sub>.md              rules, our posts there, last 50 posts, top 20 posts (30 days), their full text
Also reads data/manual/pages/*.page.json (saved by hand, see data/manual/collector.html) for Reddit's
weekly visitors and contributions and each sub's current rules.

Usage, from the project folder:
    python scripts/landscape/build_landscape.py                   fetch every sub not yet fetched today, then write the markdown
    python scripts/landscape/build_landscape.py snowflake duckdb  fetch only these (the markdown still lists every sub)
    python scripts/landscape/build_landscape.py --render-only     no fetching: rewrite the markdown from the newest data/raw/<date>
                                                                  (use after filling weekly_visitors in landscape_subs.csv)

A sub already fetched today is skipped, so an interrupted run can simply be restarted.
Delete data/raw/<date>/<sub>.json to fetch that sub again.
"""
import csv
import datetime
import json
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True  # keep the folder free of __pycache__
import arctic_shift as arc  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SUBS_CSV = ROOT / "landscape_subs.csv"
ACCOUNTS_TXT = ROOT / "our_accounts.txt"
RAW = ROOT / "data" / "raw"
OUT_MD = ROOT / "outcome" / "reddit_landscape.md"
FRONT_MD = ROOT / "README.md"  # the repo's front page: just the table
SUBS_DIR = ROOT / "outcome" / "subs"
PAGES_DIR = ROOT / "data" / "manual" / "pages"

DAY = 86400
WINDOW_DAYS = 30     # top posts window
LAST_N = 50          # "last 50 posts"
TOP_N = 20           # "top 20 posts"
MAX_PAGES = 10       # per sub; each page is 100 to 1,000 posts
COOLDOWN_DAYS = 30
HISTORY_DAYS = 365   # how far back we look for our own posts
DEAD_DAYS = 90       # no post in this long = not active
NOT_PEOPLE = {"AutoModerator", "[deleted]"}


# ---------- inputs ----------

def read_subs():
    with SUBS_CSV.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    subs = []
    for r in rows:
        name = (r.get("subreddit") or "").strip().removeprefix("r/").strip()
        if not name:
            continue
        subs.append({
            "name": name,
            "source": (r.get("source") or "").strip(),
            "fit": (r.get("fit") or "").strip(),
            "warehouse": (r.get("warehouse") or "").strip().lower() in ("y", "yes", "x", "1", "true"),
            "weekly_visitors": (r.get("weekly_visitors") or "").strip(),
        })
    return subs


def read_accounts():
    if not ACCOUNTS_TXT.exists():
        return []
    out = []
    for line in ACCOUNTS_TXT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line.removeprefix("u/").removeprefix("/u/"))
    return out


def accounts_confirmed():
    return ACCOUNTS_TXT.exists() and "NOT YET CONFIRMED" not in ACCOUNTS_TXT.read_text(encoding="utf-8")


# ---------- fetching ----------

def covers(rec, days):
    """Do the pulled posts reach back `days` days (or hold the sub's whole history)?"""
    posts = rec["posts"]
    if not rec["capped"] and rec["complete"]:
        return True
    return bool(posts) and posts[-1]["created_utc"] <= rec["fetched_at"] - days * DAY


def fetch_sub(name, now):
    rec = {"subreddit": name, "fetched_at": now, "errors": [], "authors_28d": None, "authors_7d": None}
    posts, pages, capped, complete = [], 0, False, True
    cutoff = now - WINDOW_DAYS * DAY
    for page in arc.iter_post_pages(subreddit=name, before=now):
        if page is None:
            complete = False
            rec["errors"].append(f"post pull stopped after {pages} pages")
            break
        posts += [arc.slim(p) for p in page]
        pages += 1
        settled = sum(1 for p in posts if arc.is_settled(p, now))
        if posts[-1]["created_utc"] < cutoff and settled >= LAST_N:
            break
        if pages >= MAX_PAGES:
            capped = True
            break
    rec.update({"posts": posts, "pages": pages, "capped": capped, "complete": complete})

    # Very large subs: the pull stops short, so count posts and posters with the author
    # aggregate instead. Everywhere else the pulled posts are counted directly.
    for days, key in ((28, "authors_28d"), (7, "authors_7d")):
        if not covers(rec, days):
            time.sleep(arc.PAUSE)
            rec[key] = arc.aggregate_authors(name, now - days * DAY, now)
            if rec[key] is None:
                rec["errors"].append(f"{days}-day count failed")
    time.sleep(arc.PAUSE)
    return fetch_mod_comments(rec, now)


def fetch_mod_comments(rec, now):
    """Add rec["mod_comments"]: what AutoModerator and <sub>-ModTeam commented, back to the
    oldest pulled post (at least 31 days). The only public trace of removal reasons."""
    posts = rec["posts"]
    rec["mod_comments"] = []
    if not posts or posts[0]["created_utc"] < now - DEAD_DAYS * DAY:
        return rec  # not active, nothing to explain
    sub = posts[0]["subreddit"]
    after = min(posts[-1]["created_utc"], now - (WINDOW_DAYS + 1) * DAY)
    for author in arc.mod_authors(sub):
        for i, page in enumerate(arc.iter_comment_pages(subreddit=sub, author=author, after=after, before=now)):
            if page is None:
                rec["errors"].append(f"comments by u/{author}: pull failed")
                break
            rec["mod_comments"] += [{k: c.get(k) for k in arc.KEEP_COMMENT} for c in page]
            if i + 1 >= MAX_PAGES:
                break
        time.sleep(arc.PAUSE)
    return rec


def fetch_accounts(accounts, now):
    rec = {"accounts": accounts, "fetched_at": now, "errors": [], "posts": []}
    for acc in accounts:
        n = 0
        for page in arc.iter_post_pages(author=acc, after=now - HISTORY_DAYS * DAY, before=now):
            if page is None:
                rec["errors"].append(f"u/{acc}: pull failed")
                break
            rec["posts"] += [arc.slim(p) for p in page]
            n += len(page)
        print(f"  u/{acc}: {n} posts in the last {HISTORY_DAYS} days", flush=True)
        time.sleep(arc.PAUSE)
    return rec


# ---------- pages saved by hand (data/manual/collector.html, "Save for landscape v2") ----------
# Reddit blocks scripts from about.json / rules.json, even inside the browser. So Aman opened each
# sub in Chrome and a bookmark saved what the page shows: the header's weekly visitors and
# contributions (hidden attributes) and the sidebar text, including the sub's own rules.

# Lines that end the sidebar's rules list: the heading of the next sidebar box, Reddit's left menu or
# its site-wide rules. Collected from the 43 subs saved on 9 Nov 2026.
RULES_END = {"Reddit Rules", "Home", "Popular", "News", "Explore", "Bookmarks", "Community Bookmarks", "Moderators",
             "Message Mods", "Installed Apps", "Bot Bouncer", "Resources", "Other Links", "Official Discord",
             "Post Flair", "Conferences", "Megathread", "Flairs for Posts", "Other languages", "Announcements!",
             "Friends in different places", "Please join these subreddits", "Community Flairs", "Subscriber Info", "AMA"}
RULES_END_RE = re.compile(r"^(filter|search) by\b|^(related|recommended)\b|^\d[\d,]*\s+(members|subscribers)$|^join$", re.I)
LATE_HEADINGS = {"Flairs", "Links", "Learning SQL", "Newsletter"}  # box headings, unless they open the description
PAGE_END = {"Reddit Rules", "Home", "Popular", "News", "Explore", "Installed Apps"}
SENTENCE_END = re.compile(r"[.!?)\"”’]$")


def ends_rules(lines, j, desc, title):
    """For the last rule only: is lines[j] where its description stops and the next sidebar box starts?"""
    line = lines[j]
    if line in RULES_END or RULES_END_RE.search(line) or (title and line == title):
        return True
    if desc and line in LATE_HEADINGS:
        return True
    if not re.search(r"[^\W_]", line):  # no letters or digits: "...", "✻", "."
        return True
    finished = bool(desc) and bool(SENTENCE_END.search(desc[-1]))
    if finished and re.fullmatch(r"r/\w+", line):  # a "related subs" box
        return True
    # After a finished sentence, two short lines without punctuation in a row are a box heading and its first item.
    nxt = lines[j + 1] if j + 1 < len(lines) else ""
    return finished and len(line) <= 30 and len(nxt) <= 30 and not SENTENCE_END.search(line) and not SENTENCE_END.search(nxt)


def parse_page(d):
    attrs = d.get("attributes") or []

    def header_attr(name):
        v = next((a.split("=", 1)[1] for a in attrs if a.startswith(f"shreddit-subreddit-header {name}=")), None)
        return int(v) if v and v.isdigit() else None

    lines = [line.strip() for line in (d.get("text") or "").split("\n")]
    out = {"saved_at": (d.get("saved_at") or "")[:10], "weekly_visitors": header_attr("weekly-active-users"),
           "weekly_contributions": header_attr("weekly-contributions"), "description": None, "created": None,
           "rules": [], "has_rules": False}
    title = None
    if "Community Info Section" in lines:
        ci = lines.index("Community Info Section")
        title = lines[ci + 1] if ci + 1 < len(lines) else None
        desc = lines[ci + 2] if ci + 2 < len(lines) else ""
        if desc and desc not in ("Show more", "Weekly visitors"):
            out["description"] = desc
    out["created"] = next((line[len("Created "):] for line in lines if line.startswith("Created ")), None)

    head = next((i for i, line in enumerate(lines)
                 if re.fullmatch(r"r/\S+ rules", line, re.I) and line.lower() != "reddit rules"), None)
    if head is None:
        return out
    out["has_rules"] = True
    i, n = head + 1, 1
    while i + 1 < len(lines) and lines[i] == str(n):
        name = lines[i + 1]
        nxt = None  # where the next rule's number is, if there is a next rule
        for k in range(i + 2, min(len(lines), i + 60)):
            if lines[k] == str(n + 1):
                nxt = k
                break
            if lines[k] in PAGE_END:
                break
        if nxt is not None:  # the description runs up to the next rule
            desc, j = lines[i + 2:nxt], nxt
        else:  # last rule: stop where the next sidebar box starts
            j, desc = i + 2, []
            while j < len(lines) and not ends_rules(lines, j, desc, title) and len(desc) < 12:
                desc.append(lines[j])
                j += 1
        out["rules"].append((name, " ".join(desc)))
        n, i = n + 1, j
    return out


def load_pages():
    """{lowercase sub name: parsed page} for every file in data/manual/pages/."""
    pages = {}
    for f in sorted(PAGES_DIR.glob("*.page.json")) if PAGES_DIR.exists() else []:
        d = load(f)
        if d and d.get("subreddit"):
            pages[d["subreddit"].lower()] = parse_page(d)
    return pages


def fetch_rules(names):
    """Rules for all subs in one call. The archive's rules are a one-off crawl from Jan-Feb 2025
    and cover only some subs (35 of our first 85). Returns {lowercase name: record}."""
    data = arc.get("subreddits/rules", {"subreddits": ",".join(names)})
    if data is None:
        print("  rules: call failed", flush=True)
        return None
    print(f"  rules: found for {len(data)} of {len(names)} subs", flush=True)
    return {x["subreddit"].lower(): x for x in data}


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


# ---------- numbers per sub ----------

def summarize(rec):
    now = rec["fetched_at"]
    posts = rec["posts"]
    settled = [p for p in posts if arc.is_settled(p, now)]
    last = settled[:LAST_N]

    oldest = posts[-1]["created_utc"] if posts else now
    window_start = now - WINDOW_DAYS * DAY if covers(rec, WINDOW_DAYS) else oldest
    in_window = [p for p in settled if p["created_utc"] >= window_start]
    top = sorted((p for p in in_window if arc.is_live(p)),
                 key=lambda p: (p.get("score") or 0, p.get("num_comments") or 0), reverse=True)[:TOP_N]

    # Shares and medians: the whole 30-day window when it has at least 50 posts (on a busy
    # sub the last 50 posts are only a few days), else the last 50 posts.
    sample = in_window if len(in_window) >= LAST_N else last
    live_sample = [p for p in sample if arc.is_live(p)]

    # Moderator comments on posts that didn't stay live: {post id: [(author, text), ...]}.
    # A comment that also sits on posts that stayed live (a pinned rules reminder, a link to
    # the wiki) is boilerplate, not a removal reason, so it is left out.
    all_notes = {}
    for c in sorted(rec.get("mod_comments") or [], key=lambda c: c.get("created_utc") or 0):
        link = (c.get("link_id") or "").removeprefix("t3_")
        top_level = (c.get("parent_id") or "").removeprefix("t3_") == link
        text = arc.clean_comment(c.get("body"))
        if link and top_level and text and arc.is_mod_comment(c):
            all_notes.setdefault(link, []).append((c.get("author"), text))
    live_ids = {p["id"] for p in posts if arc.is_live(p)}
    removed_ids = {p["id"] for p in posts} - live_ids
    boilerplate = {text for pid in live_ids for _, text in all_notes.get(pid, [])}
    notes = {}
    for pid in removed_ids & all_notes.keys():
        kept = [(a, t) for a, t in all_notes[pid] if t not in boilerplate]
        if kept:
            notes[pid] = kept
    not_live = [p for p in sample if not arc.is_live(p)]
    why = Counter(notes[p["id"]][0][1] for p in not_live if p["id"] in notes)

    # posts per week (all submissions, last 28 days ÷ 4)
    posts_wk_note = ""
    if covers(rec, 28):
        posts_wk = sum(1 for p in posts if p["created_utc"] >= now - 28 * DAY) / 4
    elif rec.get("authors_28d") is not None:
        posts_wk = sum(int(a["count"]) for a in rec["authors_28d"]) / 4
    else:  # estimate from the span we have
        span = max(now - oldest, DAY)
        posts_wk = len(posts) / (span / (7 * DAY))
        posts_wk_note = "~"

    # distinct posters in the last 7 days
    recent = {p["author"] for p in posts if p["created_utc"] >= now - 7 * DAY} - NOT_PEOPLE
    if covers(rec, 7):
        posters_wk = str(len(recent))
    elif rec.get("authors_7d") is not None:
        posters_wk = str(sum(1 for a in rec["authors_7d"] if a["key"] not in NOT_PEOPLE))
    else:
        posters_wk = f"≥{len(recent)}"

    members = next((p["subreddit_subscribers"] for p in posts if p.get("subreddit_subscribers") is not None), None)
    return {
        "canonical": posts[0]["subreddit"] if posts else rec["subreddit"],
        "members": members,
        "newest": posts[0]["created_utc"] if posts else None,
        "posts_wk": posts_wk, "posts_wk_note": posts_wk_note,
        "posters_wk": posters_wk,
        "last": last,
        "n_last": len(last),
        "n_sample": len(sample),
        "sample_is_window": sample is in_window,
        "live_share": len(live_sample) / len(sample) if sample else None,
        "mod_share": sum(1 for p in sample if arc.post_status(p) == "removed by mod") / len(sample) if sample else None,
        "median_score": statistics.median(p.get("score") or 0 for p in live_sample) if live_sample else None,
        "median_comments": statistics.median(p.get("num_comments") or 0 for p in live_sample) if live_sample else None,
        "top": top,
        "top_days": round((now - window_start) / DAY),
        "notes_fetched": "mod_comments" in rec,
        "notes": notes,
        "why": why,
        "n_not_live": len(not_live),
        "n_with_note": sum(why.values()),
        "capped": rec["capped"],
        "errors": rec["errors"],
    }


# ---------- markdown helpers ----------

def esc(text, limit=None):
    text = " ".join((text or "").split())
    if limit and len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text.replace("|", "\\|").replace("[", "\\[").replace("]", "\\]")


def esc_note(text, limit=None):
    """Like esc, but keeps [links](...) in moderator comments clickable."""
    text = " ".join((text or "").split())
    if limit and len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text.replace("|", "\\|")


def url(p):
    return "https://www.reddit.com" + p["permalink"]


def day(epoch):
    return arc.utc_date(epoch).isoformat()


def num(n):
    if n is None:
        return "—"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 9_950:
        return f"{n / 1000:.0f}K"
    if n >= 1000:
        return f"{n / 1000:.1f}K"
    if n >= 10 or float(n).is_integer():
        return str(round(n))
    return f"{n:.1f}"


def pct(x):
    return "—" if x is None else f"{x * 100:.0f}%"


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(" --- " for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c) if c not in (None, "") else "—" for c in r) + " |" for r in rows]
    return lines


def posts_table(posts, numbers=None, notes=None):
    """`numbers` maps post id -> its number in the Full text section (adds a # column).
    `notes` maps post id -> moderator comments (adds a Mod comment column)."""
    header = ["Date", "Title", "Author", "Flair", "Link", "Score", "Comments", "Status"]
    rows = []
    for p in posts:
        domain = "text" if (p.get("domain") or "").startswith("self.") else esc(p.get("domain"))
        # With numbers, the title jumps to the post's full text further down the page; otherwise to Reddit.
        target = f"#post-{numbers[p['id']]}" if numbers is not None else url(p)
        row = [day(p["created_utc"]), f"[{esc(p.get('title'), 110)}]({target})", "u/" + esc(p.get("author")),
               esc(p.get("link_flair_text"), 30), domain, p.get("score"), p.get("num_comments"), arc.post_status(p)]
        if numbers is not None:
            row.insert(0, numbers[p["id"]])
        if notes is not None:
            row.append(esc_note(notes[p["id"]][0][1], 100) if p["id"] in notes else "")
        rows.append(row)
    if numbers is not None:
        header.insert(0, "#")
    if notes is not None:
        header.append("Mod comment")
    return table(header, rows)


def post_text(p):
    """A post's body as markdown lines: the text quoted as written, or why there is none."""
    body = (p.get("selftext") or "").strip()
    lines = []
    if not p.get("is_self") and p.get("url"):
        lines.append(f"Link: <{p['url']}>")
        lines.append("")
    if body == "[removed]":
        lines.append("*No text: the post was removed, and the archive only has \"[removed]\".*")
    elif body == "[deleted]":
        lines.append("*No text: deleted by its author.*")
    elif body:
        lines += ["> " + line if line.strip() else ">" for line in body.splitlines()]
    elif p.get("is_self"):
        lines.append("*Title only, no body text.*")
    return lines


PROMO_WORDS = re.compile(r"promot|advertis|self[- ]?promo|vendor|marketing|commercial|solicit|spam|affiliate"
                         r"|blog|your own|product|launch|sell", re.I)
KIND = {"link": " (posts only)", "comment": " (comments only)"}

# Rule titles that decide whether dltHub can post: promotion, links, showcases, vendors, AI-written posts.
KEY_RULE = re.compile(r"promot|advertis|vendor|marketing|commercial|solicit|spam|affiliate|shill|astroturf|pitch|waitlist|"
                      r"blog|brand|showcase|launch|links?\b|AI[- ]generated|AI slop|AI content|\bAI\b", re.I)


def key_rules_cell(sub_name, page, shown=3):
    """README cell: the key rule titles, and a link to all of the sub's rules."""
    if not page:
        return ""
    if not page["has_rules"]:
        return "none of its own"
    keys = [esc_note(t, 45) for t, _ in page["rules"] if KEY_RULE.search(t)]
    link = f"[all {len(page['rules'])}](outcome/subs/{sub_name}.md#rules)"
    if not keys:
        return f"nothing on promotion · {link}"
    more = f" +{len(keys) - shown}" if len(keys) > shown else ""
    return " · ".join(keys[:shown]) + more + f" · {link}"


def visitor_cells(sub, page):
    """(weekly visitors, weekly contributions) as table text. A value typed into the CSV wins."""
    visitors = sub["weekly_visitors"] or (num(page["weekly_visitors"]) if page and page["weekly_visitors"] is not None else "")
    contribs = num(page["weekly_contributions"]) if page and page["weekly_contributions"] is not None else ""
    return visitors, contribs


def rules_section(sub, canonical, rules_rec, page=None):
    rules_url = f"https://www.reddit.com/r/{canonical}/about/rules"
    lines = ["## Rules", ""]
    if page and page["has_rules"]:
        lines += [f"Current rules, from the sub's page as saved on **{page['saved_at']}**. "
                  f"Rules marked 📣 mention promotion, links or products. [Rules on Reddit]({rules_url}).", ""]
        for i, (name, desc) in enumerate(page["rules"], 1):
            mark = " 📣" if PROMO_WORDS.search(name + " " + desc) else ""
            lines.append(f"{i}. **{esc_note(name)}**{mark}")
            if desc:
                lines.append(f"   > {esc_note(desc)}")
        return lines + [""]
    if page:
        return lines + [f"This sub has **no rules of its own**, only Reddit's site-wide rules "
                        f"(checked on the sub's page on {page['saved_at']}).", ""]
    if not rules_rec or not rules_rec.get("rules"):
        return lines + [f"Not in the archive: its rules crawl (Jan–Feb 2025) covers only some subs. "
                        f"Read them on Reddit: [r/{canonical} rules]({rules_url}).", ""]
    when = arc.utc_date(int(rules_rec["retrieved_on"])).strftime("%B %Y") if rules_rec.get("retrieved_on") else "early 2025"
    lines += [f"As of **{when}** (the archive's last crawl), so they may have changed since: "
              f"[current rules on Reddit]({rules_url}). Rules marked 📣 mention promotion, links or products.", ""]
    for i, r in enumerate(sorted(rules_rec["rules"], key=lambda r: r.get("priority") or 0), 1):
        name = " ".join((r.get("short_name") or "").split())
        desc = (r.get("description") or "").strip()
        mark = " 📣" if PROMO_WORDS.search(name + " " + desc) else ""
        lines.append(f"{i}. **{esc_note(name)}**{KIND.get(r.get('kind'), '')}{mark}")
        lines += [f"   > {line}" if line.strip() else "   >" for line in desc.splitlines()] if desc else []
    return lines + [""]


STATUS_NOTE = ("Status is read from the archive's two passes (about 20 seconds and 36 hours after posting): "
               "**live** = visible from the start · **approved** = held at first, then approved by a mod · "
               "**held by automod** = held and never approved · **removed by mod** = removed by a moderator, "
               "at once or after going live · **spam-filtered** = Reddit's own filter · "
               "**deleted by author**. Scores are as of the 36-hour pass.")


# ---------- rendering ----------

def our_posts_by_sub(acc_rec):
    by_sub = {}
    for p in (acc_rec or {}).get("posts", []):
        by_sub.setdefault(p["subreddit"].lower(), []).append(p)
    for v in by_sub.values():
        v.sort(key=lambda p: p["created_utc"], reverse=True)
    return by_sub


def free_from(sub, ours, have_accounts, today):
    if sub["source"] == "own":
        return "no cooldown"
    if not have_accounts:
        return "?"
    if not ours:
        return "now"
    free = arc.utc_date(ours[0]["created_utc"]) + datetime.timedelta(days=COOLDOWN_DAYS)
    return "now" if free <= today else f"**{free.isoformat()}**"


def write_sub_page(sub, s, ours, data_date, rules_rec=None, page=None):
    name = sub["name"]
    visitors, contribs = visitor_cells(sub, page)
    lines = [f"# r/{s['canonical']}", "",
             f"[← Back to the landscape](../reddit_landscape.md) · [Open on Reddit](https://www.reddit.com/r/{s['canonical']}/)", ""]
    if page and page["description"]:
        lines += [f"> {esc_note(page['description'])}" + (f" · created {page['created']}" if page["created"] else ""), ""]
    lines += [
             f"- **Members:** {num(s['members'])}"
             + (f" · **Weekly visitors:** {visitors}" if visitors else "")
             + (f" · **Weekly contributions:** {contribs}" if contribs else ""),
             f"- **Posts per week:** {s['posts_wk_note']}{num(s['posts_wk'])} · **Distinct posters, last 7 days:** {s['posters_wk']}",
             f"- **Fit:** {sub['fit'] or '—'} ({sub['source']})" + (" · **Warehouse sub** (one per launch)" if sub["warehouse"] else ""),
             f"- **Data pulled:** {data_date} from the Arctic Shift archive", ""]
    if s["errors"]:
        lines += [f"> ⚠️ Incomplete pull: {'; '.join(s['errors'])}", ""]

    lines += rules_section(sub, s["canonical"], rules_rec, page)
    lines += [f"## dltHub posts here (last {HISTORY_DAYS} days)", ""]
    lines += posts_table(ours) if ours else ["None found for the accounts in `our_accounts.txt`."]

    # Number every post of the two tables once, for the Full text section.
    numbers, numbered = {}, []
    for p in s["last"] + s["top"]:
        if p["id"] not in numbers:
            numbers[p["id"]] = len(numbers) + 1
            numbered.append(p)

    over = f"the {s['n_sample']} posts of the last {s['top_days']} days" if s["sample_is_window"] else f"these {s['n_sample']} posts"
    lines += ["", "## Why posts get removed here", ""]
    if not s["notes_fetched"]:
        lines += ["Moderator comments not fetched yet."]
    elif not s["n_not_live"]:
        lines += [f"All of {over} stayed live."]
    elif not s["n_with_note"]:
        lines += [f"Of {over}, {s['n_not_live']} didn't stay live, and none of those got a public comment explaining why: "
                  "they were removed silently, or the reason was sent by private message to the author. "
                  "Reddit doesn't publish removal reasons otherwise."]
    else:
        lines += [f"Of {over}, {s['n_not_live']} didn't stay live. {s['n_with_note']} of those got a public comment from "
                  "AutoModerator or the moderators explaining it, shown below. The rest were removed without a public reason "
                  "(silently, or by private message to the author); Reddit doesn't publish removal reasons otherwise. "
                  "Comments that also appear on posts that stayed live (rules reminders, wiki links) are left out.", ""]
        if s["why"]:
            lines += table(["Posts", "Comment left on the removed post"],
                           [[n, esc_note(text, 300)] for text, n in s["why"].most_common(10)])

    lines += ["", f"## Last {LAST_N} posts", "",
              f"The {s['n_last']} newest posts that are at least {arc.SETTLE_HOURS} hours old, so their status and score have settled. "
              f"Over {over}: live {pct(s['live_share'])} · removed by mods {pct(s['mod_share'])}. "
              "The full text of each post is under [Full text](#full-text), by its **#**.", "", STATUS_NOTE, ""]
    lines += posts_table(s["last"], numbers, s["notes"]) if s["last"] else ["No posts in the archive."]

    lines += ["", f"## Top {TOP_N} posts, last {WINDOW_DAYS} days", ""]
    if s["top_days"] < WINDOW_DAYS:
        lines += [f"> Very active sub: only the newest {MAX_PAGES} pages of posts were pulled, so this covers the last "
                  f"{s['top_days']} days, not {WINDOW_DAYS}.", ""]
    lines += ["Posts that stayed live, by score.", ""]
    lines += posts_table(s["top"], numbers) if s["top"] else ["No live posts in this window."]

    lines += ["", "## Full text", "",
              "Every post from the two tables above, numbered as in their **#** column, with its text as the archive read it "
              "about 20 seconds after posting. Removed posts usually have no text left.", ""]
    for p in numbered:
        info = [day(p["created_utc"]), "u/" + esc(p.get("author")), esc(p.get("link_flair_text")),
                f"score {p.get('score')}", f"{p.get('num_comments')} comments", arc.post_status(p),
                f"[open on Reddit]({url(p)})", f"[↑ back to the list](#last-{LAST_N}-posts)"]
        n = numbers[p["id"]]
        lines += [f'<a id="post-{n}"></a>', "", f"### {n}. {esc(p.get('title'))}", "", " · ".join(x for x in info if x), ""]
        lines += post_text(p) + [""]
        for author, text in s["notes"].get(p["id"], []):
            lines += [f"**Mod comment** (u/{esc(author)}): {esc_note(text)}", ""]

    SUBS_DIR.mkdir(exist_ok=True)
    (SUBS_DIR / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render(subs, day_dir, accounts):
    today = datetime.date.today()
    data_date = day_dir.name
    acc_rec = load(day_dir / "_our_accounts.json")
    ours_by_sub = our_posts_by_sub(acc_rec)
    rules = load(day_dir / "_rules.json") or {}
    pages = load_pages()
    have_accounts = bool(accounts) and acc_rec is not None

    rows, inactive, missing, total_posts = [], [], [], 0
    front = []  # (fit, weekly visitors, cells) for the repo's front-page README
    for sub in subs:
        rec = load(day_dir / f"{sub['name']}.json")
        if rec is None:
            missing.append(sub)
            continue
        total_posts += len(rec["posts"])
        s = summarize(rec)
        ours = ours_by_sub.get(s["canonical"].lower(), [])
        page = pages.get(s["canonical"].lower()) or pages.get(sub["name"].lower())
        write_sub_page(sub, s, ours, data_date, rules.get(s["canonical"].lower()) or rules.get(sub["name"].lower()), page)
        visitors, contribs = visitor_cells(sub, page)

        if not s["newest"]:
            inactive.append((sub, s, "no posts in the archive"))
            continue
        if s["newest"] < rec["fetched_at"] - DEAD_DAYS * DAY:
            inactive.append((sub, s, f"last post {day(s['newest'])}"))
            continue

        top = s["top"][0] if s["top"] else None
        top_cell = f"[{esc(top['title'], 60)}]({url(top)}) ({top['score']})" if top else "—"
        if top and s["top_days"] < WINDOW_DAYS:
            top_cell += f" · {s['top_days']} d"
        last_ours = ours[0] if ours else None
        n_note = "" if s["n_sample"] >= LAST_N else f" (n={s['n_sample']})"
        median = "—" if s["median_score"] is None else f"{num(s['median_score'])} / {num(s['median_comments'])}"
        visitors_n = int(sub["weekly_visitors"]) if sub["weekly_visitors"].isdigit() else (page or {}).get("weekly_visitors") or 0
        last_posted = day(ours[0]["created_utc"]) if ours else ("never" if have_accounts else "?")
        cooldown_end = arc.utc_date(ours[0]["created_utc"]) + datetime.timedelta(days=COOLDOWN_DAYS) if ours else None
        if sub["source"] == "own":
            cooldown = "own sub"
        elif not have_accounts:
            cooldown = "?"
        else:
            cooldown = cooldown_end.isoformat() if cooldown_end and cooldown_end > today else "—"
        front.append((int(sub["fit"] or 0), visitors_n, [
            f"[r/{s['canonical']}](outcome/subs/{sub['name']}.md#last-{LAST_N}-posts)", sub["fit"], num(s["members"]), visitors,
            num(s["posts_wk"]), pct(s["live_share"]), key_rules_cell(sub["name"], page), last_posted, cooldown]))
        rows.append((
            0 if sub["source"] == "own" else 1, -(s["members"] or 0),
            [f"[r/{s['canonical']}](subs/{sub['name']}.md)" + (" ⚠️" if s["errors"] else ""),
             sub["fit"],
             num(s["members"]),
             visitors,
             contribs,
             s["posts_wk_note"] + num(s["posts_wk"]),
             s["posters_wk"],
             median,
             f"{pct(s['live_share'])} / {pct(s['mod_share'])}{n_note}",
             top_cell,
             "W" if sub["warehouse"] else "",
             f"[{day(last_ours['created_utc'])}]({url(last_ours)})" if last_ours else ("?" if not have_accounts else "—"),
             free_from(sub, ours, have_accounts, today)]))
    rows.sort(key=lambda r: (r[0], r[1]))

    acc_note = (", ".join(f"u/{a}" for a in accounts) if accounts else "none listed") + " (`our_accounts.txt`)"
    if accounts and not accounts_confirmed():
        acc_note += ". ⚠️ **Unconfirmed list**: found as the top posters in our own subs, not yet checked with Adrian, " \
                    "so treat the cooldown columns as a guide"
    lines = ["# Reddit landscape for dltHub launches", "",
             f"One row per subreddit, data pulled **{data_date}** from the Arctic Shift archive. "
             f"Click a subreddit for its last {LAST_N} posts, its top {TOP_N} posts of the last {WINDOW_DAYS} days and our own posts there.", "",
             f"**Standing rules:** {COOLDOWN_DAYS}-day cooldown per sub (own subs exempt) · one warehouse sub (**W**) per launch · "
             "Aman or Hiba reviews every post before it goes up.", "",
             f"**Accounts checked for the cooldown:** {acc_note}.", ""]
    lines += table(["Subreddit", "Fit", "Members", "Weekly visitors", "Contribs / wk", "Posts / wk", "Posters / wk",
                    "Median score / comments", "Live / mod-removed", f"Top post ({WINDOW_DAYS} d)", "W",
                    "Last dltHub post", "Free from"], [r[2] for r in rows])

    lines += ["", "## How to read the columns", "",
              "- **Fit**: Adrian's score (5 = favorite … 0 = never) for his subs, my unverified guess for the new candidates.",
              "- **Members**: subscriber count on the newest archived post.",
              "- **Weekly visitors / Contribs / wk**: Reddit's own figures for the last week (visitors, and posts plus comments), "
              "read from each sub's page, saved by hand with the bookmark in `data/manual/collector.html`. "
              "A value typed into `landscape_subs.csv` overrides the visitors.",
              "- **Posts / wk**: every post submitted in the last 28 days ÷ 4, including ones that were filtered or removed. "
              "A `~` means it was estimated from the posts pulled.",
              "- **Posters / wk**: distinct accounts that posted in the last 7 days, without AutoModerator. A proxy for weekly activity.",
              f"- **Live / mod-removed**: share of posts that were visible 36 hours after posting, and share removed by a moderator. "
              f"Measured over the last {WINDOW_DAYS} days, or over the last {LAST_N} posts when a sub had fewer than {LAST_N} in that time "
              "(`n=` marks fewer than 50). A low live share with few mod removals means AutoModerator or Reddit's spam filter holds most posts.",
              "- **Median score / comments**: over the live posts in the same sample (scores as of 36 hours after posting).",
              f"- **Top post**: the highest-scoring live post in the last {WINDOW_DAYS} days (fewer days for the very largest subs, marked).",
              "- **W**: warehouse sub, from `landscape_subs.csv`.",
              f"- **Last dltHub post / Free from**: newest post by our accounts in that sub, and the date the {COOLDOWN_DAYS}-day cooldown ends. "
              "**now** = free to post today.",
              "- ⚠️ after a name: the pull was incomplete; see the sub's page.", "",
              "## What this table can't show", "",
              "- **Why most posts were removed**: Reddit publishes a reason only when moderators leave a public comment. "
              "Most removals, vendor posts especially, are silent. Each sub's page lists the reasons that are public.", ""]

    sub_pages = [pages.get(sub["name"].lower()) for sub in subs]
    n_own_rules = sum(1 for p in sub_pages if p and p["has_rules"])
    n_no_rules = sum(1 for p in sub_pages if p and not p["has_rules"])
    n_unsaved = sum(1 for p in sub_pages if not p)
    rules_note = (f"✅ current rules for the {n_own_rules} subs that have their own; {n_no_rules} have none of their own"
                  + (f"; {n_unsaved} not saved (the not-active subs)" if n_unsaved else ""))
    lines += ["## Data for Step 4 of the brief", "",
              "Step 4 has an LLM judge each subreddit on eight fields. What this run collected for each:", ""]
    lines += table(["Step 4 field", "Have the data?"], [
        ["1. Size and activity", "✅ members, weekly visitors and contributions, posts and posters per week"],
        ["2. Promo rules: quote the rule, pick a category", rules_note],
        ["3. Enforcement in practice", "✅ live and removed shares, removal reasons, example posts"],
        ["4. Audience", "✅ full text of recent and top posts"],
        ["5. Attitude toward AI", "✅ same"],
        ["6. Stack", "✅ same"],
        ["7. dltHub fit", "✅ all of the above plus how our own posts did"],
        ["8. Recommended action", "✅ follows from the rest"]])
    lines += [""]

    if inactive:
        lines += [f"## Not active (no post in {DEAD_DAYS} days)", ""]
        lines += [f"- r/{s['canonical']} ({sub['source']}, fit {sub['fit'] or '—'}): {num(s['members'])} members, {why}"
                  for sub, s, why in inactive]
        lines += [""]
    if missing:
        lines += ["## Not fetched yet", ""]
        lines += [", ".join(f"r/{m['name']}" for m in missing), ""]

    raw_mb = sum(f.stat().st_size for f in day_dir.glob("*.json")) / 1e6
    lines += ["## Data", "",
              f"{len(rows) + len(inactive)} subreddits, {total_posts:,} posts, {raw_mb:.1f} MB of raw JSON in `data/raw/{data_date}/`. "
              "Rebuild with `python scripts/landscape/build_landscape.py`; after filling weekly visitors, add `--render-only`."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # The repo's front page: just the database, minimal.
    front.sort(key=lambda r: (-r[0], -r[1]))
    readme = ["# Reddit landscape for dltHub", "", f"{len(front)} active subreddits · data as of {data_date}", ""]
    readme += table(["Subreddit", "Fit", "Members", "Weekly visitors", "Posts / week", "Posts that stay up",
                     "Key rules", "Last posted", "Cooldown until"],
                    [r[2] for r in front])
    FRONT_MD.write_text("\n".join(readme) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT_MD.name}: {len(rows)} active, {len(inactive)} not active, {len(missing)} not fetched; "
          f"{total_posts:,} posts, {raw_mb:.1f} MB raw", flush=True)


# ---------- main ----------

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = sys.argv[1:]
    render_only = "--render-only" in args
    only = {a.lower().removeprefix("r/") for a in args if not a.startswith("--")}
    subs = read_subs()
    accounts = read_accounts()

    if render_only:
        days = sorted(d for d in RAW.glob("*") if d.is_dir()) if RAW.exists() else []
        if not days:
            raise SystemExit("No data in data/raw/ yet. Run without --render-only first.")
        render(subs, days[-1], accounts)
        return

    now = int(time.time())
    day_dir = RAW / datetime.date.today().isoformat()
    targets = [s for s in subs if not only or s["name"].lower() in only]
    unknown = only - {s["name"].lower() for s in subs}
    if unknown:
        print(f"not in landscape_subs.csv, ignored: {', '.join(sorted(unknown))}")
    for i, sub in enumerate(targets, 1):
        path = day_dir / f"{sub['name']}.json"
        t = time.time()
        rec = load(path)
        if rec is not None and "mod_comments" in rec:
            print(f"[{i}/{len(targets)}] r/{sub['name']}: already fetched today, skipped", flush=True)
            continue
        if rec is not None:  # fetched before mod comments existed: add just those
            save(path, fetch_mod_comments(rec, rec["fetched_at"]))
            print(f"[{i}/{len(targets)}] r/{sub['name']}: added {len(rec['mod_comments'])} mod comments"
                  f"{', ERRORS: ' + '; '.join(rec['errors']) if rec['errors'] else ''} ({time.time() - t:.0f}s)", flush=True)
            continue
        rec = fetch_sub(sub["name"], now)
        save(path, rec)
        print(f"[{i}/{len(targets)}] r/{sub['name']}: {len(rec['posts'])} posts, {rec['pages']} pages"
              f"{', capped' if rec['capped'] else ''}{', ERRORS: ' + '; '.join(rec['errors']) if rec['errors'] else ''}"
              f" ({time.time() - t:.0f}s)", flush=True)
        time.sleep(arc.PAUSE)

    print(f"\nour accounts: {', '.join(accounts) or 'none listed in our_accounts.txt'}", flush=True)
    save(day_dir / "_our_accounts.json", fetch_accounts(accounts, now))
    rules_path = day_dir / "_rules.json"
    known = load(rules_path) or {}
    if not known or any(s["name"].lower() not in known.get("_asked", []) for s in subs):
        time.sleep(arc.PAUSE)
        rules = fetch_rules([s["name"] for s in subs])
        if rules is not None:
            rules["_asked"] = [s["name"].lower() for s in subs]
            save(rules_path, rules)
    render(subs, day_dir, accounts)


if __name__ == "__main__":
    main()
