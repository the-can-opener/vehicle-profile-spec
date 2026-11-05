# DBC assets

[Overview](../README.md) · [Documentation index](README.md)

## DBC Rules

DBC files decode received CAN payloads only.

Use DBC for:

- passive broadcast frames
- request/response diagnostic replies
- UDS positive responses
- ECU status messages
- sensor values

Do not use DBC for:

- command flows
- multi-step transactions
- security or session setup
- tester-present keepalive
- applicability logic

DBC message IDs must be real CAN response IDs, not invented logical IDs.

```dbc
VERSION ""

BU_: Tester ECU

BO_ 2024 OBD_Response: 8 ECU
 SG_ vehicle_speed : 24|8@1+ (1,0) [0|255] "km/h" Vector__XXX

BO_ 1893 Body_Response: 8 ECU
 SG_ response_service : 8|8@1+ (1,0) [0|255] "" Vector__XXX
 SG_ routine_high     : 16|8@1+ (1,0) [0|255] "" Vector__XXX
 SG_ routine_low      : 24|8@1+ (1,0) [0|255] "" Vector__XXX
 SG_ routine_status   : 32|8@1+ (1,0) [0|255] "" Vector__XXX
```

In this example, `0x7E8` is decimal `2024` and `0x765` is decimal `1893`.


Format 2 lists each DBC under manifest `dbc: {main: {path: signals.dbc, channel: can0}}`; `channel` names the logical bus the messages are received on and defaults to `can0`. A property uses `read.signal: {dbc: main, message: MESSAGE, signal: FIELD}`. The parser supports BO_, ordinary SG_ and VAL_; multiplexed SG_ declarations are rejected. Motorola fields use DBC sawtooth numbering. VAL_ labels are retained for inspection but are never substituted automatically. Use `decode_as: boolean` only for raw 0/1, or an explicit raw-key enum. Units must match VSS exactly; unknown units are not converted.

## Related pages

[Manifest assets](manifest.md) · [Core decoders](decoding.md) · [Shared sources](document.md#shared-sources)
