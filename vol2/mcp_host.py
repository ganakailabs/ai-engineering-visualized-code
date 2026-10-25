"""Chapter 12: the host. One MCP client per server, discovery, namespacing, shortlist.

MM-106 Host, Client, Server: the host (our harness) starts one client per server
       (1:1, per the MCP architecture), keeps identity and consent, and is the only
       part that sees every server's tools.
MM-107 Tool Discovery and Selection: tools are read at run time with tools/list and
       renamed server.tool by the HOST (the spec: names are unique only within one
       server; serverInfo.name is not guaranteed unique). The shortlist keeps the
       namespaces this step may use, THEN ranks their descriptions with Vol 1's hybrid
       search (ch13). Namespace before you rank.
"""
import json
import sys
import itertools
from contextlib import AsyncExitStack
from pathlib import Path

import _root  # noqa: F401  (Vol 1 ch13.py)

from ch13 import hybrid
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters

HERE = Path(__file__).resolve().parent
SERVERS = {"orders": "orders", "courier": "courier"}   # namespace -> mcp_servers arg
STEP_NAMESPACES = {"tracking": ["orders", "courier"],  # which servers a step may use
                   "refund": ["orders"]}
HOST_FILLS = {"customer_id", "operation_id", "idempotency_key"}  # never the model's
TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool,
         "array": list, "object": dict}


def params(arg, env=None):
    return StdioServerParameters(command=sys.executable,
                                 args=[str(HERE / "mcp_servers.py"), arg],
                                 cwd=str(HERE), env=env)


class Host:
    def __init__(self, servers=None, env=None, namespaced=True):
        self.servers = dict(SERVERS if servers is None else servers)
        self.env, self.clients, self.tools, self.info = env, {}, {}, {}
        self.namespaced, self.owner = namespaced, {}   # tool key -> server namespace

    async def __aenter__(self):
        self.stack = AsyncExitStack()
        await self.stack.__aenter__()
        for ns, arg in self.servers.items():
            c = await self.stack.enter_async_context(Client(params(arg, self.env)))
            self.clients[ns] = c
            listed = await c.list_tools()
            self.info[ns] = {"protocol": c.protocol_version, "tools": len(listed.tools)}
            for t in listed.tools:                 # the HOST namespaces: ns.tool
                key = f"{ns}.{t.name}" if self.namespaced else t.name  # BREAK: bare
                self.tools[key], self.owner[key] = t, ns     # a later server overwrites
        return self

    async def __aexit__(self, *exc):
        return await self.stack.__aexit__(*exc)

    def shortlist(self, step, query, k=2, namespace_first=True):
        allowed = (STEP_NAMESPACES[step] if namespace_first
                   else list(self.clients))
        docs = {n: f"{t.name.replace('_', ' ')}. {t.description}"
                for n, t in self.tools.items() if self.owner[n] in allowed}
        return hybrid(query, docs=docs, k=k)

    def card(self, name):
        """What the model sees: name, description, and the arguments it may fill."""
        t = self.tools[name]
        args = [a for a in t.input_schema.get("properties", {}) if a not in HOST_FILLS]
        return {"name": name, "description": t.description, "arguments": args}

    def refuse(self, name, arguments):
        """Checked by the host before any request: an explicit error, not a crash.
        A shortlist is a selection aid; this check, and the server's own
        authorization, are what enforce."""
        if name not in self.tools:
            return f"unknown tool {name!r}"
        props = self.tools[name].input_schema.get("properties", {})
        for k, v in (arguments or {}).items():
            want = props.get(k, {}).get("type")
            if k not in props:
                return f"unknown argument {k!r} for {name}"
            if want and not isinstance(v, TYPES.get(want, object)):
                return f"argument {k!r} must be {want}, got {type(v).__name__}"
        return None

    async def call(self, name, arguments):
        why = self.refuse(name, arguments)
        if why:
            return {"is_error": True, "text": f"refused: {why}", "data": None}
        ns, tool = self.owner[name], self.tools[name].name
        r = await self.clients[ns].call_tool(tool, arguments)
        text = r.content[0].text if r.content else ""
        try:
            data = json.loads(text)
        except ValueError:
            data = None
        return {"is_error": bool(r.is_error), "text": text, "data": data}


_ops = itertools.count(1)


def new_operation():
    """Made ONCE per operation by the host; travels in the arguments (FIX).
    Counters keep the book's trace repeatable; production would use random UUIDs."""
    n = next(_ops)
    return {"operation_id": f"op-{n:03d}", "idempotency_key": f"key-{n:03d}"}


async def refund_with_reissue(host, args, fix=True, tries=3):
    """A dropped reply means re-issue as a NEW request (new JSON-RPC id, per the
    2026-07-28 spec). With fix=True the op id and key are the same on every try;
    with fix=False (the BREAK) each try mints a fresh key, so the store sees two
    different refunds."""
    op = new_operation()
    attempts = []
    for _ in range(tries):
        if not fix and attempts:
            op = new_operation()
        r = await host.call("orders.issue_refund", dict(args, **op))
        attempts.append(dict(r, **op))
        if not r["is_error"]:
            break
        if "TIMEOUT" not in r["text"]:
            break
    return attempts


def dumps(x):
    return json.dumps(x, separators=(",", ":"))
