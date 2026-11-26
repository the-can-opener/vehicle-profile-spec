from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class NameKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NAME_KIND_UNSPECIFIED: _ClassVar[NameKind]
    NAME_KIND_PROPERTY: _ClassVar[NameKind]
    NAME_KIND_QUERY: _ClassVar[NameKind]

class ValueKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    VALUE_KIND_UNSPECIFIED: _ClassVar[ValueKind]
    VALUE_KIND_BOOL: _ClassVar[ValueKind]
    VALUE_KIND_INT: _ClassVar[ValueKind]
    VALUE_KIND_UINT: _ClassVar[ValueKind]
    VALUE_KIND_FLOAT: _ClassVar[ValueKind]
    VALUE_KIND_STRING: _ClassVar[ValueKind]

class Acquisition(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACQUISITION_UNSPECIFIED: _ClassVar[Acquisition]
    ACQUISITION_SIGNAL: _ClassVar[Acquisition]
    ACQUISITION_QUERY: _ClassVar[Acquisition]
    ACQUISITION_STATIC: _ClassVar[Acquisition]
    ACQUISITION_HOST: _ClassVar[Acquisition]

class Quality(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    QUALITY_UNSPECIFIED: _ClassVar[Quality]
    QUALITY_VALID: _ClassVar[Quality]
    QUALITY_STALE: _ClassVar[Quality]
    QUALITY_INVALID: _ClassVar[Quality]
    QUALITY_UNAVAILABLE: _ClassVar[Quality]
NAME_KIND_UNSPECIFIED: NameKind
NAME_KIND_PROPERTY: NameKind
NAME_KIND_QUERY: NameKind
VALUE_KIND_UNSPECIFIED: ValueKind
VALUE_KIND_BOOL: ValueKind
VALUE_KIND_INT: ValueKind
VALUE_KIND_UINT: ValueKind
VALUE_KIND_FLOAT: ValueKind
VALUE_KIND_STRING: ValueKind
ACQUISITION_UNSPECIFIED: Acquisition
ACQUISITION_SIGNAL: Acquisition
ACQUISITION_QUERY: Acquisition
ACQUISITION_STATIC: Acquisition
ACQUISITION_HOST: Acquisition
QUALITY_UNSPECIFIED: Quality
QUALITY_VALID: Quality
QUALITY_STALE: Quality
QUALITY_INVALID: Quality
QUALITY_UNAVAILABLE: Quality

class Frame(_message.Message):
    __slots__ = ("dictionary", "batch")
    DICTIONARY_FIELD_NUMBER: _ClassVar[int]
    BATCH_FIELD_NUMBER: _ClassVar[int]
    dictionary: Dictionary
    batch: Batch
    def __init__(self, dictionary: _Optional[_Union[Dictionary, _Mapping]] = ..., batch: _Optional[_Union[Batch, _Mapping]] = ...) -> None: ...

class Quantization(_message.Message):
    __slots__ = ("origin", "scale")
    ORIGIN_FIELD_NUMBER: _ClassVar[int]
    SCALE_FIELD_NUMBER: _ClassVar[int]
    origin: float
    scale: float
    def __init__(self, origin: _Optional[float] = ..., scale: _Optional[float] = ...) -> None: ...

class Constraints(_message.Message):
    __slots__ = ("min", "max", "step")
    MIN_FIELD_NUMBER: _ClassVar[int]
    MAX_FIELD_NUMBER: _ClassVar[int]
    STEP_FIELD_NUMBER: _ClassVar[int]
    min: float
    max: float
    step: float
    def __init__(self, min: _Optional[float] = ..., max: _Optional[float] = ..., step: _Optional[float] = ...) -> None: ...

class SignalSpec(_message.Message):
    __slots__ = ("id", "name", "name_kind", "unit", "value_kind", "source", "acquisition", "clock_domain", "quantization", "constraints", "max_age_ms")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_KIND_FIELD_NUMBER: _ClassVar[int]
    UNIT_FIELD_NUMBER: _ClassVar[int]
    VALUE_KIND_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    ACQUISITION_FIELD_NUMBER: _ClassVar[int]
    CLOCK_DOMAIN_FIELD_NUMBER: _ClassVar[int]
    QUANTIZATION_FIELD_NUMBER: _ClassVar[int]
    CONSTRAINTS_FIELD_NUMBER: _ClassVar[int]
    MAX_AGE_MS_FIELD_NUMBER: _ClassVar[int]
    id: int
    name: str
    name_kind: NameKind
    unit: str
    value_kind: ValueKind
    source: str
    acquisition: Acquisition
    clock_domain: str
    quantization: Quantization
    constraints: Constraints
    max_age_ms: int
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., name_kind: _Optional[_Union[NameKind, str]] = ..., unit: _Optional[str] = ..., value_kind: _Optional[_Union[ValueKind, str]] = ..., source: _Optional[str] = ..., acquisition: _Optional[_Union[Acquisition, str]] = ..., clock_domain: _Optional[str] = ..., quantization: _Optional[_Union[Quantization, _Mapping]] = ..., constraints: _Optional[_Union[Constraints, _Mapping]] = ..., max_age_ms: _Optional[int] = ...) -> None: ...

class Dictionary(_message.Message):
    __slots__ = ("fingerprint", "vehicle_id", "signals", "profile_id", "profile_version", "vss_release")
    FINGERPRINT_FIELD_NUMBER: _ClassVar[int]
    VEHICLE_ID_FIELD_NUMBER: _ClassVar[int]
    SIGNALS_FIELD_NUMBER: _ClassVar[int]
    PROFILE_ID_FIELD_NUMBER: _ClassVar[int]
    PROFILE_VERSION_FIELD_NUMBER: _ClassVar[int]
    VSS_RELEASE_FIELD_NUMBER: _ClassVar[int]
    fingerprint: bytes
    vehicle_id: str
    signals: _containers.RepeatedCompositeFieldContainer[SignalSpec]
    profile_id: str
    profile_version: str
    vss_release: str
    def __init__(self, fingerprint: _Optional[bytes] = ..., vehicle_id: _Optional[str] = ..., signals: _Optional[_Iterable[_Union[SignalSpec, _Mapping]]] = ..., profile_id: _Optional[str] = ..., profile_version: _Optional[str] = ..., vss_release: _Optional[str] = ...) -> None: ...

class Batch(_message.Message):
    __slots__ = ("dictionary_fingerprint", "base_received_ms", "series")
    DICTIONARY_FINGERPRINT_FIELD_NUMBER: _ClassVar[int]
    BASE_RECEIVED_MS_FIELD_NUMBER: _ClassVar[int]
    SERIES_FIELD_NUMBER: _ClassVar[int]
    dictionary_fingerprint: bytes
    base_received_ms: int
    series: _containers.RepeatedCompositeFieldContainer[Series]
    def __init__(self, dictionary_fingerprint: _Optional[bytes] = ..., base_received_ms: _Optional[int] = ..., series: _Optional[_Iterable[_Union[Series, _Mapping]]] = ...) -> None: ...

class QualityRuns(_message.Message):
    __slots__ = ("values", "run_lengths")
    VALUES_FIELD_NUMBER: _ClassVar[int]
    RUN_LENGTHS_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[Quality]
    run_lengths: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, values: _Optional[_Iterable[_Union[Quality, str]]] = ..., run_lengths: _Optional[_Iterable[int]] = ...) -> None: ...

class QuantizedDeltas(_message.Message):
    __slots__ = ("first_step", "step_deltas", "run_lengths")
    FIRST_STEP_FIELD_NUMBER: _ClassVar[int]
    STEP_DELTAS_FIELD_NUMBER: _ClassVar[int]
    RUN_LENGTHS_FIELD_NUMBER: _ClassVar[int]
    first_step: int
    step_deltas: _containers.RepeatedScalarFieldContainer[int]
    run_lengths: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, first_step: _Optional[int] = ..., step_deltas: _Optional[_Iterable[int]] = ..., run_lengths: _Optional[_Iterable[int]] = ...) -> None: ...

class RawDoubles(_message.Message):
    __slots__ = ("values", "run_lengths")
    VALUES_FIELD_NUMBER: _ClassVar[int]
    RUN_LENGTHS_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[float]
    run_lengths: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, values: _Optional[_Iterable[float]] = ..., run_lengths: _Optional[_Iterable[int]] = ...) -> None: ...

class BoolRuns(_message.Message):
    __slots__ = ("initial_value", "run_lengths")
    INITIAL_VALUE_FIELD_NUMBER: _ClassVar[int]
    RUN_LENGTHS_FIELD_NUMBER: _ClassVar[int]
    initial_value: bool
    run_lengths: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, initial_value: _Optional[bool] = ..., run_lengths: _Optional[_Iterable[int]] = ...) -> None: ...

class StringRuns(_message.Message):
    __slots__ = ("values", "run_lengths")
    VALUES_FIELD_NUMBER: _ClassVar[int]
    RUN_LENGTHS_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    run_lengths: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, values: _Optional[_Iterable[str]] = ..., run_lengths: _Optional[_Iterable[int]] = ...) -> None: ...

class Series(_message.Message):
    __slots__ = ("signal_id", "start_sequence", "sample_count", "first_received_delta_ms", "first_interval_ms", "received_dod_ms", "has_observed_at", "observed_offset_ms", "observed_present_bits", "sequence_deltas", "uniform_quality", "quality_runs", "value_present_bits", "quantized", "raw_doubles", "bool_runs", "string_runs")
    SIGNAL_ID_FIELD_NUMBER: _ClassVar[int]
    START_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    SAMPLE_COUNT_FIELD_NUMBER: _ClassVar[int]
    FIRST_RECEIVED_DELTA_MS_FIELD_NUMBER: _ClassVar[int]
    FIRST_INTERVAL_MS_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_DOD_MS_FIELD_NUMBER: _ClassVar[int]
    HAS_OBSERVED_AT_FIELD_NUMBER: _ClassVar[int]
    OBSERVED_OFFSET_MS_FIELD_NUMBER: _ClassVar[int]
    OBSERVED_PRESENT_BITS_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_DELTAS_FIELD_NUMBER: _ClassVar[int]
    UNIFORM_QUALITY_FIELD_NUMBER: _ClassVar[int]
    QUALITY_RUNS_FIELD_NUMBER: _ClassVar[int]
    VALUE_PRESENT_BITS_FIELD_NUMBER: _ClassVar[int]
    QUANTIZED_FIELD_NUMBER: _ClassVar[int]
    RAW_DOUBLES_FIELD_NUMBER: _ClassVar[int]
    BOOL_RUNS_FIELD_NUMBER: _ClassVar[int]
    STRING_RUNS_FIELD_NUMBER: _ClassVar[int]
    signal_id: int
    start_sequence: int
    sample_count: int
    first_received_delta_ms: int
    first_interval_ms: int
    received_dod_ms: _containers.RepeatedScalarFieldContainer[int]
    has_observed_at: bool
    observed_offset_ms: _containers.RepeatedScalarFieldContainer[int]
    observed_present_bits: bytes
    sequence_deltas: _containers.RepeatedScalarFieldContainer[int]
    uniform_quality: Quality
    quality_runs: QualityRuns
    value_present_bits: bytes
    quantized: QuantizedDeltas
    raw_doubles: RawDoubles
    bool_runs: BoolRuns
    string_runs: StringRuns
    def __init__(self, signal_id: _Optional[int] = ..., start_sequence: _Optional[int] = ..., sample_count: _Optional[int] = ..., first_received_delta_ms: _Optional[int] = ..., first_interval_ms: _Optional[int] = ..., received_dod_ms: _Optional[_Iterable[int]] = ..., has_observed_at: _Optional[bool] = ..., observed_offset_ms: _Optional[_Iterable[int]] = ..., observed_present_bits: _Optional[bytes] = ..., sequence_deltas: _Optional[_Iterable[int]] = ..., uniform_quality: _Optional[_Union[Quality, str]] = ..., quality_runs: _Optional[_Union[QualityRuns, _Mapping]] = ..., value_present_bits: _Optional[bytes] = ..., quantized: _Optional[_Union[QuantizedDeltas, _Mapping]] = ..., raw_doubles: _Optional[_Union[RawDoubles, _Mapping]] = ..., bool_runs: _Optional[_Union[BoolRuns, _Mapping]] = ..., string_runs: _Optional[_Union[StringRuns, _Mapping]] = ...) -> None: ...
