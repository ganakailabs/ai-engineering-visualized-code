# Threat model (Vol 4 Ch 1, grown in Ch 13)

Northwind Goods is fictional. Every channel the model reads is a row. Attacks are the
scripted library in `security.py`; `tests/test_security.py` keeps every fixed attack in CI.

## Channels and boundaries (Ch 13)

| Channel | Boundary crossed | Worst action if the model obeys | Check outside the model | Attacks in suite |
|---|---|---|---|---|
| ticket | customer -> model | refund another customer's order | refund tool: owner from session; approval over limit | K2, H3, M1, M2 |
| documents | index -> model | same | same | K3, H2 |
| reviews | public -> model | same | same | K1, H1 |
| tool_results | courier -> model | same | same | none in ch13.py (exercise adds C1-C4) |
| memory | past chat -> model | same | same | R1 (red-team hit, Part 3) |
| plugins | plug-in server -> model | same | same | K4, H4 |

## Assets, operations and task authorization (Ch 13)

| Protected asset | Allowed operation | Task that authorizes it | Enforcement point | Tested by |
|---|---|---|---|---|
| money | refund the session customer's own order, under the approval limit | refund_request | refund tool (`issue_refund`) | K*, H*, M*, R1 (cross-customer); W1 (wrong task) |
| customer data | read the session customer's own order | refund_request, delivery_status | read tool (`order_details`) | D1 (disclosure) |

The task is set by code at triage and carried in the session. Results are scoped: the
tests show these boundaries hold on these scripted attacks, not every security property.
Report "model followed the injection" and "harmful outcome" as separate counts.

Held-out variants (H*, M*) are never read while writing a fix. Report the held-out score,
not the known score. Attack success on a recorded real model: one local run is in `runs/evidence/` (13 attacks,
3 runs each, two `llama3.2` sizes; an observation, not a rate).

## Service boundaries (Ch 1)

| Boundary | Threat | Control in the lab | Status |
|---|---|---|---|
| API | caller claims another customer's id in the body | identity from the session only; body id ignored | tested (Ch 1) |
| API | no session | 401 | tested (Ch 1) |
| Queue / workers | two workers run one job; duplicate refund | lease + ledger key from the job id | tested (Ch 1) |
| Tools | courier note injection (SC-011) | refund tool checks the session (Ch 13) | tested (Ch 13 exercise) |
| Logs | personal data written to logs | redaction at the sink | Ch 3 |
| Secrets | keys in code or prompts | none needed in the lab | not covered: the lab has no secrets; a deployment adds a secret store and secret scanning |
