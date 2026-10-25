"""Chapter 12: MCP, hosts, clients, servers and discovery.

    python3 v2/ch12.py                          # stub model (the book's trace)
    AIEV_MODEL=ollama:llama3.2 python3 v2/ch12.py

1. The message shapes (stdlib toy, mcp_toy.py): what a 2026-07-28 request carries.
2. Discover: the host starts one client per server (official Python SDK, mcp 2.3.0),
   reads each server's tools at run time and namespaces them server.tool.
3. Shortlist and pick: namespace first, then rank by description (Vol 1 hybrid search);
   the model picks calls from the shortlist only; the host fills the customer id.
4. Re-issued, refunded twice (BREAK) vs same op id and key (FIX), on a scripted lost
   reply. Request ids are the real JSON-RPC ids the server saw.
5. Interop: the official TypeScript client (2.4.0), which we did not write, calls our
   orders server. Skipped, with a reason, when node or the package is missing.
"""
import asyncio
import os

import llm
import mcp_toy
from events import Trace
from mcp_agent import interop, pick_and_call
from mcp_host import Host, dumps, refund_with_reissue
from world import World


async def main():
    trace = Trace(World(), "T-1201", "asha", model=llm.name(), echo=False)
    print(f"model={llm.name()}")
    print("-- 1. message shapes (stdlib toy) --")
    for m in mcp_toy.shapes()[:2]:
        print(" ", dumps(m))

    print("-- 2. discover --")
    async with Host() as host:
        versions = {i["protocol"] for i in host.info.values()}
        print(f"discover servers={len(host.info)} tools={len(host.tools)} "
              f"protocol={','.join(sorted(versions))}")
        for ns, i in host.info.items():
            names = [n for n in host.tools if n.startswith(ns + ".")]
            print(f"  {ns}: {', '.join(names)}")
        print("-- 3. shortlist and pick --")
        short, results = await pick_and_call(host, trace)
        print(f"shortlist [{', '.join(short)}]")
        for r in results:
            if r.get("refused"):
                print(f"  refused {r['tool']!r} ({r['why']})")
            else:
                print(f"  call {r['tool']} {dumps(r['args'])} -> "
                      f"{'error' if r['is_error'] else dumps(r['data'])}")

    print("-- 4. a dropped reply, re-issued --")
    env = dict(os.environ, AIEV_FAULTS="refund:LOST_REPLY")
    args = {"order_id": "2001", "amount": 950, "customer_id": "asha"}
    for fix in (False, True):
        async with Host(env=env) as host:
            tries = await refund_with_reissue(host, args, fix=fix)
        label = "FIX  " if fix else "BREAK"
        for n, t in enumerate(tries, 1):
            rid = (t["data"] or {}).get("request_id") or t["text"].split("request_id=")[-1]
            print(f"  {label} try {n}: request_id={rid} op_id={t['operation_id']} "
                  f"key={t['idempotency_key']} -> "
                  f"{'lost reply' if t['is_error'] else 'ok'}")
        last = tries[-1]["data"] or {}
        print(f"  {label} payments for #2001: {last.get('payments')}"
              f"{' (replayed)' if last.get('replayed') else ''}")
        trace.emit("reissue", actor="harness", text=f"fix={fix} payments={last.get('payments')}")
    same = len({(t['operation_id'], t['idempotency_key']) for t in tries}) == 1
    print(f"reissue request_id=new op_id={'same' if same else 'new'} "
          f"key={'same' if same else 'new'}")

    print("-- 5. interop --")
    ok, out = interop()
    if ok is None:
        print(f"interop {out}")
    else:
        print(f"interop client=@modelcontextprotocol/client@2.4.0 "
              f"protocol={out.get('version') if isinstance(out, dict) else '?'} "
              f"list_tools {'ok' if ok else 'FAILED'} call {'ok' if ok else 'FAILED'}")
    trace.emit("interop", actor="harness", text=f"ok={ok}")
    return results


if __name__ == "__main__":
    asyncio.run(main())
