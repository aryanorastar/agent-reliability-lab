# Approval-bound actions and ambiguous retries: a demonstration for Dify

Dify's [public platform](https://dify.ai/) connects agent reasoning to tools and workflows. A useful integration check is what happens when a tool commits an action but its success response is lost.

Run `python3 lab.py --demo receipts --output reports/receipts.json`.

The independent demo starts a real localhost HTTP receiver and persists its effects in SQLite. A synthetic reply action requires approval bound to its tenant, action ID and arguments. The receiver commits the action, but the client deliberately drops the response. A fresh Python process then retries against the same database and receiver.

Observed result: the first client reports an unknown outcome; the retry receives the original receipt; the downstream table contains one effect. Cross-tenant and changed-argument attempts are rejected, and replay returns a saved receipt.

This demonstrates a reconciliation contract, not a Dify bug, integration test against Dify, or a universal exactly-once guarantee. The downstream receiver's idempotency behavior is part of the prototype. A provider without that contract needs its own reconciliation method. Approval revocation, real provider auth and multi-service crash recovery need further work before production use.

[Implementation](../lab.py) | [Recorded results](../reports/receipts.json)
