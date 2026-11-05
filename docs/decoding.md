# Decoding and encoding

[Overview](../README.md) · [Documentation index](README.md)

## Decoding and encoding

Byte decoders use `byte`, `bytes`, `type`, and optional `endian`. Core types: uint, int, ascii, hex. Byte offsets are zero-based; integer endian defaults to big. ASCII is strict; hex results use uppercase without spaces.

Bit decoders use `start_bit`, `bits`, `bit_order` (msb0 or lsb0), and integer type. msb0 counts from the high bit and assembles the first bit as most significant; lsb0 counts from the low bit and assembles the first bit as least significant. These conventions are distinct from DBC Motorola sawtooth notation. DBC adapters use native DBC rules.

For query responses, decode offsets begin AFTER the validated response prefix. Passive frame decoders operate on the entire CAN data field. Validate frame length, responder, response prefix, and minimum payload before decoding.

Order: extraction; invalid_raw handling; enum OR numeric scaling; canonical validation; publication. Scaling is raw × scale + offset, defaulting to 1 and 0. Enum keys are canonical raw-value strings. Unknown enum values and invalid raw encodings produce invalid observations, never zero/false defaults. Enum mapping and scaling cannot coexist.

DBC physical decoding applies factor/offset without automatically substituting `VAL_` labels. `decode_as: boolean` maps raw 0/1 to false/true; other encodings are invalid. Explicit enum mapping is an alternative to physical decoding.

Units and ranges must match VSS. Inline decoder `unit`, if specified, describes the physical result. If absent, the result is in the target property unit. Core 0.4 does not silently convert incompatible units. Shared outputs require compatible semantics and units for all consumers.

A `request` is either a hex string or `parts`, a list that mixes literal hex strings with encoded fields. An encoded field declares `input`, `type`, `bytes`, `endian`, `scale`, and `offset`. Encode raw = (input − offset) / scale, requiring an integral result within the wire width. Do not round, clamp, or overflow silently. More complex codecs require a declared versioned extension.

A `repeat` frame is separate from `parts`. Its mask selects the bits that command owns in one CAN frame. The patch supplies those bits, and every other bit is copied from the latest frame received on that CAN id.

## Related pages

[Read bindings](document.md#passive-signals-and-active-queries) · [Writes](document.md#writes) · [Native DBC decoding](dbc.md)
