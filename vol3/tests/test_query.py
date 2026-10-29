"""Chapter 9: meaning-kept check on six named rewrites, pass-through and clarify."""
import _path  # noqa: F401

import query as Q

CASES = [  # (name, original, rewrite parts, every fact kept?)
    ("resolved it", "It broke again, and can I return the charger too, but not the case?",
     ["NW-500 broke again?", "can I return the NW-500 charger too, but not the case?"], True),
    ("dropped exclusion", "can I return the charger but not the case",
     ["can I return the charger and case?"], False),
    ("dropped date", "can I return it before 15 November",
     ["can I return the NW-500?"], False),
    ("dropped limit", "is COD allowed under Rs 10000",
     ["is cash on delivery allowed?"], False),
    ("dropped product", "does the NW-550 battery cost extra",
     ["does the battery cost extra?"], False),
    ("hinglish kept", "mera NW-550 charge nahi ho raha",
     ["mera NW-550 charge nahi ho raha?"], True),
]


def test_six_named_rewrites():
    for name, original, parts, ok in CASES:
        assert all(Q.meaning_kept(original, parts).values()) == ok, name


def test_clear_question_passes_through():
    assert Q.understand("how do I reset the NW-550", {}) == [
        ("pass", "how do I reset the NW-550"), ("route", (1, "manuals"))]


def test_ambiguous_question_asks():
    assert Q.understand("is it still covered?", {}) == [("clarify", "which order?")]


def test_failed_check_asks_instead_of_searching():
    orig = Q.rewrite
    Q.rewrite = lambda m, h: ["NW-500 broke again?", "can I return the NW-500 charger and case?"]
    try:
        steps = Q.understand("It broke again, and can I return the charger too, but not the case?",
                             {"product": "NW-500"})
    finally:
        Q.rewrite = orig
    assert steps[-1][0] == "clarify" and not any(k == "route" for k, _ in steps)


def test_two_part_ticket_routes():
    steps = Q.understand("It broke again, and can I return the charger too, but not the case?",
                         {"product": "NW-500"})
    assert [d for k, d in steps if k == "route"] == [(1, "manuals"), (2, "policy")]




def test_non_string_parts_fail_check_and_ask():
    # llama3.2 run 2026-10-27 returned parts as objects; that must not crash
    # and must not be coerced: the check fails and the customer is asked.
    real = Q.llm.ask_json
    Q.llm.ask_json = lambda *a, **k: ({"parts": [{"text": "NW-500 broke again?"},
                                                 {"text": "return the charger?"}]}, None)
    try:
        steps = Q.understand(
            "It broke again, and can I return the charger too, but not the case?",
            {"product": "NW-500"})
    finally:
        Q.llm.ask_json = real
    kinds = [k for k, _ in steps]
    check = dict(steps)["check"]
    assert check["parts_are_text"] is False and not all(check.values())
    assert kinds[-1] == "clarify" and "route" not in kinds



def test_action_swap_fails_bindings():
    # External review probe: every word survives, but the actions swap products.
    kept = Q.meaning_kept("Can I return the mug and keep the lamp?",
                          ["Can I keep the mug and return the lamp?"])
    assert kept["entities"] and kept["negation"] and kept["dates"] and kept["constraints"]
    assert kept["bindings"] is False


def test_action_swap_asks_instead_of_routing():
    orig = Q.rewrite
    Q.rewrite = lambda m, h: ["Can I keep the mug?", "Can I return the lamp?"]
    try:  # two parts, so the message is rewritten rather than passed through
        steps = Q.understand("Can I return the mug and can I keep the lamp?", {})
    finally:
        Q.rewrite = orig
    assert steps[-1][0] == "clarify" and not any(k == "route" for k, _ in steps)


def test_split_parts_keep_bindings():
    kept = Q.meaning_kept("Can I return the mug and keep the lamp?",
                          ["Can I return the mug?", "Can I keep the lamp?"])
    assert all(kept.values()), kept


def test_action_does_not_leak_across_sentences():
    assert Q.bindings("Can I return the mug? Is the lamp covered?") == {("return", "mug")}


def test_known_limit_added_fact_not_detected():
    # Documented limit: the heuristic cannot tell that a rewrite added a fact the
    # customer never stated. A second check (or keeping the original) is needed.
    kept = Q.meaning_kept("can I return the mug",
                          ["can I return the mug, which arrived broken?"])
    assert all(kept.values())


if __name__ == "__main__":
    from _run import run_all
    run_all("test_query")
