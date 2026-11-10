"""Chapter 3: MM-121 What to Log, What Not To. Redact at the sink, then scan.

Every log line passes through one sink. The sink masks email addresses and phone
numbers (the Vol 1 Ch 23 patterns) and the names of known customers, and drops
fields that are never logged (the full ticket text). A scan over the written file
is the test: it must find nothing.
"""
import json
import re

import _root  # noqa: F401

from store import CUSTOMERS

PII = {"EMAIL": r"[\w.+-]+@[\w-]+\.[\w.]+",            # same patterns as Vol 1 Ch 23
       "PHONE": r"\+?\d[\d ]{8,}\d"}
NAMES = sorted({c["name"] for c in CUSTOMERS.values()}, key=len, reverse=True)
NEVER = {"ticket_text", "gen_ai.input.messages", "gen_ai.output.messages"}


def redact(text):
    for kind, pattern in PII.items():
        text = re.sub(pattern, f"[{kind}]", text)
    for name in NAMES:
        for part in (name, *name.split()):                # "Asha Rao", then "Asha", "Rao"
            text = re.sub(rf"\b{re.escape(part)}\b", "[NAME]", text)
    return text


class Sink:
    def __init__(self, path, redacting=True):
        self.path, self.redacting = path, redacting
        open(path, "w").close()

    def write(self, record):
        if self.redacting:
            record = {k: (redact(v) if isinstance(v, str) else v)
                      for k, v in record.items() if k not in NEVER}
        line = json.dumps(record, sort_keys=True)
        with open(self.path, "a") as f:
            f.write(line + "\n")
        return line


def scan(path):
    """The log test: every match of a personal-data pattern or a known name."""
    hits = []
    for n, line in enumerate(open(path), 1):
        for kind, pattern in PII.items():
            hits += [(n, kind) for _ in re.findall(pattern, line)]
        hits += [(n, "NAME") for name in NAMES for part in name.split()
                 if re.search(rf"\b{re.escape(part)}\b", line)]
    return hits
