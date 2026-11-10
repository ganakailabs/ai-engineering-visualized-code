"""Chapter 11 exercise: Double the context.

Double the context length in the KV estimator, same batch. Predict first: how does KV
memory change? Under the printed assumption (full attention on every layer) the cache
grows per token per layer, so it doubles. With half the layers on a sliding window,
those layers stop growing past the window, so it less than doubles. The model shape is
the chapter's illustrative example, not a named model.
"""
import _path  # noqa: F401

import serving as S

a, b = S.kv_bytes(8192, 16), S.kv_bytes(16384, 16)
print("kv assume=full_attention (every layer)")
print(f"  context 8192 -> {a / S.GIB:.1f} GiB; 16384 -> {b / S.GIB:.1f} GiB "
      f"(x{b / a:.2f})")
h1 = S.kv_bytes(8192, 16, sliding=(16, 128))
h2 = S.kv_bytes(16384, 16, sliding=(16, 128))
print("kv assume=half layers sliding window=128")
print(f"  context 8192 -> {h1 / S.GIB:.1f} GiB; 16384 -> {h2 / S.GIB:.1f} GiB "
      f"(x{h2 / h1:.2f})")
print(f"max seqs on 80 GiB, 16-bit weights: {S.max_sequences(80, 8192)} at 8192, "
      f"{S.max_sequences(80, 16384)} at 16384")
assert b == 2 * a
assert 1 < h2 / h1 < 2
assert S.max_sequences(80, 16384) == S.max_sequences(80, 8192) // 2
print("ch11 solution: OK")
