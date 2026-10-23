# Outcome assertions: a small demonstration for Hamming

Hamming's [public product page](https://hamming.ai/) describes checking whether calls achieve their expected outcomes and illustrates a booking claim with no booking tool call. That is the specific product problem this independent example addresses.

Run `python3 lab.py --demo outcomes --output reports/outcomes.json`.

The fixture set contains 12 synthetic structured traces. Eight are deliberately unsafe: missing, failed, empty, cross-tenant or wrong-action receipts; approval skipped; transfer started/cancelled while the assistant claims a connection. Four valid controls avoid a grader that simply rejects everything.

The checker flags all eight unsafe fixtures and accepts all four valid controls. The intentionally weak comparison accepts a completed claim based on its wording and misses six of the unsafe traces. This is a contrast between two deterministic rules, not a claim of model accuracy or an evaluation of Hamming.

Useful next experiment with a team: adapt one real, permission-cleared tool trace format, agree a rubric with an engineer, then evaluate held-out cases. Audio quality, latency, ambiguous language and production signatures remain outside this prototype.

[Source](outcome-cases.json) | [Recorded results](../reports/outcomes.json)
