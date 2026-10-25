"""Chapter 17: a gate that sees no evidence, or incomplete evidence, fails closed."""
import _path  # noqa: F401

import ch17
from evals.scenarios import EXPECTED_ESCALATIONS

assert not ch17.gate([], "empty_probe")
full = ch17.trials(2)
assert ch17.gate(full, "agent")
only_esc = [r for r in full if r["sid"] in EXPECTED_ESCALATIONS]
assert not ch17.gate(only_esc, "only_escalations")
missing = [r for r in full if r["sid"] != "S09"]
assert not ch17.gate(missing, "missing_S09")
assert not ch17.gate(full + full[:1], "duplicate_trial")
assert not ch17.gate(full[:-1], "incomplete_matrix")
refunds = {"S01", "S04", "S06", "S08", "S09"}
part = ch17.trials(2, ids=refunds)
assert not ch17.gate(part, "refunds_only")                    # default: every scenario
assert ch17.gate(part, "refunds_only", expected=ch17.matrix(refunds, (None,), 2))
mixed = [dict(r, model="other") if i == 0 else r for i, r in enumerate(full)]
assert not ch17.gate(mixed, "mixed_models")
print("test_gate_evidence: OK")
