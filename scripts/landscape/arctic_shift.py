"""Small client for the Arctic Shift Reddit archive (https://arctic-shift.photon-reddit.com).

Python standard library only. Used by build_landscape.py, and meant to be reused by the
later posting-history check from Adrian's brief. Keep callers on these functions so the
source can be swapped (e.g. for Apify) without touching them.

API docs: https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md
Notes from testing in Nov 2026 (see data_sources.md):
- Posts can only be sorted by created_utc. There is no score sort, so "top posts" means
  pulling a window and sorting locally.
- limit="auto" returns 100 to 1,000 posts per call, depending on server load.
- Rate limits are dynamic; 4 to 6 seconds between calls was fine. Being too fast answers
  HTTP 422 "Timeout. Maybe slow down a bit".
- Passing fields=<names> answers 400, so we always take full objects (and slim them).
- aggregate=created_utc&frequency=week returned 0 for every bucket (broken), but
  aggregate=author works and is fast, so post and poster counts come from that.
"""
import datetime
import json
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://arctic-shift.photon-reddit.com/api/"
UA = "dlthub-reddit-landscape/0.1 (research; contact: aman)"
PAUSE = 5  # seconds between calls

# A post's score and comment count are re-read once, about 36 hours after it was posted.
# Posts younger than this still show their score at +20 seconds.
SETTLE_HOURS = 48


def get(endpoint, params, tries=5):
    """GET BASE + endpoint. Returns the "data" list ([] if empty) or None if the call failed."""
    url = BASE + endpoint + "?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read())
            if d.get("data") is None and d.get("error"):
                wait = 15 * (attempt + 1)
                print(f"    api error '{d['error']}', waiting {wait}s", flush=True)
                time.sleep(wait)
                continue
            return d.get("data") or []
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode()[:200]
            except Exception:
                pass
            if e.code == 429:
                wait = int(e.headers.get("X-RateLimit-Reset") or 20) + 2
                print(f"    429, waiting {wait}s", flush=True)
                time.sleep(wait)
                continue
            if e.code >= 500 or (e.code == 422 and "Timeout" in body):
                wait = 20 * (attempt + 1)
                print(f"    http {e.code}, retrying in {wait}s", flush=True)
                time.sleep(wait)
                continue
            print(f"    http {e.code}: {body}", flush=True)
            return None
        except Exception as e:
            print(f"    error {e}, retrying in 10s", flush=True)
            time.sleep(10)
    return None


def iter_post_pages(subreddit=None, author=None, after=None, before=None):
    """Yield pages of posts, newest first, walking back in time. See iter_pages."""
    return iter_pages("posts", subreddit=subreddit, author=author, after=after, before=before)


def iter_comment_pages(subreddit=None, author=None, after=None, before=None):
    """Yield pages of comments, newest first, walking back in time. See iter_pages."""
    return iter_pages("comments", subreddit=subreddit, author=author, after=after, before=before)


def iter_pages(kind, subreddit=None, author=None, after=None, before=None):
    """Yield pages of posts or comments (`kind`), newest first, walking back in time.

    `after` / `before` are dates ("2026-10-01") or epoch seconds. The caller decides when
    to stop. If a call fails, yields None once and stops, so the caller can tell a complete
    pull from a partial one.
    """
    while True:
        q = {"limit": "auto", "sort": "desc"}
        if subreddit:
            q["subreddit"] = subreddit
        if author:
            q["author"] = author
        if after:
            q["after"] = after
        if before:
            q["before"] = before
        items = get(f"{kind}/search", q)
        if items is None:
            yield None
            return
        if not items:
            return
        yield items
        if len(items) < 100:  # limit=auto returns at least 100 when more exist
            return
        before = int(items[-1]["created_utc"]) - 1
        time.sleep(PAUSE)


def aggregate_authors(subreddit, after, before):
    """Posts per author in a window: [{"key": author, "count": "3"}, ...] or None on failure.

    Summing the counts gives the number of posts in the window, and the list length the
    number of distinct posters, in one call even for very large subs.
    """
    return get("posts/search/aggregate",
               {"aggregate": "author", "subreddit": subreddit, "after": after, "before": before, "limit": ""},
               tries=3)


def is_settled(post, now=None):
    """True once the archive's 36-hour second pass has updated score and comments."""
    now = now or time.time()
    return now - post["created_utc"] >= SETTLE_HOURS * 3600


# Status names. "live" and "approved" mean the post was visible at the 36-hour second pass.
INITIAL = {"moderator": "removed by mod", "automod_filtered": "held by automod",
           "reddit": "spam-filtered", "deleted": "deleted by author"}
LIVE_STATUSES = ("live", "approved")


def post_status(post):
    """What happened to a post, read from the archive's moderation fields.

    The archive reads each post twice: about 20 seconds after posting
    (removed_by_category) and about 36 hours later (_meta). Checked on r/dataengineering,
    r/snowflake and r/Python on 9 Nov 2026:
    - _meta.was_deleted_later + removal_type: the post was visible at first and removed
      afterwards (by a moderator, Reddit's filter or its author).
    - _meta.was_initially_deleted, title not replaced by "[ Removed ... ]": the post was
      held at first and visible at the second pass, i.e. a moderator approved it.
    - Held at first and "[ Removed by moderator ]" at the second pass: never approved.
    """
    cat = post.get("removed_by_category")
    meta = post.get("_meta") or {}
    title2 = meta.get("edited_title") or ""
    if meta.get("was_deleted_later"):
        rt = meta.get("removal_type")
        return INITIAL.get(rt, rt or "removed later")
    if cat is None:
        return "live"
    if meta.get("was_initially_deleted") and not title2.startswith("[ Removed"):
        return "approved"
    if "retrieved_2nd_on" not in meta and cat in ("automod_filtered", "reddit"):
        # No second pass recorded: traction means a moderator let it through.
        if (post.get("score") or 0) >= 5 or (post.get("num_comments") or 0) >= 5:
            return "approved"
    return INITIAL.get(cat, cat)  # content_takedown, copyright_takedown, ...


def is_live(post):
    return post_status(post) in LIVE_STATUSES


# Fields kept in the raw files: enough for the landscape, Step 4 classification and the
# posting-history check. Full objects are ~3 KB per post, mostly fields we never read.
KEEP = ("id", "created_utc", "retrieved_on", "subreddit", "subreddit_subscribers", "subreddit_type",
        "author", "author_flair_text", "title", "selftext", "link_flair_text", "domain", "url", "permalink",
        "is_self", "over_18", "stickied", "distinguished", "score", "num_comments", "upvote_ratio",
        "removed_by_category", "mod_reason_title", "banned_by", "approved_by", "_meta")


def slim(post):
    return {k: post.get(k) for k in KEEP if k in post}


# ---------- moderator comments (the only public trace of a removal reason) ----------
# Reddit hides removal fields (mod_reason_title, banned_by, ...) from non-moderators; they
# were empty on all ~970 removed posts checked. What is public: the comment AutoModerator
# or the sub's "<sub>-ModTeam" account leaves on a post when a mod picks a removal reason.
# Many removals, vendor posts especially, get no comment at all (silent, or by private message).

KEEP_COMMENT = ("id", "link_id", "parent_id", "author", "body", "distinguished", "created_utc")


def mod_authors(subreddit):
    return ["AutoModerator", f"{subreddit}-ModTeam"]


def is_mod_comment(c):
    author = (c.get("author") or "").lower()
    return author == "automoderator" or author.endswith("-modteam") or c.get("distinguished") == "moderator"


def clean_comment(body):
    """One line, without AutoModerator's "I am a bot" footer."""
    text = " ".join((body or "").split())
    cut = text.find("*I am a bot")
    return text[:cut].strip() if cut > 0 else text


def utc_date(epoch):
    return datetime.datetime.fromtimestamp(epoch, datetime.UTC).date()
