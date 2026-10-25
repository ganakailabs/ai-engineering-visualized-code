"""Chapter 21 exercise: what to remember, what to forget.

1. Recall Asha's notes for "my mug set arrived cracked again".
   How many tokens does that save over sending every note?
2. Try to remember a note without consent. Is it stored?
3. Run forget(). Which of Asha's notes survive?
Run: python3 vol1/solutions/ch21_solution.py
"""
import _path  # noqa: F401
from ch21 import NOTES, forget, recall, remember, tokens

if __name__ == "__main__":
    every = [n["text"] for n in NOTES if n["who"] == "asha"]
    found = recall("asha", "My new mug set arrived cracked again")
    print("tokens: every note", tokens(every), "| recalled", tokens(found))
    before = len(NOTES)
    stored = remember("asha", "Lives alone.", consent=False)
    print("stored without consent:", stored)
    dropped = forget()
    left = [n["text"] for n in NOTES if n["who"] == "asha"]
    print("dropped:", dropped, "| Asha keeps:", len(left))
    assert found == ["Mug set #2001 arrived cracked; a replacement was sent."]
    assert tokens(found) < tokens(every) / 10
    assert stored is False and len(NOTES) == before - dropped
    assert not any("warranty" in t for t in left)
    print("ch21 solution: OK")
