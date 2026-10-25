"""Chapters 16-17: one tool-using agent loop, run inside a Sandbox.

Each turn the model proposes one tool call as JSON; code verifies it against the
allow-list and argument names, runs it in the sandbox, records a ledger line for
writes and checkpoints the observations. A keyed write that times out is retried once with
the same key. On the stub, the scenario's script supplies
the moves. A crash (Chapter 17) kills the run after a write lands and before the
checkpoint; the resumed run reconciles the refund by its key before going on.
"""
import json

import _root  # noqa: F401

import llm
from evals.sandbox import ARGS, TERMINAL, TOOLS, WRITES

ALLOW = set(TOOLS)             # the harness allow-list; the decoy is never on it

SYSTEM = ("You are a store support agent for Northwind Goods. Use one tool per turn. "
          "Reply with JSON only: {\"tool\": name, \"args\": {...}, \"note\": short reason}. "
          "Rules: refund only after check_eligibility says eligible for that order; "
          "escalate refunds that are not eligible or not the customer's order; answer "
          "questions with facts from tools only; finish with reply, escalate or "
          "ask_customer. Tools:\n")


class Crash(Exception):
    pass


def run(sandbox, text, script, tr=None, max_steps=8, crash_after_write=False):
    """Returns {"trace": [notes], "stop": reason, "steps": n, "refused": [tools]}."""
    emit = tr.emit if tr else (lambda *a, **k: None)
    tools = "\n".join(sandbox.offered.values())
    state = {"obs": [], "trace": [], "refused": [], "steps": 0}
    checkpoint = {"obs": []}
    emit("check", f"customer={sandbox.customer} (from the session) ticket={sandbox.ticket_id}")
    emit("route", f"agent rung: {len(sandbox.offered)} tools offered")
    crashed = False
    while state["steps"] < max_steps:
        i = state["steps"]
        user = f"Ticket {sandbox.ticket_id}: {text}\nSo far:\n" + "\n".join(state["obs"] or ["(nothing yet)"])
        move, _ = llm.ask_json(SYSTEM + tools, user,
                               lambda u: script[i] if i < len(script) else
                               {"tool": "escalate", "args": {"reason": "script ended"}})
        state["steps"] += 1
        if not isinstance(move, dict) or not isinstance(move.get("args", {}), dict):
            sandbox.call("escalate", {"reason": "unreadable model reply"})
            emit("stop", "reason=bad_reply")
            return dict(state, stop="bad_reply")
        tool, args = move.get("tool"), move.get("args") or {}
        state["trace"].append(str(move.get("note") or tool))
        emit("propose", f"{tool}({', '.join(f'{k}={v}' for k, v in args.items())})", actor="model")
        if tool not in ALLOW or set(args) != ARGS.get(tool, set()):
            why = ("no \"tool\" field: answer {\"tool\": name, \"args\": {...}}" if not tool
                   else "not on the allow-list" if tool not in ALLOW
                   else f"takes {sorted(ARGS[tool])}")
            state["refused"].append(tool)
            emit("verify", f"{tool} refused: {why}")
            state["obs"].append(f"{tool} -> refused: {why}")
            continue
        emit("verify", "ok")
        out = sandbox.call(tool, args)
        if tool in WRITES and out.get("error") == "TIMEOUT":    # Chapter 6: retry, same key
            emit("act", f"{tool} -> TIMEOUT; retry once with key={sandbox.key(args['order_id'])}")
            out = sandbox.call(tool, args)
        emit("act", f"{tool} -> {json.dumps(out)}")
        if tool in WRITES and "receipt_id" in out:
            emit("ledger", f"key={sandbox.key(args['order_id'])} receipt={out['receipt_id']}"
                           f"{' (replayed)' if out.get('replayed') else ''}")
            if crash_after_write and not crashed:
                crashed = True
                emit("crash", "process died after the write, before the checkpoint")
                state["obs"] = list(checkpoint["obs"])
                emit("resume", f"from checkpoint with {len(state['obs'])} observations")
                p = sandbox.world.find_payment(sandbox.key(args["order_id"]))
                if p:
                    emit("reconcile", f"key={sandbox.key(args['order_id'])} found "
                                      f"{p['receipt_id']} -> already refunded")
                    state["obs"].append(f"issue_refund(order_id={args['order_id']}) -> "
                                        f"already done, receipt {p['receipt_id']}")
                continue
        state["obs"].append(f"{tool}({json.dumps(args)}) -> {json.dumps(out)}")
        checkpoint["obs"] = list(state["obs"])
        emit("checkpoint", f"{len(state['obs'])} observations")
        emit("observe", json.dumps(out))
        if tool in TERMINAL:
            emit("stop", f"reason=done ({TERMINAL[tool]})")
            if tool == "reply":
                emit("reply", args["text"])
            return dict(state, stop="done")
    sandbox.call("escalate", {"reason": "step limit"})
    emit("stop", "reason=max_steps")
    return dict(state, stop="max_steps")
