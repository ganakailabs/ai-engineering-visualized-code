"""Chapter 9: cost engineering, tokens and caching.

MM-127 Cost per Resolved Ticket: everything a ticket type spends (model calls, retrieval,
       tools, retries, human time on escalations) divided by the tickets it resolved.
MM-128 The Cache Layers: two application caches the service owns (exact, semantic) with
       an entity check on every hit, structured cacheability (an allowlist of routes,
       context and sources), tenant and permission scope in the key, an access recheck
       on every hit, and a flush when the policy or index version changes. A hit skips
       generation, not the checks. The provider's prompt cache is separate.
MM-176 Stable First, Changing Last: a provider can reuse only an identical prefix, so
       stable blocks go first and per-request values last.

Teaching choices, said out loud:
- prices are MADE-UP units ("u"), as in Vol 1 Ch 4: check your provider's pricing page;
- the ticket mix is seeded and simulated; tokens use Vol 1's rough counter;
- provider cache numbers come only from a provider's usage report, so the stub has none.
"""
import random
import re

import _root  # noqa: F401

from store import HANDBOOK, POLICY_VERSION, ORDERS
from stub_model import rough_token_count

# ---------------- MM-127 cost per resolved ticket ----------------

# Made-up units, only to show the arithmetic. Never hard-code prices from a book.
UNIT = {"in_per_1k": 1.0, "out_per_1k": 4.0, "retrieve": 0.2, "tool": 0.1,
        "human_min": 10.0}
TYPES = ["delivery", "refund", "warranty"]


def tickets(release, n_per_type=100, seed=9):
    """A simulated week per release. 'small' swaps to a cheaper model that needs more
    retries and escalates more refund and warranty tickets (the simulator's choice)."""
    rng = random.Random(seed)
    model = {"big": {"price": 1.0, "retry": 0.05, "esc": {"delivery": 0.02, "refund": 0.10,
                                                         "warranty": 0.08}},
             "small": {"price": 0.4, "retry": 0.20, "esc": {"delivery": 0.03, "refund": 0.30,
                                                           "warranty": 0.25}}}[release]
    out = []
    for kind in TYPES:
        for i in range(n_per_type):
            calls = 1 + sum(rng.random() < model["retry"] for _ in range(2))
            esc = rng.random() < model["esc"][kind]
            out.append({"id": f"T-{kind[:3]}-{i:03d}", "type": kind, "calls": calls, "price": model["price"],
                        "in_tok": 3000, "out_tok": 250, "retrieve": 1 if kind != "delivery"
                        else 0, "tools": 1, "escalated": esc,
                        "human_min": 8 if esc else 0,
                        # a human resolves an escalation; the rest resolve 97% of the time
                        "resolved": True if esc else rng.random() < 0.97})
    return out


def ticket_cost(t):
    """One ticket's receipt, in made-up units."""
    model = t["calls"] * t["price"] * (t["in_tok"] / 1000 * UNIT["in_per_1k"]
                                       + t["out_tok"] / 1000 * UNIT["out_per_1k"])
    first = t["price"] * (t["in_tok"] / 1000 * UNIT["in_per_1k"]
                          + t["out_tok"] / 1000 * UNIT["out_per_1k"])
    return {"model": first, "retries": model - first,
            "retrieve": t["retrieve"] * UNIT["retrieve"], "tools": t["tools"] * UNIT["tool"],
            "human": t["human_min"] * UNIT["human_min"]}


def per_call(ts):
    """What a dashboard of model calls shows: model spend divided by calls."""
    spend = sum(ticket_cost(t)["model"] + ticket_cost(t)["retries"] for t in ts)
    return spend / sum(t["calls"] for t in ts)


def per_resolved(ts):
    """Everything spent, divided by tickets actually resolved."""
    spend = sum(sum(ticket_cost(t).values()) for t in ts)
    return spend / max(1, sum(t["resolved"] for t in ts))


# ---------------- MM-128 application caches ----------------

ORDER_ID = re.compile(r"#?(\d{4})\b")
PERSONAL = {"refund", "return", "replace", "cancel"}   # the old text rule's keywords

# Structured cacheability: an allowlist, decided from what the reply was BUILT from,
# not from the words of the question.
CACHEABLE_ROUTES = {"faq"}            # routes whose answers are general by design
PUBLIC_SOURCES = {"handbook"}         # provenance a cached answer may rest on
GENERAL = {"tenant": "a", "route": "faq", "context": False, "sources": ["handbook"],
           "perm_v": 1, "can_read": {"handbook"}}


def text_rule(q):
    """The old predicate: a decision keyword AND an order id in the question text.
    'Refund the order we discussed' has its order in session context, so it passes."""
    return bool(words(q) & PERSONAL and ORDER_ID.search(q))


def cacheable(ctx):
    """(ok, reason): allowlisted route, no session or order context used, and every
    source public. A personal answer fails here even when its text names no order."""
    if ctx["route"] not in CACHEABLE_ROUTES:
        return False, f"route {ctx['route']} not allowlisted"
    if ctx.get("context"):
        return False, "used session/order context"
    if set(ctx.get("sources", ())) - PUBLIC_SOURCES:
        return False, "non-public source"
    return True, "general answer"


def norm(q):
    return " ".join(re.findall(r"\w+", q.lower()))


def words(q):
    return set(re.findall(r"[a-z]+", q.lower()))


class AppCache:
    """Exact and semantic caches the service owns. A hit skips generation, not the
    checks: authorization and validity still run on every hit.
    Keys carry the policy and index versions (a version change empties them) and the
    scope: tenant and permissions version. entity: check order ids on a semantic hit.
    structured: store only answers cacheable() allows. Both off is the naive cache."""

    def __init__(self, policy_v, index_v, entity=True, structured=True, threshold=0.6):
        self.versions, self.threshold = (policy_v, index_v), threshold
        self.entity, self.structured = entity, structured
        self.exact, self.semantic = {}, []

    @staticmethod
    def scope(ctx):
        return (ctx["tenant"], ctx["perm_v"])

    def put(self, q, reply, ctx=None):
        ctx = ctx or GENERAL
        if self.structured:
            ok, why = cacheable(ctx)
            if not ok:
                return f"not cached reason={why}"
        entry = (reply, tuple(ctx.get("sources", ())))
        self.exact[(self.versions, self.scope(ctx), norm(q))] = entry
        self.semantic.append((self.versions, self.scope(ctx), q, entry))
        return "cached"

    def _recheck(self, ctx, entry):
        """On every hit: may THIS caller read what the answer was built from, now?"""
        reply, sources = entry
        return reply if set(sources) <= set(ctx.get("can_read", ())) else None

    def get(self, q, ctx=None):
        ctx = ctx or GENERAL
        hit = self.exact.get((self.versions, self.scope(ctx), norm(q)))
        if hit:
            reply = self._recheck(ctx, hit)
            return (reply, "exact hit") if reply else (None, "hit refused reason=access")
        best, score = None, 0.0
        for v, sc, cq, entry in self.semantic:
            if v != self.versions or sc != self.scope(ctx):
                continue
            s = len(words(q) & words(cq)) / len(words(q) | words(cq))
            if s > score:
                best, score = (cq, entry), s
        if not best:
            return None, "miss reason=empty"
        if score < self.threshold:
            return None, f"semantic miss reason=similarity {score:.2f}"
        if self.entity and set(ORDER_ID.findall(q)) != set(ORDER_ID.findall(best[0])):
            return None, "semantic miss reason=order id differs"
        reply = self._recheck(ctx, best[1])
        if not reply:
            return None, "hit refused reason=access"
        return reply, f"semantic hit similarity={score:.2f}"

    def set_versions(self, policy_v, index_v):
        """A new policy or index version: entries under the old versions are dropped."""
        before = len(self.exact)
        self.versions = (policy_v, index_v)
        self.exact = {k: v for k, v in self.exact.items() if k[0] == self.versions}
        self.semantic = [e for e in self.semantic if e[0] == self.versions]
        return before - len(self.exact)


# ---------------- MM-176 stable first, changing last ----------------

SYSTEM = ("You are the Northwind Goods support assistant. Answer only from the policy, "
          "the handbook and the order record. Cite clause ids.")
TOOLS = "Tools: lookup_order(order_id), search_handbook(query), escalate(reason)."


def policy_block(version=POLICY_VERSION):
    return f"POLICY {version}: " + " ".join(f"[{c}] {t}" for c, t in HANDBOOK.items())


def blocks(ticket, policy_version=POLICY_VERSION):
    """Every block of the prompt, tagged stable or changing."""
    o = ORDERS[ticket["order_id"]]
    return {
        "header": ("changing", f"Ticket {ticket['ticket_id']} received {ticket['at']}."),
        "system": ("stable", SYSTEM),
        "tools": ("stable", TOOLS),
        "policy": ("stable", policy_block(policy_version)),
        "order": ("changing", f"Order #{ticket['order_id']}: {o['item']}, INR {o['amount']}."),
        "ticket": ("changing", ticket["text"]),
    }


AS_SHIPPED = ["header", "system", "tools", "policy", "order", "ticket"]
STABLE_FIRST = ["system", "tools", "policy", "order", "header", "ticket"]


def prompt(ticket, layout, policy_version=POLICY_VERSION):
    b = blocks(ticket, policy_version)
    return "\n".join(b[name][1] for name in layout)


def shared_prefix_tokens(a, b):
    """Tokens two prompts share from the very start (Vol 1's rough counter)."""
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    return rough_token_count(a[:n].rsplit("\n", 1)[0] if n < len(a) else a)


def stable_tokens(ticket):
    b = blocks(ticket)
    return rough_token_count("\n".join(b[k][1] for k in ("system", "tools", "policy")))


def prefix_stable(t1, t2, layout):
    """The prefix-stability test: two different tickets must share the whole stable block."""
    return shared_prefix_tokens(prompt(t1, layout), prompt(t2, layout)) >= stable_tokens(t1)
