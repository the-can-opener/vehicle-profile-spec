# Mapping rules

- signals.X.monitor becomes a DBC read.signal on the vocabulary's canonical path.
- A single-actuator action becomes a quoted write case. LOCK and UNLOCK become the true and false cases of Vehicle.Cabin.Door.Central.IsLocked. WIPERS becomes the MEDIUM case of Vehicle.Body.Windshield.Front.Wiping.Mode when the command does not select a speed. Any other multi-actuator or non-VSS command becomes a named action.
- Byte arrays become uppercase spaced hex. A wildcard remains `*`.
- ref: sequences.x becomes call: x, with the endpoint owned by the caller.
- request_id/response_id become tx/rx on a raw CAN endpoint; request-only endpoints omit rx/timeout.
- Inline send objects receive a generated request-only endpoint.
- Shared endpoint-free sequences can be converted after their dependencies.
- Declare --framing raw, isotp or isotp-single-frame for request/response migration. No framing is guessed. The last mode validates/removes request PCI and adjusts DBC response offsets for the raw one-byte header.
- Use --responder ENDPOINT=HEX when response IDs are a range, and --steering-side left|right for physical door names.
- Queries translate fixed-length VIN/hex and ordinary DBC decoders, merging with a passive binding on the same property. Known equivalent unit spellings and supported enum labels are normalized.
- Unknown identities, ambiguous messages, unsupported codecs/multiplexing and incompatible integer/fractional domains stay in unmapped.

The vocabulary is `docs/vocabulary.yaml` in the source repository and is bundled into the wheel. The CLI uses it directly. Original uncertain bindings are preserved in unmapped, never silently discarded. The migrated file alone is not proof of wire equivalence.
