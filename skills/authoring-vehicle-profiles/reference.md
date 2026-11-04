# Format 2 reference

The manifest has `manifest: 1`, `format: 2`, reverse-DNS `id`, semver `version`, `name`, `vss: "6.1"`, applicability and explicit asset lists. Without `documents`, it is also the only document.

Document sections: channels, endpoints, sources, properties, sequences, queries, actions, requires, extensions and applies_to. Entries replace whole entries in order; null deletes. Cross-package replacement requires document `override: true`. Calls resolve after merge. Unknown required extensions cannot activate.

Read signal forms: DBC/message/signal; channel/id/id_format/length/decode; source/output. Read query forms: endpoint/request/response/decode or source/output. Query offsets start after the matched response prefix. Source kind must match acquisition kind. Policy controls preferred binding, max_age_ms and active_fallback; it cannot grant runtime permission or implicitly enable polling.

Write forms: endpoint/request/expect; endpoint/steps/deadline_ms; or cases of those bodies. Cases use canonical string targets such as "true". Constraints narrow VSS min/max and define an exact decimal step grid. Parts encode `(input - offset) / scale` without rounding. A sequence has only steps and inherits the endpoint. A response match is acknowledgement; it never updates observed state. No response expectation means sent. Transmission timeout can mean OUTCOME_UNKNOWN.

Request-only endpoints omit rx and timeout_ms. Response endpoints need both. Raw CAN payloads and patterns include the exact data field; ISO-TP uses application bytes and owns PCI/padding. Reassembled application responses cannot be treated as raw frames.

Named queries declare description, endpoint, request, response and typed decode or typed outputs. Actions declare description and a write body; optional retry defaults to never. Actions have no cases, effect or output_schema. There are no operations, verify or completion fields.
