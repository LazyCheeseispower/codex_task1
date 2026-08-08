#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch AI-related Hacker News stories for the last N hours.

Uses the public HN Algolia search API. Output is a JSON candidate list for the
daily curating step; the Codex run still selects and rewrites the final items.
"""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone


QUERIES = [
    "AI", "LLM", "OpenAI", "Anthropic", "DeepMind", "machine learning",
    "AGI", "GPT", "Claude", "Gemini", "robotics", "neural",
]

KEYWORD_RE = re.compile(
    r"(ai|a\.i\.|llm|gpt|openai|anthropic|deepmind|claude|gemini|machine learning|"
    r"ml|agent|model|neural|robotics|robot|agi|diffusion|transformer|inference|"
    r"token|compute|data center|chip|nvidia|meta|google|microsoft|apple|amazon|"
    r"mistral|llama|qwen|moonshot|baidu|alibaba|byte)",
    re.I,
)


def fetch_hits(query, since_ts, per_page=100):
    params = {
        "query": query,
        "tags": "story",
        "numericFilters": "created_at_i>%d,points>30" % since_ts,
        "hitsPerPage": per_page,
    }
    url = "https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "codex-ai-daily-ppt/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    return data.get("hits", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=40)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    since_ts = int((now - timedelta(hours=args.hours)).timestamp())
    seen = {}
    stories = []
    for query in QUERIES:
        try:
            hits = fetch_hits(query, since_ts)
        except Exception as exc:
            print("query %r failed: %s" % (query, exc), file=sys.stderr)
            continue
        for hit in hits:
            title = hit.get("title") or ""
            if not KEYWORD_RE.search(title):
                continue
            oid = hit.get("objectID")
            if not oid or oid in seen:
                continue
            seen[oid] = True
            stories.append({
                "id": oid,
                "title": title,
                "url": hit.get("url") or "",
                "hn_url": "https://news.ycombinator.com/item?id=%s" % oid,
                "points": hit.get("points") or 0,
                "comments": hit.get("num_comments") or 0,
                "author": hit.get("author") or "",
                "created_at": hit.get("created_at") or "",
            })

    stories.sort(key=lambda s: (s["points"], s["comments"]), reverse=True)
    stories = stories[:args.limit]
    payload = {
        "date": now.strftime("%Y-%m-%d"),
        "fetched_at": now.isoformat(),
        "window_hours": args.hours,
        "stories": stories,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("saved %d stories to %s" % (len(stories), args.out))


if __name__ == "__main__":
    main()
