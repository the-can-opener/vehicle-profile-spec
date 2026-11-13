# Mapping rules

- signals.X.monitor becomes a DBC read.signal on the vocabulary's canonical path.
- A single-actuator action becomes a quoted write case. LOCK and UNLOCK become the true and false cases of Vehicle.Cabin.IsCentralLockEngaged. WIPERS becomes the MEDIUM case of Vehicle.Body.Windshield.Front.Wiping.Mode when the command does not select a speed. OPEN_*_WINDOW writes 100 on that door's Window.Position and CLOSE_*_WINDOW writes 0. WINDOW_CHILD_LOCK and WINDOW_CHILD_UNLOCK are the true and false cases of Vehicle.Cabin.IsWindowChildLockEngaged. Left and right assume left-hand drive. SEATBELT_WARNING maps to Vehicle.Cabin.IsSeatBeltWarningActive, the vehicle indicator, and not to a seat's IsBelted sensor. Any other multi-actuator or non-VSS command becomes a named action.
- The migrator reads version 1 and version 1.1. In 1.1, each command of an entity's `values`, or a flat `ENTITY.command` key, becomes one write case on the entity's VSS actuator. DOORS lock and unlock become the true and false cases of Vehicle.Cabin.IsCentralLockEngaged. on, off, open and close select true or false on a boolean actuator. Any other command must be an allowed value of the actuator, else it stays unmapped. Commands of an entity outside the vocabulary become named actions ENTITY_COMMAND.
- A 1.1 `encode` becomes an encoded request part `{input: value, type, bytes, endian, scale, offset}`, and min, max and step become write constraints. A vehicle-specific numeric entity becomes an action with an input_schema. Only whole-byte fields convert. Format 2 refuses a target that does not encode to a whole number; the 1.1 runtime rounded it.
- Byte arrays become uppercase spaced hex. A wildcard remains `*`.
- ref: sequences.x becomes call: x, with the endpoint owned by the caller.
- request_id/response_id become tx/rx on a raw CAN endpoint; request-only endpoints omit rx/timeout. response_ids ranges stay `{range: [lo, hi]}`. `extended`, `fd` and `addressing` carry over; addresses become hex bytes.
- can.buses.N becomes channel canN with its bitrate (integer or auto), data_bitrate and fd; a bus that is used but not declared becomes `{protocol: can, configuration: runtime}`. Every declared bus and endpoint is converted, used or not.
- Inline send objects receive a generated request-only endpoint on channel canN with any declared fd.
- A DBC binds to the single bus its monitored messages use, else can0; a monitor on another bus becomes an inline frame binding. Step delay_ms becomes a wait_ms step. Per-step/per-query timeout_ms and `batch` have no format 2 form: timeouts stay unmapped, batch is noted as runtime policy.
- Shared endpoint-free sequences can be converted after their dependencies.
- Declare --framing raw, isotp or isotp-single-frame for request/response migration. No framing is guessed. The last mode validates/removes request PCI and adjusts DBC response offsets for the raw one-byte header.
- Use --responder ENDPOINT=HEX when response IDs are a range, and --steering-side left|right for physical door names.
- Queries translate fixed-length VIN/hex and ordinary DBC decoders, merging with a passive binding on the same property. Known equivalent unit spellings, including `kph` for `km/h`, and supported enum labels are normalized. A kilometer reading on a meter property is scaled by 1000.
- Unknown identities, ambiguous messages, unsupported codecs/multiplexing and incompatible integer/fractional domains stay in unmapped.

The vocabulary is `docs/vocabulary.yaml` in the source repository and is bundled into the wheel. The CLI uses it directly. Original uncertain bindings are preserved in unmapped, never silently discarded. The migrated file alone is not proof of wire equivalence.
