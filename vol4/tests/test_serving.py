"""Tests for serving.py (Chapter 11): the estimator's arithmetic under its assumption."""
import _path  # noqa: F401

import serving as S

assert S.kv_bytes_per_token() == 2 * 32 * 8 * 128 * 2 == 131_072
assert S.kv_bytes(8192, 16) == 16 * S.GIB                  # 128 KiB x 8192 x 16
assert S.kv_bytes(8192, 32) == 2 * S.kv_bytes(8192, 16)    # linear in batch
hyb = S.kv_bytes(8192, 16, sliding=(16, 128))
assert S.kv_bytes(8192, 16) / 2 < hyb < S.kv_bytes(8192, 16)
assert S.kv_bytes(100, 1, sliding=(16, 128)) == S.kv_bytes(100, 1)  # within window

assert S.self_host_naive(10_000) < S.api_cost(10_000) < S.self_host_full(10_000)
assert S.gpus_needed(150_000) == 1 and S.gpus_needed(150_001) == 2
assert abs(S.self_host_full(S.break_even()) - S.api_cost(S.break_even())) < 1e-6
assert S.max_sequences(80, 8192, bits=4) > S.max_sequences(80, 8192, bits=16)
assert S.max_sequences(80, 8192, reserve=0.10) == 57          # (72 - 14.9) GiB / 1 GiB
assert S.planned_sequences(57) == 42
print("test_serving: OK")
