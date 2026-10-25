"""Model adapter for Vol 2: the stub by default, a real local model on request.

    AIEV_MODEL=ollama:llama3.2 python3 vol2/ch01.py

The stub is a script written for each chapter (a demonstration, not a model). The
real path reuses Vol 1's ollama_model.py, asks for JSON mode, and parses the reply
with parse.first_json. Anything that is not the JSON object the caller needs comes
back as None, with a [parse] warning on stderr; the caller turns None into a safe
escalate. A real model's output WILL differ from the book's stub trace.
"""
import json

import _root  # noqa: F401  (Vol 1 ollama_model.py, parse.py)

import ollama_model
from parse import first_json, warn


SEED, TEMPERATURE = 7, 0.0     # Chapter 17 sets these per trial; every earlier chapter keeps 7 and 0.0


def name():
    real = ollama_model.selected()
    return f"ollama:{real}" if real else "stub"


def ask_json(system, user, stub, max_output_tokens=400):
    """One model turn. Returns (dict or None, raw text).

    stub(user) -> dict is the scripted reply used when no real model is selected."""
    real = ollama_model.selected()
    if real is None:
        reply = stub(user)
        return reply, json.dumps(reply)
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
    body = ollama_model.build_request(messages, real, temperature=TEMPERATURE,
                                      max_output_tokens=max_output_tokens, seed=SEED)
    body["format"] = "json"                       # Ollama JSON mode
    try:
        data = ollama_model._post(body)
        msg = data.get("message", {})
        if not msg.get("content") and msg.get("thinking"):
            # a reasoning model (gpt-oss) used the cap thinking: once more, with room
            warn(f"{real} spent its {max_output_tokens}-token cap thinking; asking again")
            body["options"]["num_predict"] = max_output_tokens * 4 + 1024
            data = ollama_model._post(body)
    except Exception as e:                         # unreachable server, HTTP error
        warn(f"model call failed ({type(e).__name__}: {e}); escalating")
        return None, ""
    text = ollama_model.parse_response(data, real)["text"]
    move = first_json(text, (dict,))
    if move is None:
        warn(f"model reply is not a JSON object: {text[:80]!r}")
    return move, text
