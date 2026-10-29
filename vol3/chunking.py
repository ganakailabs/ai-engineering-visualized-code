"""Chunks that follow the document, small-to-big, and applicability tags (Vol 3 Ch 4).

The returns handbook in vol3/knowledge/policy/ is a fictional fixture with one section per
clause and a tags line under each heading. section_chunks() cuts at headings and keeps
the tags; small_chunks() cuts each section into sentences with a parent link;
applies() is the gate: a chunk is used only if every required tag is present and
matches the question's product, region and date. A missing tag means "not applicable".
A malformed date excludes the chunk; an optional effective_to tag ends a clause.
Supersession (a newer clause replacing an older one) is Chapter 10's precedence, not
this filter. A heading-based chunk is a better unit than a fixed cut; it is not a
guarantee that the chunk holds the clause's complete meaning.
"""
import re
from datetime import date
from pathlib import Path

import _root  # noqa: F401

import events
from events import Trace
from ingest import _Clock
from store import TODAY

HANDBOOK = Path(__file__).resolve().parent / "knowledge" / "policy" / "returns-handbook.md"
REQUIRED = ("product", "region", "doc_type", "effective_from")
events.KINDS.update({"filter", "expand"})        # Vol 3 (series contract section 4)


def read(path=HANDBOOK):
    head, _, body = Path(path).read_text().partition("\n# ")
    meta = dict(re.findall(r"^(\w+): (.+)$", head, re.M))
    return meta, "# " + body


def fixed_chunks(body, size=12, overlap=0):
    """The naive cut: every `size` words, headings and tags stripped.
    With overlap, each chunk repeats the last `overlap` words of the one before."""
    text = " ".join(l for l in body.splitlines()
                    if l.strip() and not l.startswith(("#", "tags:")))
    w = text.split()
    step = size - overlap
    return [" ".join(w[i:i + size]) for i in range(0, len(w), step)]


def section_chunks(meta, body):
    out = []
    for sec in re.split(r"^## ", body, flags=re.M)[1:]:
        title, _, rest = sec.partition("\n")
        tags = dict(re.findall(r"(\w+)=(\S+)", rest.splitlines()[0])) \
            if rest.startswith("tags:") else {}
        text = " ".join(l for l in rest.splitlines()[1 if tags else 0:] if l.strip())
        cid = f"{meta['source']}@{meta['version']}:{title.split()[0]}"
        out.append({"id": cid, "title": title, "tags": tags, "text": text})
    return out


def small_chunks(parents):
    out = []
    for p in parents:
        for n, s in enumerate(re.split(r"(?<=\.)\s+", p["text"]), 1):
            out.append({"id": f"{p['id']}.s{n}", "parent": p["id"], "text": s})
    return out


def applies(tags, product, region, today=TODAY):
    """(True, '') or (False, reason). Missing tags are 'not applicable', never 'all'."""
    missing = [k for k in REQUIRED if k not in tags]
    if missing:
        return False, f"tag missing ({', '.join(missing)})"
    if tags["product"] not in ("ALL", product):
        return False, f"product={tags['product']}"
    if tags["region"] not in ("ALL", region):
        return False, f"region={tags['region']}"
    try:
        start = date.fromisoformat(tags["effective_from"])
    except ValueError:
        return False, f"effective_from={tags['effective_from']!r} is not a date"
    if start > today:
        return False, f"effective_from={start} today={today}"
    if "effective_to" in tags:                 # optional: a clause that has ended
        try:
            end = date.fromisoformat(tags["effective_to"])
        except ValueError:
            return False, f"effective_to={tags['effective_to']!r} is not a date"
        if end < today:
            return False, f"effective_to={end} today={today}"
    return True, ""


def gate(parents, product, region, today=TODAY, trace=None):
    kept = []
    for p in parents:
        ok, why = applies(p["tags"], product, region, today)
        if ok:
            kept.append(p)
        elif trace:
            trace.emit("filter", f"{p['id'].split(':')[1]} {why} -> excluded",
                       chunk=p["id"], reason=why)
    return kept


def words(t):
    return set(re.findall(r"[a-z0-9]+", t.lower()))


def best_small(question, smalls):
    return max(smalls, key=lambda s: len(words(question) & words(s["text"])))


def answer_context(question, product, region, today=TODAY, echo=True):
    """Gate the sections, search the small chunks, hand back the parent section."""
    meta, body = read()
    t = Trace(_Clock(), "T-104", "asha", echo=echo)
    parents = gate(section_chunks(meta, body), product, region, today, t)
    hit = best_small(question, small_chunks(parents))
    parent = next(p for p in parents if p["id"] == hit["parent"])
    t.emit("retrieve", f"small hit={hit['id'].split(':')[1]}", chunk=hit["id"])
    t.emit("expand", f"parent={parent['id'].split(':')[1]} words={len(parent['text'].split())}",
           parent=parent["id"])
    return {"trace": t, "hit": hit, "parent": parent, "kept": [p["id"] for p in parents]}
