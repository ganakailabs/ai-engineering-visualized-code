"""A scripted stand-in for a chat model API. No network, no key.

call_model(messages, temperature=0.0, max_output_tokens=300, seed=None)
returns {"text": str, "usage": {"input_tokens": int, "output_tokens": int},
         "finish_reason": "stop" | "length"}

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


def call_model(messages, temperature=0.0, max_output_tokens=300, seed=None):
    rng = random.Random(seed)
    text = _reply(messages, temperature, rng)
    words = text.split()
    finish = "stop"
    if rough_token_count(text) > max_output_tokens:
        text = " ".join(words[:max_output_tokens])
        finish = "length"
    prompt = " ".join(_content_text(m["content"]) for m in messages)
    return {
        "text": text,
        "usage": {"input_tokens": rough_token_count(prompt),
                  "output_tokens": rough_token_count(text)},
        "finish_reason": finish,
    }
