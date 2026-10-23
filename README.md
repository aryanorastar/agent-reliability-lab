# Agent Reliability Lab

Three small, executable proof-of-work demos by **Aryan Gupta**, a Computer Engineering student at Thapar (expected 2028) and an Omi contributor. Built with Codex assistance; implementation and validation commands are inspectable below.

The question: **Did the agent actually complete the action it claimed?**

This is an independent local prototype using synthetic data, a real localhost HTTP service and SQLite. It does not test or benchmark the hosted products mentioned below, use customer data, make phone calls, or spend model/API credits.

## Run in one minute

Python 3.10+; no external dependencies.

```sh
git clone https://github.com/aryanorastar/agent-reliability-lab.git
cd agent-reliability-lab
python3 lab.py
python3 -m unittest discover -s tests -v
```

Expected: **24/24 assertions pass** and four integration/regression tests pass. See the [recorded result](reports/results.json). Run the commands to reproduce rather than relying on a screenshot.

## Three demonstrations

| Demo | Concrete failure | Evidence |
|---|---|---|
| [Outcome checks for Hamming](demos/hamming.md) | Agent says booking completed with no successful booking receipt; a transfer is initiated but never bridges | 12 synthetic traces, including unsafe and valid controls |
| [Webhook reconciliation for Roark](demos/roark.md) | Duplicate and late call events misstate a call or human transfer's outcome | 5 local state assertions, plus concurrent duplicate and invalid-input tests |
| [Approval and retry receipts for Dify](demos/dify.md) | A send succeeds downstream, its response is lost, and the worker retries after restarting | 7 local HTTP/SQLite assertions; a fresh Python process retries with the same key |

```sh
python3 lab.py --demo outcomes --output reports/outcomes.json
python3 lab.py --demo webhooks --output reports/webhooks.json
python3 lab.py --demo receipts --output reports/receipts.json
```

## What to inspect

1. Start with a deliberately invalid trace in [outcome-cases.json](demos/outcome-cases.json).
2. `verify_outcome()` checks its structured evidence, not its confident wording.
3. `Ledger.execute()` binds an approval to tenant, action ID and argument digest. It keeps an ambiguous delivery **unknown** until it gets a validated receipt.
4. The HTTP receiver commits an idempotency key and effect in one SQLite transaction. Its deduplication contract is essential to the example.
5. `Ledger.webhook()` persists event identities and advances the call phase monotonically. A transfer-start event does not establish a human connection.

## Limits that matter

- These are deterministic trace checks, not an LLM judge or a measured audio/latency benchmark.
- The localhost receiver implements the idempotency contract. Arbitrary provider APIs might not; ambiguous outcomes then need provider-specific reconciliation.
- The webhook demo starts **after** a trusted adapter has verified provider authentication and mapped an authenticated tenant. It does not implement Retell's signature verification or accept public webhooks.
- Call lifecycle events are deduplicated by tenant, call ID and event type. This deliberately excludes repeated transcript updates. The minimal transfer model does not represent multiple transfer attempts in one call.
- A receipt is trusted evidence from this demo's downstream service. A production system must validate its origin and authorization; an arbitrary model-written receipt is not sufficient.
- This is a portfolio prototype, not a production service or evidence of a defect in Hamming, Roark, Dify or Retell.

## Related public work

- [Omi Watch recording recovery contribution](https://github.com/BasedHardware/omi/pull/22059)
- [Omi mobile task delivery and recovery contribution](https://github.com/BasedHardware/omi/pull/22841)
- [Omi Support Bot](https://github.com/BasedHardware/omi-vector-bot)
- [Astar: macOS voice assistant](https://github.com/aryanorastar/Astar)

For a paid, student-compatible evaluation or integration project: [aryangupts05@gmail.com](mailto:aryangupts05@gmail.com). Specific weekly hours and scope would need agreement.
