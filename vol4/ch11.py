"""Chapter 11: Inference and Serving, Managed vs Self-Hosted.

Run from the repo root:  python3 vol4/ch11.py
Part 1 fills the rent-or-own worksheet (example inputs, simulated units) (MM-131).
Part 2 estimates KV memory with its assumption printed, and sets it against total GPU
memory (MM-132). Part 3 is optional: with AIEV_MODEL=ollama:<model> it times your own
model's prefill and decode from Ollama's response fields; otherwise it says so.
"""
import _root  # noqa: F401

import json
import os
import urllib.request

import serving as S

PROMPT = ("You are Northwind Goods' support assistant. A customer writes: my mug set "
          "(order #2001) arrived cracked. What happens next? Answer in two sentences.")


def ollama_timings(model):
    url = os.environ.get("AIEV_OLLAMA_URL", "http://localhost:11434") + "/api/generate"
    body = json.dumps({"model": model, "prompt": PROMPT, "stream": False,
                       "options": {"temperature": 0, "num_predict": 120}}).encode()
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


if __name__ == "__main__":
    w = S.WORKSHEET
    print("== Part 1: rent or own (MM-131), example inputs ==")
    print(f"{'tickets/mo':>10} {'api':>9} {'self naive':>10} "
          f"{'self full':>10} gpus")
    for n in (10_000, 50_000, 100_000, 1_000_000):
        print(f"{n:>10,} {S.api_cost(n):>9,.0f} {S.self_host_naive(n):>10,.0f} "
              f"{S.self_host_full(n):>10,.0f} {S.gpus_needed(n):>4}")
    print(f"break-even (one GPU, fully costed): {S.break_even():,.0f} tickets/mo")
    print("  naive leaves out idle hours, ops and on-call (simulated units)")

    print("== Part 2: KV cache at scale (MM-132), example model shape ==")
    m = S.EXAMPLE_MODEL
    per_tok = S.kv_bytes_per_token()
    print(f"kv assume=full_attention layers={m['layers']} kv_heads={m['kv_heads']} "
          f"head_dim={m['head_dim']}")
    print(f"  -> bytes={per_tok:,} per token ({per_tok / 1024:.0f} KiB)")
    for ctx, batch in ((8192, 1), (8192, 16), (16384, 16)):
        print(f"kv context={ctx:>5} batch={batch:>2} -> "
              f"{S.kv_bytes(ctx, batch) / S.GIB:5.1f} GiB")
    hyb = S.kv_bytes(8192, 16, sliding=(16, 128))
    print(f"kv assume=half layers sliding window=128, 8192x16 -> {hyb / S.GIB:.1f} GiB")
    print("gpu memory example=80 GiB = weights + kv + runtime overhead")
    for bits in (16, 8, 4):
        print(f"  weights {bits:>2}-bit={S.weight_bytes(bits=bits) / S.GIB:4.1f} GiB "
              f"-> max seqs at 8192: {S.max_sequences(80, 8192, bits=bits)}")
    print("  (idealized ceilings: no runtime memory, every slot full)")
    ceil = S.max_sequences(80, 8192, reserve=0.10)
    print(f"  16-bit, 10% kept for the runtime (example) -> max seqs at 8192: {ceil}")
    print(f"  plan with 25% spare for peaks and failover (example) -> "
          f"{S.planned_sequences(ceil)}")
    print("  runtime memory on your server: unmeasured (read it from your runtime)")

    print("== Part 3: your own prefill and decode (optional) ==")
    from ollama_model import selected
    model = selected()
    if not model:
        print("ollama: off (set AIEV_MODEL=ollama:<model> to time yours)")
        print("prefill tok/s and decode tok/s: unmeasured (no model set)")
    else:
        r = ollama_timings(model)
        pre = r["prompt_eval_count"] / (r["prompt_eval_duration"] / 1e9)
        dec = r["eval_count"] / (r["eval_duration"] / 1e9)
        print(f"model={model} prompt_tokens={r['prompt_eval_count']} "
              f"reply_tokens={r['eval_count']}")
        print(f"prefill tok/s={pre:.0f} decode tok/s={dec:.1f}")
        print("record these with your model and hardware; they are yours")
