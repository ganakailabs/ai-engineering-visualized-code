"""Structured events, rendered as the Vol 1 trace (series contract section 4).

Code records an event; the readable line is rendered from it. Tests read the events
and the world, never the printed text.
"""
KINDS = {"harness", "route", "propose", "check", "act", "observe", "plan",
         "reply", "escalate", "stop", "state", "held",
         "verify", "checkpoint", "resume", "ledger", "reconcile", "approve",
         "handoff", "memory", "decide",
         "assemble", "compact", "retrieve",
         "judge", "requery", "decompose",
         "discover", "shortlist", "reissue", "interop",
         "registry", "auth", "crash"}  # Ch 4-13 (series contract section 4)


class Trace:
    def __init__(self, world, ticket_id, customer_id, model="stub", run_id="r-1",
                 echo=True):
        self.world, self.events, self.echo = world, [], echo
        self.base = {"run_id": run_id, "ticket_id": ticket_id,
                     "customer_id": customer_id, "model": model}

    def emit(self, kind, text, actor="code", **payload):
        assert kind in KINDS, f"unknown event kind {kind}"
        event = dict(self.base, event_id=f"e-{len(self.events) + 1:06d}",
                     ts_sim=self.world.now(), actor=actor, kind=kind,
                     text=text, payload=payload)
        self.events.append(event)
        if self.echo:
            print(f"  {kind:<9}{' ' if len(kind) > 8 else ''}{text}")
        return event

    def of(self, kind):
        return [e for e in self.events if e["kind"] == kind]
