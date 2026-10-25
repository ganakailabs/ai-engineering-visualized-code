"""Tolerant parsing of model replies, shared by every chapter.

Real models wrap answers in many ways: "<approve>", "**Deny**: ...", code
fences, a friendly sentence before the JSON. These helpers find the part your
code needs, or return None. A None is never a crash: the caller turns it into
a safe escalate and prints why (warn). That is the lesson: parse, check, and
fall back safely.
"""
import json
import re
import sys

DECISIONS = ("approve", "deny", "escalate")


def warn(why):
    print(f"[parse] {why}", file=sys.stderr)


def _clean(text):
    text = re.sub(r"```[a-zA-Z]*", " ", str(text))       # code fences
    return text.replace("`", " ").strip()


def label(text, allowed):
    """First allowed label in the reply: at the start once wrappers are
    stripped, or anywhere as '<label>' / 'label:'. Else None."""
    words = "|".join(map(re.escape, allowed))
    low = _clean(text).lower()
    start = re.sub(r"^[\s<*\"'\[(]+", "", low)           # <, **, quotes ...
    m = re.match(rf"({words})(?![a-z])", start)
    if m:
        return m.group(1)
    m = re.search(rf"<\s*({words})\s*>|(?<![a-z])({words})\s*\**\s*:", low)
    return (m.group(1) or m.group(2)) if m else None


def decision_reply(text, allowed=DECISIONS + ("answer", "done")):
    """'<Deny>  Final sale (R3)' -> 'deny: Final sale (R3)'. None if no label."""
    found = label(text, allowed)
    if found is None:
        return None
    clean = _clean(text)
    m = re.search(rf"<?\s*\**{found}\**\s*>?\s*[:\-]?\s*", clean, re.I)
    reason = clean[m.end():].strip() if m else clean
    return f"{found}: {reason}"


def first_json(text, kinds=(dict, list)):
    """The first JSON object (or list) anywhere in the reply, else None."""
    text = _clean(text)
    dec = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch in "{[":
            try:
                value, _ = dec.raw_decode(text[i:])
            except json.JSONDecodeError:
                continue
            if isinstance(value, kinds):
                return value
    return None
