"""Optional: run the book's code against a real local model with Ollama.

Off by default. The stub stays the default so every test is deterministic and
needs no key. To switch, start Ollama, pull a model, then set an env var:

    ollama pull llama3.2
    AIEV_MODEL=ollama:llama3.2 python3 ch06.py

Uses only the standard library: one POST to http://localhost:11434/api/chat
(set AIEV_OLLAMA_URL to use another address). Real outputs WILL differ from
the expected outputs printed in the book. That is the point: compare them.
"""
import json
import os
import sys
import urllib.error
import urllib.request

import formats

URL = os.environ.get("AIEV_OLLAMA_URL", "http://localhost:11434") + "/api/chat"
_warned = set()


def selected():
    """The Ollama model name from AIEV_MODEL=ollama:<model>, or None."""
    value = os.environ.get("AIEV_MODEL", "")
    return value.split(":", 1)[1] if value.startswith("ollama:") else None


def _text(content):
    if isinstance(content, str):
        return content
    return " ".join(p.get("text", "") for p in content if p.get("type") == "text")


def _tool(t):
    """Book tool spec (Ch 11) -> Ollama's function-tool JSON."""
    props = {k: {"type": "string", "description": str(v)}
             for k, v in t.get("parameters", {}).items()}
    return {"type": "function",
            "function": {"name": t["name"], "description": t.get("description", ""),
                         "parameters": {"type": "object", "properties": props,
                                        "required": list(props)}}}


def build_request(messages, model, temperature=0.0, max_output_tokens=300,
                  seed=None, tools=None):
    options = {"temperature": temperature, "num_predict": max_output_tokens}
    if seed is not None:
        options["seed"] = seed
    msgs = [{"role": m["role"], "content": _text(m["content"])}
            for m in messages]
    hint, wants_json = formats.for_messages(messages)
    if hint:                       # real models need the format spelled out
        if msgs and msgs[0]["role"] == "system":
            msgs[0] = dict(msgs[0], content=msgs[0]["content"] + "\n\n" + hint)
        else:
            msgs.insert(0, {"role": "system", "content": hint})
    body = {"model": model, "stream": False, "options": options,
            "messages": msgs}
    if wants_json:
        body["format"] = "json"    # Ollama JSON mode
    if tools:
        body["tools"] = [_tool(t) for t in tools]
    return body


def parse_response(data, model):
    msg = data.get("message", {})
    calls = [{"name": c["function"]["name"],
              "arguments": c["function"].get("arguments", {})}
             for c in msg.get("tool_calls") or []]
    result = {"text": msg.get("content", ""),
              "usage": {"input_tokens": data.get("prompt_eval_count", 0),
                        "output_tokens": data.get("eval_count", 0)},
              "finish_reason": "length" if data.get("done_reason") == "length"
              else "stop", "model": "ollama:" + model}
    if calls:
        result["tool_calls"] = calls
        result["finish_reason"] = "tool_calls"
    return result


def _post(body, opener=urllib.request.urlopen):
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with opener(req, timeout=300) as r:
        return json.loads(r.read())


def call_ollama(messages, model, temperature=0.0, max_output_tokens=300,
                seed=None, tools=None, opener=urllib.request.urlopen):
    body = build_request(messages, model, temperature, max_output_tokens,
                         seed, tools)
    try:
        return parse_response(_post(body, opener), model)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        if tools and "does not support tools" in detail:
            if model not in _warned:          # fall back, and say why
                _warned.add(model)
                print(f"[ollama] {model} has no tool calling; asking again "
                      "without tools. Pick a tools model: "
                      "https://ollama.com/search?c=tool", file=sys.stderr)
            body.pop("tools")
            return parse_response(_post(body, opener), model)
        raise RuntimeError(f"Ollama error {e.code}: {detail}. "
                           f"Did you run 'ollama pull {model}'?") from None
    except urllib.error.URLError:
        raise RuntimeError(
            f"Cannot reach Ollama at {URL}. Start it with 'ollama serve' "
            "(or open the Ollama app), or unset AIEV_MODEL to use the "
            "built-in stub.") from None
