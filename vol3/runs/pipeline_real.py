"""One real-model run of the capstone pipeline (vol3/pipeline.py).

    AIEV_MODEL=ollama:llama3.2 python3 vol3/runs/pipeline_real.py

Runs pipeline.main() unchanged and records every answer() call it makes (message,
config, action, reply, citations, escalation reasons) so the replies can be read and
graded by hand. pipeline.main() grades each ticket by code against the hand labels in
TICKETS (action, pack coverage, never-cite ids); that grade does not read the reply.
Writes vol3/runs/<date>-<model>-capstone-real.txt and -capstone-replies.json.
"""
import contextlib
import datetime
import io
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import _root  # noqa: E402,F401

import llm  # noqa: E402
import ollama_model  # noqa: E402
import pipeline as PL  # noqa: E402

REAL = ollama_model.selected()
TAG = (REAL or "stub").replace(":latest", "")
DATE = datetime.date.today().isoformat()
OUT = Path(os.environ.get("AIEV_RUNS_DIR", HERE))

METER = dict(calls=0, prompt=0, output=0)
_post = ollama_model._post


def _metered(body):
    data = _post(body)
    METER["calls"] += 1
    METER["prompt"] += data.get("prompt_eval_count", 0) or 0
    METER["output"] += data.get("eval_count", 0) or 0
    return data


ollama_model._post = _metered
CALLS = []
_answer = PL.Pipeline.answer


def _recorded(self, message, session, history=None):
    out = _answer(self, message, session, history)
    CALLS.append(dict(config={k: v for k, v in self.cfg.items()}, message=message,
                      region=session.region, action=out["action"], reply=out["reply"],
                      cited=out.get("cited", []), why=out.get("why", []),
                      pack=[x["id"] for _, x in out.get("pack", [])]))
    return out


PL.Pipeline.answer = _recorded


def main():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print(f"Capstone pipeline real run  model={llm.name()}  seed={llm.SEED} "
              f"temperature={llm.TEMPERATURE}  date={DATE}")
        PL.main()
        print(f"model calls={METER['calls']} prompt_tokens={METER['prompt']} "
              f"output_tokens={METER['output']}")
    text = buf.getvalue()
    sys.stdout.write(text)
    log = OUT / f"{DATE}-{TAG}-capstone-real.txt"
    log.write_text(text)
    rep = OUT / f"{DATE}-{TAG}-capstone-replies.json"
    rep.write_text(json.dumps(CALLS, indent=1, default=str))
    print(f"wrote {log}\nwrote {rep}")


if __name__ == "__main__":
    main()
