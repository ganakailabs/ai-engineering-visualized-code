"""Chapter 7: Fluent Is Not True (code moved from the Oct 6 Ch 5; chapter text pending)."""
import re

from stub_model import call_model
from store import POLICY, policy_text


# MM-017 / MM-019: a fluent answer must point at a clause that exists
def cited_clauses_exist(text):
    cited = re.findall(r"\b(R\d+)\b", text)
    return bool(cited) and all(c in POLICY for c in cited)


if __name__ == "__main__":
    reply = call_model([{"role": "system", "content": policy_text()},
                        {"role": "user", "content": "Do you do price match refunds?"}])["text"]
    print("reply:", reply, "| cited clauses exist:", cited_clauses_exist(reply))
