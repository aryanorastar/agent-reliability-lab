# Architecture and verification checklist

Synthetic fixtures -> structured outcome assertions -> per-case JSON report.

Approved action -> tenant/action/argument binding -> localhost HTTP receiver -> SQLite delivery record -> receipt -> client SQLite action record. A deliberately lost response forces an ambiguous retry from a separate process.

Authenticated synthetic event -> validated envelope -> transactional event deduplication -> monotonic call state -> handoff outcome. Provider auth is an explicit boundary outside the prototype.

## Acceptance checklist

- [x] No vendor accounts, model calls, calls to people, customer data or external side effects.
- [x] Unsafe traces have valid controls as well as deliberate failures.
- [x] Local HTTP integration exercises downstream commit, lost response, fresh-process retry and stored receipt replay.
- [x] Tenant mismatch and changed arguments are denied.
- [x] Duplicate/out-of-order events and invalid-input persistence behavior are checked.
- [x] Concurrent duplicate events are checked against the real SQLite store.
- [x] Product-specific notes cite public sources and distinguish independent prototype behavior from vendor behavior.
- [ ] Real vendor adapter authentication, hosted execution and production qualification. Outside this portfolio demo's scope; not claimed.

This repository starts as a public proof-of-work artifact. Any future PR must start as a draft and remain so until its applicable flow and current-commit checks are verified.
