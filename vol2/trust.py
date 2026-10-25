"""Chapter 13: tool trust. Secrets outside context, an allow-list, results as data.

MM-159 Keep Secrets Outside Context: the host holds a token per server, bound to that
       server as its audience; each server holds its own downstream key in its own
       environment. No secret is ever put in a prompt; a scan proves it.
MM-160 The Tool Allow-List: the registry pins each tool by a fingerprint of its
       definition (name, description, input schema), since MCP tools carry no version
       field of their own. Unlisted or changed tools are refused at load. Passing the
       allow-list says nothing about whether a RESULT is true or safe to obey: results
       are wrapped as data and can never add a tool or widen a step.

Our servers run over stdio, where the MCP authorization spec says credentials come from
the environment. The audience check below demonstrates the spec's HTTP rule (a server
accepts only tokens issued for it) in-process; it is not an OAuth implementation.
"""
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from mcp_host import Host, params  # noqa: F401

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "registry.json"
COURIER_KEY = "ck_demo_7Q2x9"           # a demo value for the mock courier API


def fingerprint(tool):
    """Pin a tool by what the model and host rely on: its name, words and schema."""
    body = json.dumps({"name": tool.name,
                       "description": tool.description,
                       "input": tool.input_schema}, sort_keys=True)
    return hashlib.sha256(body.encode()).hexdigest()[:12]


def load_registry(path=REGISTRY):
    return json.loads(Path(path).read_text())


def server_env(ns, base=None):
    """Each server gets only its own credentials (FIX). The orders server never sees
    the courier key; the host's prompt builder never sees either."""
    env = dict(os.environ if base is None else base)
    env.pop("COURIER_API_KEY", None)
    if ns == "courier":
        env["COURIER_API_KEY"] = COURIER_KEY
    return env


@dataclass(frozen=True)
class Token:
    audience: str                         # the one server this token was issued for
    scope: str
    value: str


def accept(server, token):
    """The audience rule: a server accepts only tokens issued for it."""
    if token is None or token.audience != server:
        aud = getattr(token, 'audience', None)
        return False, f"audience={aud} -> {server} refused"
    return True, f"audience={token.audience} -> {server} ok"


class TrustedHost(Host):
    """Chapter 12's host plus the registry check at load and a token per server."""

    def __init__(self, registry=None, env=None, **kw):
        super().__init__(env=env, **kw)
        self.registry = load_registry() if registry is None else registry
        self.refused, self.calls = [], []
        self.tokens = {ns: Token(ns, "tools", f"tok-{ns}") for ns in self.servers}

    async def __aenter__(self):
        base = self.env
        self.env = None
        from contextlib import AsyncExitStack
        from mcp.client import Client
        self.stack = AsyncExitStack()
        await self.stack.__aenter__()
        for ns, arg in self.servers.items():
            c = await self.stack.enter_async_context(
                Client(params(arg, server_env(ns, base))))
            self.clients[ns] = c
            listed = await c.list_tools()
            self.info[ns] = {"protocol": c.protocol_version, "tools": len(listed.tools),
                             "server": c.server_info.name, "version": c.server_info.version}
            pinned = self.registry.get(ns, {}).get("tools", {})
            for t in listed.tools:
                key = f"{ns}.{t.name}"
                if ns not in self.registry:
                    self.refused.append((key, "server not listed"))
                elif t.name not in pinned:
                    self.refused.append((key, "not listed"))
                elif pinned[t.name] != fingerprint(t):
                    self.refused.append((key, f"changed: pinned {pinned[t.name]}, "
                                              f"got {fingerprint(t)}"))
                else:
                    self.tools[key], self.owner[key] = t, ns
        return self

    async def call(self, name, arguments, token=None):
        ns = self.owner[name]
        ok, why = accept(ns, self.tokens[ns] if token is None else token)
        if not ok:
            return {"is_error": True, "text": f"auth {why}", "data": None, "refused": True}
        self.calls.append(name)
        return await super().call(name, arguments)


def as_data(name, result):
    """A tool result goes into the prompt as quoted data, labelled with its source."""
    body = json.dumps(result.get("data") if result.get("data") is not None
                      else result.get("text"))
    # a result cannot close its own tag: escape <, > and & (the tag marks
    # trust, it does not enforce it; the boundary checks do that)
    body = (body.replace("&", "\\u0026").replace("<", "\\u003c")
            .replace(">", "\\u003e"))
    return f"<tool_result source={name} trust=data>{body}</tool_result>"


# A promise is a sentence that tells the customer an action happened or will happen.
# Each action names the tool whose receipt would back it.
ACTIONS = {"refund": "issue_refund", "pickup": "book_pickup", "cancel": "cancel_pickup"}
PROMISE = re.compile(r"\b(you will|you'll|will be|has been|have been|we've|we have|"
                     r"is being|is on its way|issued|processed|booked|cancelled)\b", re.I)


def unbacked(reply, ran):
    """The reply check: sentences that promise an action with no receipt for it.
    reply: the text for the customer; ran: names of tool calls that really ran."""
    out = []
    for sentence in re.split(r"(?<=[.!?])\s+", reply or ""):
        for word, tool in ACTIONS.items():
            if (re.search(rf"\b{word}", sentence, re.I) and PROMISE.search(sentence)
                    and not any(n.endswith(tool) for n in ran)):
                out.append((word, sentence))
    return out


def hold(reply, promises):
    """FIX: drop the unbacked sentences before the reply leaves the host."""
    for _, sentence in promises:
        reply = reply.replace(sentence, "").strip()
    return reply


def secrets_in(texts, secrets=(COURIER_KEY,)):
    """The log scan: how many secrets appear anywhere in prompts, events or replies."""
    blob = "\n".join(texts)
    return sum(1 for s in secrets if s and s in blob)


async def pin(servers=None):
    """Review the tools, then write the registry: `python3 vol2/trust.py pin`."""
    out = {}
    async with Host(servers) as h:
        for key, t in h.tools.items():
            ns = h.owner[key]
            out.setdefault(ns, {"tools": {}})["tools"][t.name] = fingerprint(t)
    return out


if __name__ == "__main__":
    import asyncio
    import sys
    if sys.argv[1:] == ["pin"]:
        REGISTRY.write_text(json.dumps(asyncio.run(pin()), indent=2) + "\n")
        print(f"wrote {REGISTRY.name}")
