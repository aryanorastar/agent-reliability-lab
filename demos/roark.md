# Call and handoff event reconciliation: a demonstration for Roark

Roark's [public product](https://roark.ai/) focuses on evaluating voice-agent behavior. A test report can be misleading if the application mistakes a transfer request for a completed human connection, or regresses a call's state when an older event is retried.

Run `python3 lab.py --demo webhooks --output reports/webhooks.json`.

This independent SQLite example ingests synthetic events shaped around the documented `event` and `call.call_id` envelope in [Retell's webhook documentation](https://docs.retellai.com/features/webhook-overview). That documentation describes non-blocking delivery, retries, and separate transfer-started, bridged and cancelled events.

The local checks cover:

- An analyzed call remains analyzed after late started/ended events.
- Repeated end events are deduplicated.
- The same call ID in a different authenticated tenant has independent state.
- A failed call may end without ever producing a started event.
- A late transfer-started event does not replace an observed cancellation.

The test suite also races 12 duplicate deliveries across six threads and requires one new event record. Invalid payloads leave no event state.

Scope: this is not a Roark adapter or an actual Retell integration. Provider signature verification, real call delivery and multiple transfer attempts require an additional trusted adapter and live qualification. This example covers local reconciliation after authentication.

[Implementation](../lab.py) | [Recorded results](../reports/webhooks.json)
