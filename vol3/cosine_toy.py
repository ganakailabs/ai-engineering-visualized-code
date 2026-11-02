"""A three-number toy for Chapter 6: cosine similarity by hand, and a near-miss.

Each text gets three hand-picked numbers: how much it is about charging, about
headphones, and about mugs. Real embeddings have hundreds of numbers learned by a model;
these three are made up so the arithmetic fits on a page. Notice what they cannot hold:
the product code. "NW-50" and "NW-500" look the same along all three axes.

    cos(a, b) = (a . b) / (|a| |b|)
"""
import math

QUERY = ("NW-500 charger", (0.9, 0.4, 0.0))
DOCS = [
    ("NW-50 charger cable", (0.9, 0.3, 0.0)),      # similar words, WRONG product
    ("NW-500 battery life", (0.5, 0.8, 0.0)),
    ("mug care", (0.0, 0.0, 1.0)),
]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cosine(a, b):
    return dot(a, b) / (math.sqrt(dot(a, a)) * math.sqrt(dot(b, b)))


def main():
    q = QUERY[1]
    print(f"query {QUERY[0]!r} = {q}  |q| = {math.sqrt(dot(q, q)):.3f}")
    for text, v in sorted(DOCS, key=lambda d: -cosine(q, d[1])):
        print(f"  {text!r:24} {v}  dot={dot(q, v):.2f}  |d|={math.sqrt(dot(v, v)):.3f}  "
              f"cos={cosine(q, v):.3f}")
    print("top hit is the NW-50 cable: close in meaning, wrong product (Ch 7 adds an exact-id lane)")


if __name__ == "__main__":
    main()
