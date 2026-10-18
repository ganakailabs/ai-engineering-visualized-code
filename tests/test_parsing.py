"""Malformed model replies never crash: they are read tolerantly or become a
safe escalate. No network. Run: python3 tests/test_parsing.py"""
import contextlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import formats  # noqa: E402
import ollama_model as om  # noqa: E402
from parse import decision_reply, first_json, label  # noqa: E402
from ch07 import citation_gate  # noqa: E402
from ch08 import decision_of  # noqa: E402
from ch18 import TRACKS, route  # noqa: E402
from ch19 import run_agent  # noqa: E402
from ch20 import run as run_plan  # noqa: E402
from ch24 import handle_ticket  # noqa: E402

GARBAGE = "lorem ipsum ??? 42"


def model_saying(text):
    return lambda messages, **kw: {"text": text, "usage": {
        "input_tokens": 10, "output_tokens": 5}}


quiet = contextlib.redirect_stderr(io.StringIO())   # [parse] warnings
with quiet:
    # labels: <approve>, case, bold, leading text
    assert decision_reply("<approve> Within 30 days (R1)") == "approve: Within 30 days (R1)"
    assert decision_reply("**Deny**: final sale (R3)") == "deny: final sale (R3)"
    assert decision_reply("Sure. escalate: needs a person") == "escalate: needs a person"
    assert decision_reply(GARBAGE) is None
    assert decision_reply("Sadly it can't be refunded.") is None
    assert decision_of("<deny> Final sale (R3)") == "deny"
    assert label("REFUND", TRACKS) == "refund" and label("refunds", TRACKS) is None
    # JSON: fenced, prose first, garbage
    assert first_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert first_json('Here you go: {"final": "done: ok"} hope it helps') == {"final": "done: ok"}
    assert first_json(GARBAGE) is None
    # the gate is not fooled by a wrapped label without a clause
    assert citation_gate("<approve> sure thing").startswith("escalate: held")
    # router: tolerant match, unknown -> other
    assert route("x", model=model_saying("<Warranty>"))[0] == "warranty"
    assert route("x", model=model_saying(GARBAGE))[0] == "other"
    # agent: fenced and prose+JSON moves work; garbage escalates
    fenced = '```json\n{"thought": "t", "final": "done: ok"}\n```'
    assert run_agent("x", model=model_saying(fenced))[0] == "done: ok"
    prose = 'Sure! {"thought": "t", "final": "escalate: no"}'
    assert run_agent("x", model=model_saying(prose))[0] == "escalate: no"
    assert run_agent("x", model=model_saying(GARBAGE))[0].startswith("escalate")
    # agent: a tool called with wrong args is an observation, not a crash
    bad = json.dumps({"thought": "t", "action": "change_address", "args": {"x": 1}})
    reply, trace = run_agent("x", model=model_saying(bad), max_steps=2)
    assert trace[0][3].startswith("error: change_address failed")
    # planner: garbage -> escalate; JSON-mode {"steps": [...]} accepted
    assert run_plan("swap #2001", model=model_saying(GARBAGE))[-1][0] == "escalate"
    steps = {"steps": [{"tool": "check_stock", "args": {"item": "mug set green"}}]}
    assert run_plan("swap #2001 green", model=model_saying(json.dumps(steps)))[0] \
        == ("plan", ["check_stock"])
    # the whole agent run on a garbage model: every ticket escalates, no crash
    for t in ("Refund #2001?", "Change the address for #5120 to X.",
              "Please swap my mug set #2001 for the blue one.", "Warranty on NW-500?"):
        r, _ = handle_ticket(t, log=lambda line: None, model=model_saying(GARBAGE))
        assert r.startswith("escalate"), (t, r)

# a cited answer with no label (or 'Answer:') still passes the output guardrail
from ch23 import check_out  # noqa: E402
assert check_out("Answer: NW-500 carries a 12-month warranty [S2]") is None
cited = ("NW-500 headphones carry a 12-month warranty against defects. A battery "
         "that stops charging counts as a defect. [S2]")
with contextlib.redirect_stderr(io.StringIO()):
    def rag_model(messages, **kw):
        system = messages[0]["content"].lower()
        text = "warranty" if "classify the ticket" in system else cited
        return {"text": text, "usage": {"input_tokens": 1, "output_tokens": 1}}
    r, steps = handle_ticket("My NW-500 battery stopped charging. Warranty?",
                             log=lambda line: None, model=rag_model)
assert r == "answer: " + cited and ("check", "output guardrail: ok") in steps, (r, steps)

# real-model path: the adapter adds the exact format and JSON mode
agent_msgs = [{"role": "system", "content": "You are an agent for X."},
              {"role": "user", "content": "hi"}]
body = om.build_request(agent_msgs, "m")
assert body["format"] == "json" and formats.AGENT in body["messages"][0]["content"]
router = om.build_request([{"role": "system", "content": "Classify the ticket: a"},
                           {"role": "user", "content": "hi"}], "m")
assert "format" not in router and formats.ROUTER in router["messages"][0]["content"]
print("parsing test: OK")
