"""Chapter 9: Choosing a Model.

The three "models" are scripted characters in stub_model.py, and every price and speed
below is a TOY number chosen for the demo. Put your provider's current rates and your
own measured latencies in TOY_MENU before you trust any result.
"""
from stub_model import call_model
from store import fetch_order
from ch02 import order_facts
from ch07 import GROUNDED, citation_gate
from ch08 import GOLDEN, passes

# MM-023: the menu. Toy cost units per 1,000 tokens; toy seconds per call and per token.
TOY_MENU = {
    "stub-small":     {"in": 1, "out": 4,  "start_s": 0.3, "per_token_s": 0.01},
    "stub-large":     {"in": 5, "out": 20, "start_s": 0.6, "per_token_s": 0.02},
    "stub-reasoning": {"in": 5, "out": 20, "start_s": 0.6, "per_token_s": 0.02},
}
BAR = 0.90  # the pass rate to beat: the current assistant's score in Chapter 8


def assistant(ticket, oid, model):
    system = GROUNDED + (order_facts(oid, fetch_order(oid)) if oid else "")
    r = call_model([{"role": "system", "content": system},
                    {"role": "user", "content": ticket}], model=model)
    return citation_gate(r["text"]), r["usage"]


# MM-024 and MM-025: same golden set, same rubric, every model on the shortlist
def bake_off(models=TOY_MENU, golden=GOLDEN):
    rows = {}
    for name, p in models.items():
        passed, cost, seconds = 0, 0.0, 0.0
        for ticket, oid, expected in golden:
            reply, u = assistant(ticket, oid, name)
            passed += passes(reply, expected)
            cost += (u["input_tokens"] * p["in"] + u["output_tokens"] * p["out"]) / 1000
            seconds += p["start_s"] + u["output_tokens"] * p["per_token_s"]
        rows[name] = {"pass_rate": passed / len(golden),
                      "cost_per_resolved": cost / passed if passed else float("inf"),
                      "avg_seconds": seconds / len(golden)}
    return rows


def pick(rows, bar=BAR):
    ok = {m: r for m, r in rows.items() if r["pass_rate"] >= bar}
    return min(ok, key=lambda m: ok[m]["cost_per_resolved"]) if ok else None


if __name__ == "__main__":
    rows = bake_off()
    for m, r in rows.items():
        print(f"{m:15} pass {r['pass_rate']:.0%}  cost/resolved {r['cost_per_resolved']:.2f} toy units"
              f"  avg {r['avg_seconds']:.2f} toy s")
    print("pick:", pick(rows))
