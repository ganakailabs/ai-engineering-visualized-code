// Chapter 12: a stranger's client (the official TypeScript SDK, pinned 2.4.0) calls
// our orders server over stdio. It pins revision 2026-07-28: in 2.4.0, as in 2.3.1, the default
// negotiation mode is "legacy", which settles on 2025-11-25 instead.
//   node v2/interop/stranger.mjs python3 v2/mcp_servers.py orders
import { Client } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";

const [command, ...args] = process.argv.slice(2);
const transport = new StdioClientTransport({ command, args });
const client = new Client({ name: "stranger", version: "1.0.0" },
  { versionNegotiation: { mode: { pin: "2026-07-28" } } });
await client.connect(transport);
const tools = (await client.listTools()).tools.map((t) => t.name);
const r = await client.callTool({ name: "look_up_shipment",
  arguments: { order_id: "6001", customer_id: "asha" } });
console.log(JSON.stringify({ version: client.getNegotiatedProtocolVersion(), tools,
  is_error: Boolean(r.isError), text: r.content?.[0]?.text ?? "" }));
await client.close();
