"""Chapter 9: Agent Memory: Lifetime, Scope and Correction.

Run from the repo root:  python3 vol2/ch09.py
Real model (optional):  AIEV_MODEL=ollama:llama3.2 python3 vol2/ch09.py
The memories are fixture data (fictional). The writes, the correction and the expiry are scripted; then the model
writes the reply from the context memory builds, so the context is what we check.
"""
import llm
import memory
from events import Trace
from world import World

OLD, NEW = "14 Lane 5, Koregaon Park, Pune", "B-302, Baner Road, Pune"


def asha_memory(world, tr):
    """Fixture memories from Asha's earlier tickets (fictional)."""
    m = memory.Memory(world)
    rows = [("address", OLD, "persistent", "customer", "fact", "ticket-T-1873"),
            ("prefers", "replacement over refund", "persistent", "customer",
             "preference", "ticket-T-1873"),
            ("episode", "2026-08-20 mug set arrived cracked; replaced", "persistent",
             "customer", "episode", "ticket-T-1873"),
            ("episode", "2026-09-12 mug set arrived cracked; replaced", "persistent",
             "customer", "episode", "ticket-T-1950"),
            ("on_call", "is waiting on the phone", "session", "ticket", "fact",
             "ticket-T-2001-a")]
    for key, value, lifetime, scope, type_, source in rows:
        m.write("asha" if scope == "customer" else "T-2001-a", key, value, lifetime, scope, type_, source, hours=1)
        tr.emit("memory", f"write key={key} lifetime={lifetime} scope={scope} "
                f"type={type_} source={source}")
    m.write("team", "courier", "courier pickups slow this week", "persistent", "team",
            "fact", "ops-note", readers=("agent",))
    return m


def correction(propagate=True):
    print(f"--- {'FIX: correct everywhere' if propagate else 'BREAK: store only'} ---")
    world = World()
    tr = Trace(world, "T-2001-a", "asha")
    m = asha_memory(world, tr)
    r = m.recall("asha")
    tr.emit("memory", f"recall episodes={len(r['episodes'])}")
    m.correct("asha", "address", NEW, "ticket-T-2001-a", propagate=propagate)
    where = m.copies_of(OLD)
    tr.emit("memory", "correct key=address -> " + ", ".join(
        f"{copy} {'still old' if old else 'updated'}" for copy, old in where.items()))
    return world, m, tr


def lifetimes(m, tr):
    m.world.tick(90)                                 # the session ends
    tr.emit("memory", f"expire -> forgot {m.expire()} session record(s)")


SYSTEM = ("You write one short reply to a Northwind Goods customer. Use only the memory "
          "and the ticket given. Reply with ONE JSON object and nothing else: "
          '{"reply": "<two sentences at most>"}')


def stub(user):
    address = NEW if NEW in user else OLD
    return {"reply": f"Sorry it arrived cracked again. The replacement will go to {address}."}


def model_replies(m, tr):
    r = m.recall("asha")
    context = (f"Memory summary: {r['summary']}\nPast episodes: "
               + " | ".join(e["value"] for e in r["episodes"]))
    ticket = "Ticket: My mug set #2001 arrived cracked, again. Where will the new one go?"
    move, _ = llm.ask_json(SYSTEM, context + "\n" + ticket, stub, max_output_tokens=200)
    reply = (move or {}).get("reply", "escalate: no valid reply")
    tr.emit("reply", reply, actor="model")
    return context, reply


if __name__ == "__main__":
    for propagate in (False, True):
        world, m, tr = correction(propagate)
        lifetimes(m, tr)
        print(f"--- the model replies (model={llm.name()}) ---")
        model_replies(m, tr)
