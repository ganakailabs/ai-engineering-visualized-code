"""Chapter 12: the agent step over MCP tools, and the interop check.

pick_and_call: the host shortlists (namespace first, then rank), the model picks calls
from the shortlist only, the host refuses anything else and fills the customer id.
interop: the official TypeScript client (2.4.0), which we did not write, calls a server.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import llm

HERE = Path(__file__).resolve().parent
TICKET = "Where is my parcel for order 6001? Can the courier still redirect it?"
STEP_QUERY = "where is the parcel now, and can it still be redirected"
SYSTEM = ("You are Northwind's support agent. Choose the tool calls for this ticket "
          "from the tool list ONLY, using the exact tool names. Reply with JSON: "
          '{"calls": [{"tool": "<name>", "arguments": {...}}]}')


def stub(user):
    return {"calls": [{"tool": "orders.look_up_shipment", "arguments": {"order_id": "6001"}},
                      {"tool": "courier.ask_carrier", "arguments": {"order_id": "6001"}}]}


async def pick_and_call(host, trace, customer="asha", query=STEP_QUERY):
    short = host.shortlist("tracking", query)
    trace.emit("shortlist", actor="harness", text=f"shortlist [{', '.join(short)}]", tools=short)
    cards = [host.card(n) for n in short]
    user = f"Ticket: {TICKET}\nTools: {json.dumps(cards)}"
    reply, raw = llm.ask_json(SYSTEM, user, stub)
    print(f"  model raw: {raw[:300]}")
    trace.emit("propose", actor="model", text=f"raw={raw[:160]}")
    results = []
    calls = (reply or {}).get("calls") if isinstance(reply, dict) else None
    if not isinstance(calls, list) or not calls:
        trace.emit("escalate", actor="harness", text="no usable tool calls -> handoff")
        return short, results
    for c in calls[:3]:
        name = c.get("tool") if isinstance(c, dict) else None
        if name not in short:                       # the host enforces the shortlist
            trace.emit("check", actor="harness", text=f"refused {name!r}: not on the shortlist")
            results.append({"tool": name, "refused": True, "why": "not on the shortlist"})
            continue
        given = c.get("arguments") or {}
        if not isinstance(given, dict):             # a real model sent a list here
            trace.emit("check", actor="harness", text=f"refused {name!r}: arguments not an object")
            results.append({"tool": name, "refused": True, "why": "arguments not an object"})
            continue
        args = {k: v for k, v in given.items()
                if k in host.card(name)["arguments"]}
        if "customer_id" in host.tools[name].input_schema.get("properties", {}):
            args["customer_id"] = customer          # from the session, not the model
        r = await host.call(name, args)
        trace.emit("observe", actor="tool", text=f"{name} -> {r['text'].replace(chr(10), '')[:80]}")
        results.append({"tool": name, "args": args, **r})
    return short, results


def interop(server_arg="orders"):
    script = HERE / "interop" / "stranger.mjs"
    if not shutil.which("node"):
        return None, "skipped: node not found"
    if not (HERE / "interop" / "node_modules" / "@modelcontextprotocol" / "client").exists():
        return None, "skipped: run `npm ci` in v2/interop first"
    p = subprocess.run(["node", str(script), sys.executable,
                        str(HERE / "mcp_servers.py"), server_arg],
                       capture_output=True, text=True, timeout=60, cwd=HERE)
    if p.returncode != 0:
        return False, f"failed: {p.stderr.strip()[-200:]}"
    out = json.loads(p.stdout.strip().splitlines()[-1])
    ok = out["version"] == "2026-07-28" and "look_up_shipment" in out["tools"] \
        and not out["is_error"]
    return ok, out
