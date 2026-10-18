"""The optional Ollama adapter builds the right request. No network: a fake
opener stands in for urllib. Run: python3 tests/test_ollama_adapter.py"""
import io
import json
import os
import sys
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ollama_model as om  # noqa: E402
from ch11 import TOOLS  # noqa: E402

msgs = [{"role": "system", "content": "Rules."},
        {"role": "user", "content": [{"type": "text", "text": "Refund #2001?"}]}]
sent = []


def fake(reply):
    def opener(req, timeout):
        sent.append((req.full_url, json.loads(req.data), timeout))
        return io.BytesIO(json.dumps(reply).encode())
    return opener


reply = {"message": {"role": "assistant", "content": "",
                     "tool_calls": [{"function": {"name": "fetch_order",
                                                  "arguments": {"order_id": "2001"}}}]},
         "done_reason": "stop", "prompt_eval_count": 40, "eval_count": 9}
r = om.call_ollama(msgs, "llama3.2", 0.5, 120, 7, TOOLS, opener=fake(reply))
url, body, _ = sent[-1]
assert url.endswith("/api/chat")
assert body["model"] == "llama3.2" and body["stream"] is False
assert body["options"] == {"temperature": 0.5, "num_predict": 120, "seed": 7}
assert body["messages"][1] == {"role": "user", "content": "Refund #2001?"}
fn = body["tools"][0]
assert fn["type"] == "function" and fn["function"]["name"] == "fetch_order"
assert fn["function"]["parameters"]["required"] == ["order_id"]
assert r["tool_calls"] == [{"name": "fetch_order", "arguments": {"order_id": "2001"}}]
assert r["usage"] == {"input_tokens": 40, "output_tokens": 9}

# env var selects the adapter; unset means the stub
os.environ["AIEV_MODEL"] = "ollama:llama3.2"
assert om.selected() == "llama3.2"
del os.environ["AIEV_MODEL"]
assert om.selected() is None


# Ollama not running: a clear message, not a stack of socket errors
def down(req, timeout):
    raise urllib.error.URLError("connection refused")


try:
    om.call_ollama(msgs, "llama3.2", opener=down)
    raise AssertionError("should have failed")
except RuntimeError as e:
    assert "ollama serve" in str(e) and "unset AIEV_MODEL" in str(e)


# a model without tool calling: ask again without tools
def no_tools(req, timeout):
    if "tools" in json.loads(req.data):
        raise urllib.error.HTTPError(req.full_url, 400, "bad", {}, io.BytesIO(
            b'{"error":"llama2 does not support tools"}'))
    return io.BytesIO(json.dumps({"message": {"content": "escalate: no tool"},
                                  "eval_count": 3}).encode())


om._warned.add("llama2")   # keep the test output quiet
r = om.call_ollama(msgs, "llama2", tools=TOOLS, opener=no_tools)
assert r["text"] == "escalate: no tool" and "tool_calls" not in r
print("ollama adapter test: OK")
