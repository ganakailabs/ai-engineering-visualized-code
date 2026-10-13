"""Chapter 15 exercise: trace the four stages, then break one.

1. For "My NW-500 battery stopped charging. Is it covered?" print what each stage
   produces: index size, retrieved ids, the augmented prompt, the answer.
2. Break stage 2: retrieve with k=0. What does the model say now?
3. Ask the same question closed book. What does the model claim?
Run: python3 solutions/ch15_solution.py
"""
import _path  # noqa: F401
from ch15 import augment, closed_book, generate, index, retrieve

if __name__ == "__main__":
    q = "My NW-500 battery stopped charging. Is it covered?"
    idx = index()
    passages = retrieve(q, idx)
    prompt = augment(passages)
    answer = generate(prompt, q)
    print("1 index:", len(idx), "passages\n2 retrieve:", list(passages))
    print("3 augment:\n" + prompt + "\n4 generate:", answer)
    broken = generate(augment(retrieve(q, idx, k=0)), q)
    memory = closed_book(q)
    print("k=0:", broken, "\nclosed book:", memory)
    assert list(passages) == ["S2"] and "[S2]" in answer and "12-month" in answer
    assert broken.startswith("escalate"), "no pages: the rules make it hand over"
    assert "6-month" in memory, "closed book: fluent and wrong (the handbook says 12 months)"
    print("ch15 solution: OK")
