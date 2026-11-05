"""Typed format 2 grammar. Raw document entries remain partial until composition."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Positive = Annotated[int, Field(gt=0, strict=True)]
Nonnegative = Annotated[int, Field(ge=0, strict=True)]
Hex = Annotated[str, Field(pattern=r"^[0-9A-F]{2}( [0-9A-F]{2})*$")]
Byte = Annotated[str, Field(pattern=r"^[0-9A-F]{2}$")]
CanID = Annotated[str, Field(pattern=r"^[0-9A-F]{1,8}$")]

# Transport defaults. A missing channel reference names DEFAULT_CHANNEL; a missing
# DEFAULT_CHANNEL declaration is classic CAN at DEFAULT_BITRATE.
DEFAULT_CHANNEL = "can0"
DEFAULT_BITRATE = 500000
MAX_RX_IDS = 1000


Datatype = Annotated[
    str, Field(pattern=r"^(boolean|string|u?int(8|16|32|64)|float|double)(\[\])?$")
]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Pattern(Model):
    prefix: str = Field(pattern=r"^([0-9A-F]{2}|\*)( ([0-9A-F]{2}|\*))*$")
    exact: bool = False
    min_data_bytes: Nonnegative = 0


class Decoder(Model):
    byte: Nonnegative | None = None
    bytes: Positive | None = None
    start_bit: Nonnegative | None = None
    bits: Positive | None = None
    bit_order: Literal["msb0", "lsb0"] | None = None
    type: Literal["uint", "int", "ascii", "hex"]
    endian: Literal["big", "little"] = "big"
    scale: float | None = None
    offset: float | None = None
    enum: dict[str, Any] | None = None
    invalid_raw: list[int] = Field(default_factory=list)
    unit: str | None = None
    datatype: Datatype | None = None

    @model_validator(mode="after")
    def shape(self):
        byte = self.byte is not None and self.bytes is not None
        bit = self.start_bit is not None and self.bits is not None and self.bit_order is not None
        if (
            byte == bit
            or (byte and any(x is not None for x in (self.start_bit, self.bits, self.bit_order)))
            or (bit and any(x is not None for x in (self.byte, self.bytes)))
        ):
            raise ValueError("choose exactly one complete byte or bit decoder")
        if bit and self.type not in ("int", "uint"):
            raise ValueError("bits require an integer type")
        if self.enum is not None and (self.scale is not None or self.offset is not None):
            raise ValueError("enum and scaling are exclusive")
        return self


class EncodedField(Model):
    input: str
    type: Literal["uint", "int"]
    bytes: Positive
    endian: Literal["big", "little"] = "big"
    scale: float = 1
    offset: float = 0

    @model_validator(mode="after")
    def nonzero(self):
        if not self.scale:
            raise ValueError("scale cannot be zero")
        return self


class Parts(Model):
    parts: list[Hex | EncodedField] = Field(min_length=1)


class RequestStep(Model):
    request: Hex | Parts
    expect: Pattern | None = None


class CallStep(Model):
    call: str


class WaitStep(Model):
    wait_ms: Nonnegative


Step = RequestStep | CallStep | WaitStep


class Sequence(Model):
    steps: list[Step] = Field(min_length=1)


class Constraints(Model):
    min: float | None = None
    max: float | None = None
    step: Annotated[float, Field(gt=0)] | None = None

    @model_validator(mode="after")
    def ordered(self):
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min exceeds max")
        return self


class ActionRelease(Model):
    action: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")


class RepeatFrame(Model):
    base: Literal["last-rx"]
    mask: Hex
    patch: Hex

    @model_validator(mode="after")
    def aligned(self):
        from .codec import check_repeat_frame

        check_repeat_frame(self.mask, self.patch)
        return self


class Repeat(Model):
    interval_ms: Positive
    release: Literal["silence"] | ActionRelease
    frame: RepeatFrame


class Body(Model):
    endpoint: str
    request: Hex | Parts | None = None
    expect: Pattern | None = None
    steps: list[Step] | None = Field(default=None, min_length=1)
    deadline_ms: Positive | None = None
    duration: Positive | Literal["latched"] | None = None
    release: ActionRelease | None = None
    repeat: Repeat | None = None

    @model_validator(mode="after")
    def shape(self):
        has_request, has_steps = self.request is not None, self.steps is not None
        has_repeat = self.repeat is not None
        if has_request and (has_steps or has_repeat):
            raise ValueError("DOC_EXCLUSIVE_FORMS: choose request, steps, or repeat")
        if not has_request and not has_steps and not has_repeat:
            raise ValueError("DOC_EXCLUSIVE_FORMS: choose request, steps, or repeat")
        if self.expect is not None and not has_request:
            raise ValueError("expect requires request")
        if has_repeat and (self.duration is not None or self.release is not None):
            raise ValueError("DOC_EXCLUSIVE_FORMS: repeat excludes duration and release")
        return self


class DirectWrite(Body):
    constraints: Constraints | None = None


class CasesWrite(Model):
    cases: dict[str, Body] = Field(min_length=1)
    constraints: Constraints | None = None


class IdRange(Model):
    range: list[CanID] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def ordered(self):
        low, high = (int(x, 16) for x in self.range)
        if low > high:
            raise ValueError("response ID range is reversed")
        if high - low >= MAX_RX_IDS:
            raise ValueError(f"response ID range exceeds {MAX_RX_IDS} IDs")
        return self


def expand_rx(rx):
    """Inclusive receive IDs as integers, in declaration order."""
    result: list[int] = []
    for item in rx:
        if isinstance(item, str):
            result.append(int(item, 16))
        else:
            entry = item["range"] if isinstance(item, dict) else item.range
            result.extend(range(int(entry[0], 16), int(entry[1], 16) + 1))
    return result


class FdFrames(Model):
    tx_dl: Literal[8, 64]


class ExtendedAddressing(Model):
    mode: Literal["extended"]
    target_address: Byte
    source_address: Byte


class MixedAddressing(Model):
    mode: Literal["mixed"]
    address_extension: Byte


Addressing = ExtendedAddressing | MixedAddressing


class Endpoint(Model):
    channel: str = DEFAULT_CHANNEL
    protocol: Literal["can", "isotp"]
    tx: CanID
    rx: list[CanID | IdRange] = Field(default_factory=list)
    id_format: Literal["standard", "extended"]
    timeout_ms: Positive | None = None
    responder: CanID | None = None
    fd: bool | FdFrames | None = None
    addressing: Addressing | None = None

    @model_validator(mode="after")
    def addresses(self):
        limit = 0x7FF if self.id_format == "standard" else 0x1FFFFFFF
        ids = expand_rx(self.rx)
        if any(x > limit for x in [int(self.tx, 16), *ids]):
            raise ValueError("CAN ID outside selected format")
        if len(ids) != len(set(ids)):
            raise ValueError("response IDs overlap")
        if len(ids) > MAX_RX_IDS:
            raise ValueError(f"response IDs exceed {MAX_RX_IDS}")
        if ids and self.timeout_ms is None:
            raise ValueError("response endpoints need timeout_ms")
        if len(ids) > 1 and (self.responder is None or int(self.responder, 16) not in ids):
            raise ValueError("multi-responder endpoints need explicit responder selection")
        if self.protocol == "can":
            if self.addressing is not None:
                raise ValueError("ISO-TP addressing requires protocol isotp")
            if isinstance(self.fd, FdFrames):
                raise ValueError("tx_dl applies to ISO-TP endpoints; raw CAN takes fd true/false")
        return self


class Channel(Model):
    protocol: Literal["can", "canfd"]
    configuration: Literal["runtime"] | None = None
    bitrate: Positive | Literal["auto"] | None = None
    data_bitrate: Positive | None = None
    fd: bool | FdFrames | None = None

    @model_validator(mode="after")
    def configured(self):
        if self.configuration is not None and self.bitrate is not None:
            raise ValueError("DOC_EXCLUSIVE_FORMS: bitrate and runtime configuration")
        if self.protocol == "can" and (self.data_bitrate is not None or self.fd):
            raise ValueError("data_bitrate and fd require protocol canfd")
        return self


def sends_fd(channel, endpoint):
    """Resolved frame format of an endpoint's requests: endpoint fd, then channel fd."""
    for value in (endpoint.get("fd"), channel.get("fd")):
        if value is not None:
            return bool(value)
    return False


class DbcSignal(Model):
    dbc: str
    message: str
    signal: str
    decode_as: Literal["boolean"] | None = None
    enum: dict[str, Any] | None = None

    @model_validator(mode="after")
    def exclusive(self):
        if self.decode_as and self.enum is not None:
            raise ValueError("decode_as and enum are exclusive")
        return self


class InlineSignal(Model):
    channel: str = DEFAULT_CHANNEL
    id: CanID
    id_format: Literal["standard", "extended"]
    length: Annotated[int, Field(ge=0, le=64)]
    decode: Decoder


class SourceRef(Model):
    source: str
    output: str
    decode_as: Literal["boolean"] | None = None
    enum: dict[str, Any] | None = None

    @model_validator(mode="after")
    def exclusive(self):
        if self.decode_as and self.enum is not None:
            raise ValueError("decode_as and enum are exclusive")
        return self


class Query(Model):
    endpoint: str
    request: Hex | Parts
    response: Pattern
    decode: Decoder
    interval_ms: Positive | None = None


class Policy(Model):
    preferred: Literal["signal", "query"] | None = None
    max_age_ms: Nonnegative | None = None
    active_fallback: bool = False


class Read(Model):
    signal: DbcSignal | InlineSignal | SourceRef | None = None
    query: Query | SourceRef | None = None
    policy: Policy | None = None

    @model_validator(mode="before")
    @classmethod
    def exclusive_forms(cls, data):
        if isinstance(data, dict):
            for kind, keys in [
                ("signal", ("dbc", "channel", "source")),
                ("query", ("endpoint", "source")),
            ]:
                binding = data.get(kind)
                if isinstance(binding, dict) and sum(key in binding for key in keys) > 1:
                    raise ValueError("DOC_EXCLUSIVE_FORMS: choose one read binding form")
        return data

    @model_validator(mode="after")
    def present(self):
        if self.signal is None and self.query is None:
            raise ValueError("read needs a binding")
        if self.policy and self.policy.preferred and getattr(self, self.policy.preferred) is None:
            raise ValueError("preferred binding is missing")
        return self


class Property(Model):
    aliases: list[str] = Field(default_factory=list)
    read: Read | None = None
    write: DirectWrite | CasesWrite | None = None
    value: Any = None

    @model_validator(mode="before")
    @classmethod
    def write_forms(cls, data):
        if isinstance(data, dict) and isinstance(data.get("write"), dict):
            write = data["write"]
            forms = [key for key in ("request", "steps", "cases", "repeat") if key in write]
            if (
                not forms
                or ("cases" in forms and forms != ["cases"])
                or ("request" in forms and ("steps" in forms or "repeat" in forms))
            ):
                raise ValueError("DOC_EXCLUSIVE_FORMS: choose one write form")
        return data

    @model_validator(mode="after")
    def exclusive(self):
        if "value" in self.model_fields_set and self.value is None:
            raise ValueError("static null is not a VSS value")
        if any(getattr(self, k) is None for k in self.model_fields_set & {"read", "write"}):
            raise ValueError("null bindings are not capabilities")
        if "value" in self.model_fields_set and self.read is not None:
            raise ValueError("DOC_EXCLUSIVE_FORMS: value and read")
        if not self.model_fields_set.intersection({"read", "write", "value"}):
            raise ValueError("property needs a binding or value")
        return self


class DbcSource(Model):
    kind: Literal["signal"]
    dbc: str
    message: str


class SignalSource(Model):
    kind: Literal["signal"]
    channel: str = DEFAULT_CHANNEL
    id: CanID
    id_format: Literal["standard", "extended"]
    length: Annotated[int, Field(ge=0, le=64)]
    outputs: dict[str, Decoder] = Field(min_length=1)


class QuerySource(Model):
    kind: Literal["query"]
    endpoint: str
    request: Hex | Parts
    response: Pattern
    interval_ms: Positive | None = None
    outputs: dict[str, Decoder] = Field(min_length=1)


class NamedQuery(Model):
    description: str
    endpoint: str
    request: Hex | Parts
    response: Pattern
    decode: Decoder | None = None
    datatype: Datatype | None = None
    unit: str | None = None
    outputs: dict[str, Decoder] | None = None
    interval_ms: Positive | None = None
    input_schema: dict[str, Any] | None = None

    @model_validator(mode="after")
    def shape(self):
        if (self.decode is None) == (self.outputs is None):
            raise ValueError("choose decode or outputs")
        if self.decode and not self.datatype:
            raise ValueError("named query needs datatype")
        if self.outputs and any(not d.datatype for d in self.outputs.values()):
            raise ValueError("named query outputs need datatype")
        return self


class Action(Body):
    description: str
    retry: Literal["never", "idempotent"] = "never"
    input_schema: dict[str, Any] | None = None


class DocumentRaw(Model):
    applies_to: dict[str, Any] = Field(default_factory=dict)
    channels: dict[str, Any] = Field(default_factory=dict)
    endpoints: dict[str, Any] = Field(default_factory=dict)
    sources: dict[str, Any] = Field(default_factory=dict)
    properties: dict[str, Any] = Field(default_factory=dict)
    sequences: dict[str, Any] = Field(default_factory=dict)
    queries: dict[str, Any] = Field(default_factory=dict)
    actions: dict[str, Any] = Field(default_factory=dict)
    requires: dict[str, str] = Field(default_factory=dict)
    extensions: dict[str, Any] = Field(default_factory=dict)


class Document(DocumentRaw):
    channels: dict[str, Channel] = Field(default_factory=dict)
    endpoints: dict[str, Endpoint] = Field(default_factory=dict)
    sources: dict[str, DbcSource | SignalSource | QuerySource] = Field(default_factory=dict)
    properties: dict[str, Property] = Field(default_factory=dict)
    sequences: dict[str, Sequence] = Field(default_factory=dict)
    queries: dict[str, NamedQuery] = Field(default_factory=dict)
    actions: dict[str, Action] = Field(default_factory=dict)


class Frame(Model):
    id: CanID
    data: Hex
    id_format: Literal["standard", "extended"] | None = None


class FixtureExpectation(Model):
    value: Any = None
    quality: Literal["valid", "stale", "invalid", "unavailable"] | None = None
    sent: list[Hex] | None = None
    result: (
        Literal[
            "sent",
            "acknowledged",
            "accepted",
            "running",
            "succeeded",
            "failed",
            "cancelled",
            "unknown",
        ]
        | None
    ) = None
    error: str | None = None


class FixtureCase(Model):
    label: str | None = None
    kind: Literal["signal", "query", "write", "action"]
    path: str | None = None
    name: str | None = None
    frame: Frame | None = None
    responses: list[Hex | Frame] | None = None
    target: Any = None
    input: dict[str, Any] | None = None
    expect: FixtureExpectation

    @model_validator(mode="after")
    def target_shape(self):
        if (self.path is None) == (self.name is None):
            raise ValueError("use exactly one path or name; label describes the test")
        if self.kind in ("signal", "write") and self.path is None:
            raise ValueError("signal/write requires path")
        if self.kind == "write" and "target" not in self.model_fields_set:
            raise ValueError("write fixture requires target")
        if self.kind == "action" and self.name is None:
            raise ValueError("action requires name")
        return self


class Fixture(Model):
    fixture: Literal[1]
    cases: list[FixtureCase]
