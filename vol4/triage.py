"""Chapter 12: a small triage student, a clean dataset, and two gates (MM-134, MM-135).

The tickets are SIMULATED from templates (seeded, so every run is the same). The true
type of each ticket stands in for a human label. The "teacher" stands in for the large
model's triage labels: it is right most of the time, but usually files an item that
arrived damaged (a refund) under warranty. Real teacher labels come from a recorded
model; runs/evidence/ has one local-model run on the held-out split. The student is a multinomial naive Bayes classifier in plain
Python, shown in full in the chapter.
"""
import math
import random
import re
from collections import Counter, defaultdict

TYPES = ["delivery", "refund", "warranty", "faq"]
TEMPLATES = {
    "delivery": ["where is my order #{o}", "order #{o} has not arrived yet",
                 "tracking for #{o} has not moved in {d} days",
                 "when will my {i} be delivered", "courier says #{o} delivered but nothing here"],
    "refund": ["i want my money back for the {i}", "can i return the {i} from order #{o}",
               "my {i} arrived cracked, order #{o}",
               "the {i} arrived broken, i want it sorted",
               "refund for #{o} please i changed my mind"],
    "warranty": ["my {i} stopped working after {d} months", "the {i} broke after {d} months of use",
                 "is the {i} still under warranty", "{i} will not switch on any more, bought {d} months ago",
                 "repair or replace my {i} under warranty"],
    "faq": ["do you ship to {c}", "what are your opening hours",
            "how long does delivery take to {c}", "do you have a store in {c}",
            "can i change my email address"],
}
FILL = dict(o=[str(n) for n in range(1200, 6400, 37)],
            i=["lamp", "mug set", "headphones", "jacket", "kettle", "chair",
               "desk", "rug", "blender", "backpack", "speaker", "monitor"],
            d=["2", "3", "4", "5", "6", "8", "9", "11"],
            c=["pune", "delhi", "goa", "berlin", "leeds", "chennai", "lyon"])
OPEN = ["", "hi, ", "hello, ", "urgent: ", "please help, ", "hey team, "]
CLOSE = ["", " thanks", " asap", " regards", " thank you", " cheers"]
CRITICAL = {("refund", "faq"), ("warranty", "faq")}   # a money question sent to FAQ


def make_tickets(n=1200, dup_rate=0.1, seed=12):
    rnd = random.Random(seed)
    out = []
    for k in range(n):
        if out and rnd.random() < dup_rate:              # a customer resends
            prev = rnd.choice(out)
            out.append(dict(prev, id=f"T{k:04d}"))
            continue
        t = rnd.choice(TYPES)
        tpl = rnd.choice(TEMPLATES[t])
        body = re.sub(r"{(\w)}", lambda m: rnd.choice(FILL[m.group(1)]), tpl)
        text = rnd.choice(OPEN) + body + rnd.choice(CLOSE)
        out.append({"id": f"T{k:04d}", "text": text, "human": t,
                    "family": f"{t}/{TEMPLATES[t].index(tpl)}"})
    return out


def teacher_label(t, seed=7):
    """Simulated teacher: files damaged-on-arrival refunds as warranty 80% of the
    time, and slips on 3% of everything else."""
    rnd = random.Random(f"{seed}:{t['text']}")
    if t["human"] == "refund" and re.search(r"arrived (cracked|broken)", t["text"]) \
            and rnd.random() < 0.8:
        return "warranty"
    if rnd.random() < 0.03:
        return rnd.choice([x for x in TYPES if x != t["human"]])
    return t["human"]


def review(sample, teacher):
    """A human reviews a sample of teacher labels: (ticket, teacher, human) where they disagree."""
    return [(t, teacher[t["id"]], t["human"]) for t in sample if teacher[t["id"]] != t["human"]]


def dedup(tickets):
    """Keep the first ticket for each normalised text."""
    seen, out = set(), []
    for t in tickets:
        key = " ".join(t["text"].lower().split())
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


def split(tickets, seed=3, val=0.15, test=0.2):
    """Train / validation / test by ticket, after dedup: no text in two splits."""
    ts = sorted(tickets, key=lambda t: t["id"])
    random.Random(seed).shuffle(ts)
    a, b = int(len(ts) * (1 - val - test)), int(len(ts) * (1 - test))
    return ts[:a], ts[a:b], ts[b:]


def split_groups(tickets, key, test_groups):
    """Hold out whole groups (a customer, a thread, a week, a template family) when
    exact dedup leaves related tickets on both sides. Returns (train, test)."""
    return ([t for t in tickets if key(t) not in test_groups],
            [t for t in tickets if key(t) in test_groups])


def per_class(pred, gold):
    """{type: (right, n)} so a slice's count is visible, not only the average."""
    out = {}
    for p, g in zip(pred, gold):
        r, n = out.get(g, (0, 0))
        out[g] = (r + (p == g), n + 1)
    return out


def zero_fail_bound(n):
    """Rule of three: 0 failures in n gives a 95% upper bound of about 3/n."""
    return 3 / n


def words(text):
    return re.findall(r"[a-z]+", text.lower())


class NaiveBayes:
    """Multinomial naive Bayes: P(type) x product of P(word | type), add-one smoothed."""

    def fit(self, texts, labels):
        self.prior = Counter(labels)
        self.counts = defaultdict(Counter)
        for text, y in zip(texts, labels):
            self.counts[y].update(words(text))
        self.vocab = {w for c in self.counts.values() for w in c}
        self.total = {y: sum(c.values()) for y, c in self.counts.items()}
        self.n = len(labels)
        return self

    def score(self, text, y):
        s = math.log(self.prior[y] / self.n)
        for w in words(text):
            if w in self.vocab:
                s += math.log((self.counts[y][w] + 1) / (self.total[y] + len(self.vocab)))
        return s

    def predict(self, text):
        return max(self.prior, key=lambda y: self.score(text, y))


def accuracy(pred, gold):
    return sum(p == g for p, g in zip(pred, gold)) / len(gold)


def critical(pred, gold):
    return sum((g, p) in CRITICAL for p, g in zip(pred, gold))


def gate_try(plateau, labelled, min_labelled=500):
    """May we try? Prompting has stopped improving, and there is enough labelled data."""
    why = []
    if not plateau:
        why.append("plateau=no")
    if labelled < min_labelled:
        why.append(f"labelled={labelled}<{min_labelled}")
    return (not why), why


def gate_ship(gain, crit, policy="superior", margin=0.0, cheaper=False):
    """May we ship? This lab's policy ("superior"): a held-out gain over the current
    model, and no critical miss. Another valid policy, declared before the test is
    opened ("noninferior"): quality no worse than `margin` below the current model,
    AND cheaper or faster, AND no critical miss. Critical cases bind under both."""
    why = []
    if policy == "superior" and gain <= 0:
        why.append(f"gain={gain:+.3f}")
    if policy == "noninferior":
        if gain < -margin:
            why.append(f"gain={gain:+.3f}<-{margin}")
        if not cheaper:
            why.append("not cheaper")
    if crit:
        why.append(f"critical={crit}")
    return (not why), why
