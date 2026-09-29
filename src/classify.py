"""Classify ticket text into the fixed taxonomy.

Two methods:
  keyword  - offline baseline, no API key. Also the thing the LLM has to beat.
  llm      - one call per ticket, PII redacted first, results cached in SQLite
             so re-runs cost nothing.
"""
import hashlib
import json
import os
import re
import sqlite3
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

import config
from src.redact import redact

CATS = list(config.TAXONOMY)
_lock = threading.Lock()
usage = {"calls": 0, "cached": 0, "in": 0, "out": 0, "parse_fail": 0}


def keyword_classify(text):
    t = text.lower()
    scores = {c: sum(t.count(k) for k in kws) for c, (_, kws) in config.TAXONOMY.items()}
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return {"primary": "other", "secondary": None, "confidence": "low"}
    ranked = sorted((s, c) for c, s in scores.items() if s > 0)[::-1]
    sec = ranked[1][1] if len(ranked) > 1 else None
    return {"primary": best, "secondary": sec, "confidence": "low"}


def _prompt(message):
    tmpl = (config.ROOT / "prompts" / f"{config.PROMPT_VERSION}.txt").read_text()
    tax = "\n".join(f"- {c}: {d}" for c, (d, _) in config.TAXONOMY.items())
    return tmpl.format(taxonomy=tax, message=message[:2000])


def _parse(raw):
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        d = json.loads(m.group(0))
        assert d.get("primary") in CATS
        if d.get("secondary") not in CATS:
            d["secondary"] = None
        return d
    except Exception:
        return None


class Cache:
    def __init__(self):
        config.OUT.mkdir(exist_ok=True)
        self.db = sqlite3.connect(config.OUT / "cache.sqlite", check_same_thread=False)
        self.db.execute("create table if not exists c (k text primary key, v text)")

    def get(self, k):
        with _lock:
            r = self.db.execute("select v from c where k=?", (k,)).fetchone()
        return json.loads(r[0]) if r else None

    def put(self, k, v):
        with _lock:
            self.db.execute("insert or replace into c values (?,?)", (k, json.dumps(v)))
            self.db.commit()


def _llm_one(client, cache, text):
    prompt = _prompt(redact(text))
    key = hashlib.sha256(f"{config.MODEL}|{prompt}".encode()).hexdigest()
    hit = cache.get(key)
    if hit:
        with _lock:
            usage["cached"] += 1
        return hit
    resp = client.messages.create(model=config.MODEL, max_tokens=120,
                                  messages=[{"role": "user", "content": prompt}])
    raw = "".join(b.text for b in resp.content if b.type == "text")
    d = _parse(raw)
    with _lock:
        usage["calls"] += 1
        usage["in"] += resp.usage.input_tokens
        usage["out"] += resp.usage.output_tokens
        if d is None:
            usage["parse_fail"] += 1
    d = d or {"primary": "other", "secondary": None, "confidence": "parse_fail"}
    cache.put(key, d)
    return d


def classify(df, field="customer_message", method="keyword", workers=8):
    texts = df[field].tolist()
    if method == "keyword":
        res = [keyword_classify(x) for x in texts]
    else:
        if not os.getenv("ANTHROPIC_API_KEY"):
            sys.exit("ANTHROPIC_API_KEY not set. Use --method keyword to run offline.")
        import anthropic
        client, cache = anthropic.Anthropic(), Cache()
        with ThreadPoolExecutor(workers) as ex:
            res = list(ex.map(lambda x: _llm_one(client, cache, x) if x.strip()
                              else {"primary": "other", "secondary": None, "confidence": "empty"}, texts))
    out = pd.DataFrame(res)
    out.insert(0, "ticket_id", df["ticket_id"].values)
    out["method"] = method
    return out


def cost_summary():
    usd = usage["in"] / 1e6 * config.PRICE_IN_PER_M + usage["out"] / 1e6 * config.PRICE_OUT_PER_M
    n = max(usage["calls"], 1)
    per_ticket = usd / n
    month = per_ticket * 650 * 52 / 12
    return {**usage, "usd_this_run": round(usd, 4),
            "usd_per_ticket": round(per_ticket, 6),
            "usd_per_month_at_650_per_week": round(month, 2),
            "inr_per_month": round(month * config.USD_TO_INR, 0),
            "prices_used_per_M": [config.PRICE_IN_PER_M, config.PRICE_OUT_PER_M]}
