"""Chapter 12: MCP message shapes at revision 2026-07-28, printed with the stdlib only.

A teaching toy: it builds the JSON-RPC messages a client sends, so you can read them.
It does not speak to anything; the real exchange in ch12.py runs on the official SDK.
"""
import json

PROTOCOL = "2026-07-28"


def meta(client="northwind-host"):
    """Every request carries this (no initialize handshake at this revision)."""
    return {"io.modelcontextprotocol/protocolVersion": PROTOCOL,
            "io.modelcontextprotocol/clientCapabilities": {},
            "io.modelcontextprotocol/clientInfo": {"name": client, "version": "2.12.0"}}


def request(rid, method, params=None):
    return {"jsonrpc": "2.0", "id": rid, "method": method,
            "params": dict(params or {}, _meta=meta())}


def shapes(op_id="op-7f3a", key="key-91c2"):
    args = {"order_id": "2001", "amount": 950, "customer_id": "asha",
            "operation_id": op_id, "idempotency_key": key}
    return [request(1, "server/discover"),
            request(2, "tools/list"),
            request(3, "tools/call", {"name": "issue_refund", "arguments": args}),
            request(4, "tools/call", {"name": "issue_refund", "arguments": args})]


if __name__ == "__main__":
    for m in shapes():
        print(json.dumps(m, separators=(",", ":")))
