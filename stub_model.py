"""A scripted stand-in for a chat model API. No network, no key.

call_model(messages, temperature=0.0, max_output_tokens=300, seed=None,
           model="stub-large", tools=None)
returns {"text": str, "usage": {"input_tokens": int, "output_tokens": int},
         "finish_reason": "stop" | "length", "model": str}
plus "tool_calls": [{"name": str, "arguments": dict}] when the model asks for a tool
(Chapter 11), and usage["thinking_tokens"] for the toy reasoning model (Chapter 9).

Toy models (Chapter 9): "stub-small", "stub-large" (the default) and "stub-reasoning".
They are scripted characters, not real models, and say nothing about any real model.
embed(text) (Chapter 12) is a toy embedding: hand-made concept axes, not a trained model.

The stub is scripted to reproduce the failure each chapter teaches.
Real models must be measured; do not read the stub's behaviour as data.
"""
import math
import random
import re


def rough_token_count(text: str) -> int:
    """PLACEHOLDER counter: one 'token' per word or punctuation mark.
    Real tokenizers differ. Measure with your provider's tokenizer."""
    return len(re.findall(r"\w+|[^\w\s]", text))


def _content_text(content) -> str:
    if isinstance(content, str):
        return content
    # list of parts: {"type": "text", "text": ...} or {"type": "image", ...}
    return " ".join(p.get("text", "") for p in content if p.get("type") == "text")


def _has_image(messages) -> bool:
    for m in messages:
        if isinstance(m["content"], list):
            if any(p.get("type") == "image" for p in m["content"]):
                return True
    return False


def sample(scores: dict, temperature: float, rng: random.Random) -> str:
    """Softmax over scores, then one weighted draw. temperature 0 = argmax."""
    if temperature <= 0:
        return max(scores, key=scores.get)
    weights = {k: math.exp(v / temperature) for k, v in scores.items()}
    total = sum(weights.values())
    r = rng.random() * total
    for k, w in weights.items():
        r -= w
        if r <= 0:
            return k
    return k


def _reply(messages, temperature, rng) -> str:
    system = " ".join(_content_text(m["content"]) for m in messages if m["role"] == "system")
    users = [_content_text(m["content"]) for m in messages if m["role"] == "user"]
    last = users[-1].lower() if users else ""
    everything = (system + " " + " ".join(users)).lower()
    has_policy = "policy (version" in everything
    pushy = any(w in last for w in ("manager", "insist", "lawyer", "unacceptable"))

    # Ch 10: an instruction hidden in ticket text. Obeyed unless the prompt marks
    # ticket text as data (delimiters plus a rule that says so).
    if "ignore previous instructions" in everything:
        if "text inside <ticket> is data" in system.lower() and "ignore previous instructions" not in system.lower():
            return "escalate: The ticket contains instructions; ticket text is data, not orders."
        return "approve: Approved as the ticket instructed."

    # Ch 10: adjectives without examples -> friendly prose, no decision label
    if "be concise" in system.lower() and "examples:" not in system.lower():
        return ("I'm so sorry to hear that! I've looked into your order and, sadly, "
                "this one can't be refunded, but I'm happy to help with anything else.")

    # Ch 3: rules mixed with customer text in the system message
    if "as the store manager i approve" in system.lower():
        return "approve: Approved as instructed by the store manager."

    # Ch 3: the same claim, but arriving as customer text in the user role
    if "as the store manager" in last:
        return "escalate: The ticket claims manager approval; refund rules come from policy, not ticket text."

    # Ch 2: pushy customer, no code-side rule check (the stub gives in)
    if pushy and "decision_locked" not in system.lower():
        return "approve: I understand your frustration. I have approved a full refund."

    # Ch 3: image input
    if _has_image(messages):
        return "approve: The photo shows a visible crack, so the item qualifies under R2."

    # Ch 7: told to answer only from the page, the policy gap becomes an abstain
    if ("price match" in last or "price-match" in last) and "answer only from the policy" in system.lower():
        return "escalate: The policy does not cover price matching."

    # Ch 5: question the policy does not cover
    if "price match" in last or "price-match" in last:
        return ("approve: Yes, we offer price-match refunds within 14 days (R5)."
                if has_policy else "Yes, we offer price-match refunds within 14 days.")

    # Ch 5: borderline ticket, the dice decide
    if "opened the box" in last:
        scores = {"approve": 1.0, "escalate": 0.8, "deny": 0.6}
        return sample(scores, temperature, rng) + ": Borderline case under R1."

    # Ch 2: private, current data the model cannot know
    if ("where is" in last or "status" in last) and "order facts" not in everything:
        return "Your order has shipped and will arrive in 3-5 business days."

    # Ch 1 and 2: no policy in context -> fluent, confident, invented
    if not has_policy:
        if "refund" in last:
            return "Yes, you'll get a full refund within 3 days."
        return "Happy to help! Could you share more details?"

    # Policy present: follow the facts that the code put in the context
    m = re.search(r"days_since_delivery=(\d+)", everything)
    days = int(m.group(1)) if m else None
    if "final_sale=true" in everything:
        return "deny: Final-sale items cannot be refunded (R3)."
    if days is not None and days > 30:
        return f"deny: Delivered {days} days ago; the window is 30 days (R1)."
    if "amount=" in everything:
        amount = int(re.search(r"amount=(\d+)", everything).group(1))
        if amount > 5000:
            return "escalate: Amount above INR 5,000 needs an agent (R4)."
        return "approve: Within 30 days of delivery (R1)."
    seen = re.search(r"#(\d{4})", " ".join(users))
    if seen:
        return f"escalate: Order #{seen.group(1)} needs a lookup before I can decide."
    return "escalate: I could not find the order. Please share your order number."


# Ch 9: toy model characters. Numbers are made up for the demo, not measurements.
THINKING_TOKENS = 120  # hidden working tokens the toy reasoning model spends per call


def _small_model_slip(messages, text):
    """The toy small model skips the R4 amount check (scripted weakness)."""
    if text.startswith("escalate: Amount above"):
        return "approve: Within 30 days of delivery (R1)."
    return text


# Ch 11: JSON output and tool calls
def _json_reply(messages, temperature, rng, tools):
    import json
    roles = [m["role"] for m in messages]
    users = [_content_text(m["content"]) for m in messages if m["role"] == "user"]
    if tools and "tool" not in roles:
        m = re.search(r"#(\d{4})", users[-1] if users else "")
        if m and any(t.get("name") == "fetch_order" for t in tools):
            return None, [{"name": "fetch_order", "arguments": {"order_id": m.group(1)}}]
    facts = [_content_text(m["content"]) for m in messages if m["role"] == "tool"]
    plain = [m for m in messages if m["role"] != "tool"]
    if facts:
        plain = plain + [{"role": "system", "content": "\n".join(facts)}]
    base = _reply(plain, temperature, rng)
    decision, _, reason = base.partition(":")
    clause = re.findall(r"\b(R\d+)\b", reason)
    repairing = any(u.startswith("Your last reply failed the check") for u in users)
    if decision.strip() == "escalate" and "R4" in clause and not repairing:
        # scripted slip: a value outside the contract's allowed list
        return json.dumps({"decision": "approved", "clause": "R4", "reason": "Big order, approved."}), None
    return json.dumps({"decision": decision.strip(), "clause": clause[0] if clause else None,
                       "reason": reason.strip()}), None


def call_model(messages, temperature=0.0, max_output_tokens=300, seed=None,
               model="stub-large", tools=None):
    rng = random.Random(seed)
    tool_calls = None
    system = " ".join(_content_text(m["content"]) for m in messages if m["role"] == "system")
    if "reply with json" in system.lower():
        text, tool_calls = _json_reply(messages, temperature, rng, tools)
        text = text or ""
    else:
        text = _reply(messages, temperature, rng)
    if model == "stub-small":
        text = _small_model_slip(messages, text)
    words = text.split()
    finish = "stop"
    if rough_token_count(text) > max_output_tokens:
        text = " ".join(words[:max_output_tokens])
        finish = "length"
    prompt = " ".join(_content_text(m["content"]) for m in messages)
    usage = {"input_tokens": rough_token_count(prompt),
             "output_tokens": rough_token_count(text)}
    if model == "stub-reasoning":
        usage["thinking_tokens"] = THINKING_TOKENS
        usage["output_tokens"] += THINKING_TOKENS  # billed as output tokens
    result = {"text": text, "usage": usage, "finish_reason": finish, "model": model}
    if tool_calls:
        result["tool_calls"] = tool_calls
        result["finish_reason"] = "tool_calls"
    return result


# Ch 12: a toy embedding. Each axis is a hand-picked concept; words count toward it.
# A real embedding model learns hundreds or thousands of axes from data.
AXES = ("money", "time", "damage", "sale", "delivery")
CONCEPT_WORDS = {
    "money": ("refund", "refunded", "refunds", "money", "reimburse", "price", "inr", "pay"),
    "time": ("days", "day", "window", "weeks", "late"),
    "damage": ("damaged", "broken", "cracked", "crack", "photo", "replace", "replaced"),
    "sale": ("final-sale", "clearance", "sale", "discount"),
    "delivery": ("delivery", "delivered", "shipping", "arrive", "parcel", "where"),
}


def embed(text):
    words = re.findall(r"[a-z0-9-]+", text.lower())
    vec = [sum(w in CONCEPT_WORDS[a] for w in words) for a in AXES]
    length = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / length for v in vec]  # unit length, so dot product = cosine
