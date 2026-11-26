"""Compressed columnar protobuf telemetry codec and .vts/.zip container I/O."""

from __future__ import annotations

import hashlib
import io
import json
import math
import struct
import zipfile
import zlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from fractions import Fraction
from pathlib import Path
from typing import Any, BinaryIO

from . import telemetry_pb2
from .catalog import load_catalog, numeric_limits
from .codec import check_constraints

VTS_MAGIC = b"VTS1"
FLAG_RAW = 0x00
FLAG_ZLIB = 0x01
ZIP_MAGIC = b"PK\x03\x04"

_MAX_SINT64 = (1 << 63) - 1
_MIN_SINT64 = -(1 << 63)


class TelemetryError(ValueError):
    """Raised when telemetry encoding, decoding, or validation fails."""


class NameKind(StrEnum):
    PROPERTY = "property"
    QUERY = "query"


class ValueKind(StrEnum):
    BOOL = "bool"
    INT = "int"
    UINT = "uint"
    FLOAT = "float"
    STRING = "string"


class Acquisition(StrEnum):
    SIGNAL = "signal"
    QUERY = "query"
    STATIC = "static"
    HOST = "host"


class Quality(StrEnum):
    VALID = "valid"
    STALE = "stale"
    INVALID = "invalid"
    UNAVAILABLE = "unavailable"


_NAME_KIND_TO_PB = {
    NameKind.PROPERTY: telemetry_pb2.NAME_KIND_PROPERTY,
    NameKind.QUERY: telemetry_pb2.NAME_KIND_QUERY,
}
_PB_TO_NAME_KIND = {v: k for k, v in _NAME_KIND_TO_PB.items()}

_VALUE_KIND_TO_PB = {
    ValueKind.BOOL: telemetry_pb2.VALUE_KIND_BOOL,
    ValueKind.INT: telemetry_pb2.VALUE_KIND_INT,
    ValueKind.UINT: telemetry_pb2.VALUE_KIND_UINT,
    ValueKind.FLOAT: telemetry_pb2.VALUE_KIND_FLOAT,
    ValueKind.STRING: telemetry_pb2.VALUE_KIND_STRING,
}
_PB_TO_VALUE_KIND = {v: k for k, v in _VALUE_KIND_TO_PB.items()}

_ACQUISITION_TO_PB = {
    Acquisition.SIGNAL: telemetry_pb2.ACQUISITION_SIGNAL,
    Acquisition.QUERY: telemetry_pb2.ACQUISITION_QUERY,
    Acquisition.STATIC: telemetry_pb2.ACQUISITION_STATIC,
    Acquisition.HOST: telemetry_pb2.ACQUISITION_HOST,
}
_PB_TO_ACQUISITION = {v: k for k, v in _ACQUISITION_TO_PB.items()}

_QUALITY_TO_PB = {
    Quality.VALID: telemetry_pb2.QUALITY_VALID,
    Quality.STALE: telemetry_pb2.QUALITY_STALE,
    Quality.INVALID: telemetry_pb2.QUALITY_INVALID,
    Quality.UNAVAILABLE: telemetry_pb2.QUALITY_UNAVAILABLE,
}
_PB_TO_QUALITY = {v: k for k, v in _QUALITY_TO_PB.items()}


@dataclass(frozen=True)
class Quantization:
    origin: float = 0.0
    scale: float = 1.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.origin) or not math.isfinite(self.scale) or self.scale <= 0:
            raise TelemetryError("quantization scale must be finite and positive")


@dataclass(frozen=True)
class Constraints:
    min: float | None = None
    max: float | None = None
    step: float | None = None

    def as_dict(self) -> dict[str, float]:
        result: dict[str, float] = {}
        if self.min is not None:
            result["min"] = self.min
        if self.max is not None:
            result["max"] = self.max
        if self.step is not None:
            result["step"] = self.step
        return result


@dataclass(frozen=True)
class SignalSpec:
    id: int
    name: str
    name_kind: NameKind = NameKind.PROPERTY
    unit: str = ""
    value_kind: ValueKind = ValueKind.FLOAT
    source: str = ""
    acquisition: Acquisition = Acquisition.SIGNAL
    clock_domain: str = "host-utc"
    quantization: Quantization | None = None
    constraints: Constraints | None = None
    max_age_ms: int = 0


@dataclass(frozen=True)
class Dictionary:
    vehicle_id: str
    signals: tuple[SignalSpec, ...]
    profile_id: str = ""
    profile_version: str = ""
    vss_release: str = "6.1"
    fingerprint: bytes = b""

    def __post_init__(self) -> None:
        seen_ids: set[int] = set()
        for spec in self.signals:
            if spec.id in seen_ids:
                raise TelemetryError(f"duplicate signal id: {spec.id}")
            seen_ids.add(spec.id)
        expected = compute_fingerprint(
            self.vehicle_id,
            self.signals,
            self.profile_id,
            self.profile_version,
            self.vss_release,
        )
        if not self.fingerprint:
            object.__setattr__(self, "fingerprint", expected)
        elif self.fingerprint != expected:
            raise TelemetryError("dictionary fingerprint does not match canonical contents")

    def by_id(self, signal_id: int) -> SignalSpec:
        for spec in self.signals:
            if spec.id == signal_id:
                return spec
        raise TelemetryError(f"unknown signal id: {signal_id}")

    def resolve_signal(self, name: str, source: str = "") -> SignalSpec:
        exact = [s for s in self.signals if s.name == name and (not source or s.source == source)]
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            raise TelemetryError(f"ambiguous signal {name!r}; specify source")
        by_name = [s for s in self.signals if s.name == name]
        if len(by_name) == 1 and not source:
            return by_name[0]
        raise TelemetryError(f"signal not found in dictionary: {name!r} (source={source!r})")


@dataclass(frozen=True)
class Observation:
    name: str
    received_at_ms: int
    value: bool | int | float | str | None = None
    quality: Quality = Quality.VALID
    name_kind: NameKind = NameKind.PROPERTY
    unit: str = ""
    source: str = ""
    acquisition: Acquisition = Acquisition.SIGNAL
    observed_at_ms: int | None = None
    clock_domain: str = "host-utc"
    sequence: int = 0

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "name_kind": self.name_kind.value,
            "quality": self.quality.value,
            "source": self.source,
            "acquisition": self.acquisition.value,
            "received_at_ms": self.received_at_ms,
            "receivedAt": format_rfc3339_ms(self.received_at_ms),
            "clock_domain": self.clock_domain,
            "sequence": self.sequence,
        }
        if self.unit:
            payload["unit"] = self.unit
        if self.value is not None:
            payload["value"] = self.value
        if self.observed_at_ms is not None:
            payload["observed_at_ms"] = self.observed_at_ms
            payload["observedAt"] = format_rfc3339_ms(self.observed_at_ms)
        return payload

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Observation:
        if "received_at_ms" in raw:
            received_ms = int(raw["received_at_ms"])
        elif "receivedAt" in raw:
            received_ms = parse_rfc3339_ms(raw["receivedAt"])
        else:
            raise TelemetryError("observation requires received_at_ms or receivedAt")

        observed_ms: int | None = None
        if raw.get("observed_at_ms") is not None:
            observed_ms = int(raw["observed_at_ms"])
        elif raw.get("observedAt") is not None:
            observed_ms = parse_rfc3339_ms(raw["observedAt"])

        return cls(
            name=str(raw["name"]),
            received_at_ms=received_ms,
            value=raw.get("value"),
            quality=Quality(raw.get("quality", Quality.VALID.value)),
            name_kind=NameKind(raw.get("name_kind", NameKind.PROPERTY.value)),
            unit=str(raw.get("unit", "")),
            source=str(raw.get("source", "")),
            acquisition=Acquisition(raw.get("acquisition", Acquisition.SIGNAL.value)),
            observed_at_ms=observed_ms,
            clock_domain=str(raw.get("clock_domain", "host-utc")),
            sequence=int(raw.get("sequence", 0)),
        )


def format_rfc3339_ms(epoch_ms: int) -> str:
    sec, ms = divmod(epoch_ms, 1000)
    dt = datetime.fromtimestamp(sec, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{ms:03d}Z"


def parse_rfc3339_ms(value: str) -> int:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return round(dt.timestamp() * 1000)


def compute_fingerprint(
    vehicle_id: str,
    signals: Sequence[SignalSpec],
    profile_id: str = "",
    profile_version: str = "",
    vss_release: str = "6.1",
) -> bytes:
    canonical = {
        "vehicle_id": vehicle_id,
        "profile_id": profile_id,
        "profile_version": profile_version,
        "vss_release": vss_release,
        "signals": [
            {
                "id": s.id,
                "name": s.name,
                "name_kind": s.name_kind.value,
                "unit": s.unit,
                "value_kind": s.value_kind.value,
                "source": s.source,
                "acquisition": s.acquisition.value,
                "clock_domain": s.clock_domain,
                "quantization": (
                    {"origin": s.quantization.origin, "scale": s.quantization.scale}
                    if s.quantization
                    else None
                ),
                "constraints": s.constraints.as_dict() if s.constraints else None,
                "max_age_ms": s.max_age_ms,
            }
            for s in sorted(signals, key=lambda item: item.id)
        ],
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).digest()


def _datatype_to_value_kind(datatype: str) -> ValueKind:
    if datatype == "boolean":
        return ValueKind.BOOL
    if datatype == "string":
        return ValueKind.STRING
    if datatype.startswith("uint"):
        return ValueKind.UINT
    if datatype.startswith("int"):
        return ValueKind.INT
    if datatype in ("float", "double"):
        return ValueKind.FLOAT
    raise TelemetryError(f"unsupported scalar datatype for telemetry: {datatype!r}")


_HOST_GNSS_SPECS: tuple[
    tuple[str, ValueKind, str, Quantization | None, Constraints | None], ...
] = (
    (
        "Vehicle.CurrentLocation.Latitude",
        ValueKind.FLOAT,
        "degrees",
        Quantization(0.0, 1e-7),
        Constraints(min=-90.0, max=90.0),
    ),
    (
        "Vehicle.CurrentLocation.Longitude",
        ValueKind.FLOAT,
        "degrees",
        Quantization(0.0, 1e-7),
        Constraints(min=-180.0, max=180.0),
    ),
    (
        "Vehicle.CurrentLocation.Altitude",
        ValueKind.FLOAT,
        "m",
        Quantization(0.0, 1e-3),
        None,
    ),
    (
        "Vehicle.CurrentLocation.Heading",
        ValueKind.FLOAT,
        "degrees",
        Quantization(0.0, 1e-2),
        Constraints(min=0.0, max=360.0),
    ),
    (
        "Vehicle.CurrentLocation.HorizontalAccuracy",
        ValueKind.FLOAT,
        "m",
        Quantization(0.0, 1e-3),
        Constraints(min=0.0),
    ),
    (
        "Vehicle.CurrentLocation.VerticalAccuracy",
        ValueKind.FLOAT,
        "m",
        Quantization(0.0, 1e-3),
        Constraints(min=0.0),
    ),
    (
        "Vehicle.CurrentLocation.GNSSReceiver.FixType",
        ValueKind.STRING,
        "",
        None,
        None,
    ),
)

_HOST_IMU_SPECS: tuple[tuple[str, ValueKind, str, Quantization | None, Constraints | None], ...] = (
    (
        "Vehicle.Acceleration.Longitudinal",
        ValueKind.FLOAT,
        "m/s^2",
        Quantization(0.0, 1e-3),
        None,
    ),
    (
        "Vehicle.Acceleration.Lateral",
        ValueKind.FLOAT,
        "m/s^2",
        Quantization(0.0, 1e-3),
        None,
    ),
    (
        "Vehicle.Acceleration.Vertical",
        ValueKind.FLOAT,
        "m/s^2",
        Quantization(0.0, 1e-3),
        None,
    ),
    (
        "Vehicle.AngularVelocity.Roll",
        ValueKind.FLOAT,
        "degrees/s",
        Quantization(0.0, 1e-2),
        None,
    ),
    (
        "Vehicle.AngularVelocity.Pitch",
        ValueKind.FLOAT,
        "degrees/s",
        Quantization(0.0, 1e-2),
        None,
    ),
    (
        "Vehicle.AngularVelocity.Yaw",
        ValueKind.FLOAT,
        "degrees/s",
        Quantization(0.0, 1e-2),
        None,
    ),
    (
        "Vehicle.Orientation.Roll",
        ValueKind.FLOAT,
        "degrees",
        Quantization(0.0, 1e-2),
        None,
    ),
    (
        "Vehicle.Orientation.Pitch",
        ValueKind.FLOAT,
        "degrees",
        Quantization(0.0, 1e-2),
        None,
    ),
    (
        "Vehicle.Orientation.Yaw",
        ValueKind.FLOAT,
        "degrees",
        Quantization(0.0, 1e-2),
        None,
    ),
)

_HOST_DEFAULT_QUANTIZATION: dict[str, Quantization] = {
    name: quant for name, _, _, quant, _ in (*_HOST_GNSS_SPECS, *_HOST_IMU_SPECS) if quant
}
_HOST_DEFAULT_QUANTIZATION["Vehicle.Speed"] = Quantization(0.0, 1e-2)


def host_gnss_signals(
    *,
    source: str = "host.gnss",
    clock_domain: str = "gnss-utc",
    include_speed: bool = False,
    start_id: int = 1,
) -> list[SignalSpec]:
    specs: list[SignalSpec] = []
    next_id = start_id
    for name, vkind, unit, quant, constraints in _HOST_GNSS_SPECS:
        specs.append(
            SignalSpec(
                id=next_id,
                name=name,
                name_kind=NameKind.PROPERTY,
                unit=unit,
                value_kind=vkind,
                source=source,
                acquisition=Acquisition.HOST,
                clock_domain=clock_domain,
                quantization=quant,
                constraints=constraints,
            )
        )
        next_id += 1
    if include_speed:
        specs.append(
            SignalSpec(
                id=next_id,
                name="Vehicle.Speed",
                name_kind=NameKind.PROPERTY,
                unit="km/h",
                value_kind=ValueKind.FLOAT,
                source=source,
                acquisition=Acquisition.HOST,
                clock_domain=clock_domain,
                quantization=Quantization(0.0, 1e-2),
                constraints=Constraints(min=0.0),
            )
        )
    return specs


def host_imu_signals(
    *,
    source: str = "host.imu",
    clock_domain: str = "host-utc",
    start_id: int = 1,
) -> list[SignalSpec]:
    specs: list[SignalSpec] = []
    next_id = start_id
    for name, vkind, unit, quant, constraints in _HOST_IMU_SPECS:
        specs.append(
            SignalSpec(
                id=next_id,
                name=name,
                name_kind=NameKind.PROPERTY,
                unit=unit,
                value_kind=vkind,
                source=source,
                acquisition=Acquisition.HOST,
                clock_domain=clock_domain,
                quantization=quant,
                constraints=constraints,
            )
        )
        next_id += 1
    return specs


def host_sensor_signals(
    *,
    gnss_source: str = "host.gnss",
    imu_source: str = "host.imu",
    include_gnss_speed: bool = False,
    start_id: int = 1,
) -> list[SignalSpec]:
    gnss = host_gnss_signals(
        source=gnss_source, include_speed=include_gnss_speed, start_id=start_id
    )
    imu = host_imu_signals(source=imu_source, start_id=start_id + len(gnss))
    return [*gnss, *imu]


def _signal_source_label(binding: dict[str, Any]) -> str:
    if "dbc" in binding:
        return f"dbc:{binding['dbc']}:{binding['message']}.{binding['signal']}"
    if "source" in binding:
        return f"source:{binding['source']}.{binding['output']}"
    channel = binding.get("channel", "can0")
    return f"{channel}:{binding['id']}"


def _query_source_label(binding: dict[str, Any]) -> str:
    if "source" in binding:
        return f"source:{binding['source']}.{binding['output']}"
    return f"query:{binding['endpoint']}"


def build_dictionary(
    vehicle_id: str,
    *,
    document: dict[str, Any] | None = None,
    extra_signals: Sequence[SignalSpec] = (),
    include_host_sensors: bool = False,
    include_gnss_speed: bool = False,
    clock_domain: str = "host-utc",
) -> Dictionary:
    """Build a canonical Dictionary from a resolved vehicle profile and optional host signals."""
    vss_release = (document or {}).get("vss", "6.1")
    catalog = load_catalog(vss_release)
    signals: list[SignalSpec] = []
    next_id = 1

    if document is not None:
        for path, prop in sorted(document.get("properties", {}).items()):
            entry = catalog.get(path)
            if entry is None:
                continue
            dtype = entry.get("datatype", "")
            if dtype.endswith("[]"):
                continue
            vkind = _datatype_to_value_kind(dtype)
            unit = entry.get("unit", "")
            limits = numeric_limits(entry)

            read = prop.get("read")
            if read:
                read_constraints = read.get("constraints") or {}
                merged_min = read_constraints.get("min", limits.get("min"))
                merged_max = read_constraints.get("max", limits.get("max"))
                step = read_constraints.get("step")
                constraints = (
                    Constraints(min=merged_min, max=merged_max, step=step)
                    if (merged_min is not None or merged_max is not None or step is not None)
                    else None
                )
                quant = (
                    Quantization(origin=float(merged_min or 0.0), scale=float(step))
                    if step is not None
                    else None
                )
                max_age_ms = int((read.get("policy") or {}).get("max_age_ms") or 0)

                if "signal" in read:
                    signals.append(
                        SignalSpec(
                            id=next_id,
                            name=path,
                            name_kind=NameKind.PROPERTY,
                            unit=unit,
                            value_kind=vkind,
                            source=_signal_source_label(read["signal"]),
                            acquisition=Acquisition.SIGNAL,
                            clock_domain=clock_domain,
                            quantization=quant,
                            constraints=constraints,
                            max_age_ms=max_age_ms,
                        )
                    )
                    next_id += 1
                if "query" in read:
                    signals.append(
                        SignalSpec(
                            id=next_id,
                            name=path,
                            name_kind=NameKind.PROPERTY,
                            unit=unit,
                            value_kind=vkind,
                            source=_query_source_label(read["query"]),
                            acquisition=Acquisition.QUERY,
                            clock_domain=clock_domain,
                            quantization=quant,
                            constraints=constraints,
                            max_age_ms=max_age_ms,
                        )
                    )
                    next_id += 1
            elif "value" in prop:
                signals.append(
                    SignalSpec(
                        id=next_id,
                        name=path,
                        name_kind=NameKind.PROPERTY,
                        unit=unit,
                        value_kind=vkind,
                        source="static",
                        acquisition=Acquisition.STATIC,
                        clock_domain=clock_domain,
                    )
                )
                next_id += 1

        for qname, query in sorted(document.get("queries", {}).items()):
            endpoint = query.get("endpoint", "")
            if "outputs" in query:
                for out_name, out_spec in sorted(query["outputs"].items()):
                    dtype = out_spec.get("datatype", "")
                    if dtype.endswith("[]"):
                        continue
                    signals.append(
                        SignalSpec(
                            id=next_id,
                            name=f"{qname}.{out_name}",
                            name_kind=NameKind.QUERY,
                            unit=out_spec.get("unit", ""),
                            value_kind=_datatype_to_value_kind(dtype),
                            source=f"query:{endpoint}",
                            acquisition=Acquisition.QUERY,
                            clock_domain=clock_domain,
                        )
                    )
                    next_id += 1
            elif "datatype" in query and not query["datatype"].endswith("[]"):
                signals.append(
                    SignalSpec(
                        id=next_id,
                        name=qname,
                        name_kind=NameKind.QUERY,
                        unit=query.get("unit", ""),
                        value_kind=_datatype_to_value_kind(query["datatype"]),
                        source=f"query:{endpoint}",
                        acquisition=Acquisition.QUERY,
                        clock_domain=clock_domain,
                    )
                )
                next_id += 1

    existing_keys = {(s.name, s.source) for s in signals}
    appended: list[SignalSpec] = []
    if include_host_sensors:
        appended.extend(host_sensor_signals(include_gnss_speed=include_gnss_speed))
    appended.extend(extra_signals)

    for spec in appended:
        key = (spec.name, spec.source)
        if key in existing_keys:
            continue
        existing_keys.add(key)
        signals.append(
            SignalSpec(
                id=next_id,
                name=spec.name,
                name_kind=spec.name_kind,
                unit=spec.unit,
                value_kind=spec.value_kind,
                source=spec.source,
                acquisition=spec.acquisition,
                clock_domain=spec.clock_domain,
                quantization=spec.quantization,
                constraints=spec.constraints,
                max_age_ms=spec.max_age_ms,
            )
        )
        next_id += 1

    return Dictionary(
        vehicle_id=vehicle_id,
        signals=tuple(signals),
        profile_id=str((document or {}).get("id", "")),
        profile_version=str((document or {}).get("version", "")),
        vss_release=vss_release,
    )


def infer_dictionary(
    vehicle_id: str,
    observations: Sequence[Observation],
    *,
    vss_release: str = "6.1",
) -> Dictionary:
    """Infer a Dictionary directly from observations when no vehicle profile is supplied."""
    catalog = load_catalog(vss_release)
    seen: dict[tuple[str, str], SignalSpec] = {}
    next_id = 1
    for obs in observations:
        key = (obs.name, obs.source)
        if key in seen:
            continue
        entry = catalog.get(obs.name)
        unit = obs.unit or (entry.get("unit", "") if entry else "")
        constraints: Constraints | None = None
        if entry is not None and not entry.get("datatype", "").endswith("[]"):
            vkind = _datatype_to_value_kind(entry["datatype"])
            limits = numeric_limits(entry)
            if limits:
                constraints = Constraints(min=limits.get("min"), max=limits.get("max"))
        else:
            vkind = _infer_value_kind(obs.value)
        quant = _HOST_DEFAULT_QUANTIZATION.get(obs.name) if vkind == ValueKind.FLOAT else None
        seen[key] = SignalSpec(
            id=next_id,
            name=obs.name,
            name_kind=obs.name_kind,
            unit=unit,
            value_kind=vkind,
            source=obs.source,
            acquisition=obs.acquisition,
            clock_domain=obs.clock_domain,
            quantization=quant,
            constraints=constraints,
        )
        next_id += 1
    return Dictionary(
        vehicle_id=vehicle_id,
        signals=tuple(seen.values()),
        vss_release=vss_release,
    )


def _infer_value_kind(value: Any) -> ValueKind:
    if isinstance(value, bool):
        return ValueKind.BOOL
    if isinstance(value, int):
        return ValueKind.INT
    if isinstance(value, str):
        return ValueKind.STRING
    return ValueKind.FLOAT


def dictionary_to_pb(dictionary: Dictionary) -> telemetry_pb2.Dictionary:
    pb = telemetry_pb2.Dictionary(
        fingerprint=dictionary.fingerprint,
        vehicle_id=dictionary.vehicle_id,
        profile_id=dictionary.profile_id,
        profile_version=dictionary.profile_version,
        vss_release=dictionary.vss_release,
    )
    for spec in dictionary.signals:
        sig_pb = pb.signals.add(
            id=spec.id,
            name=spec.name,
            name_kind=_NAME_KIND_TO_PB[spec.name_kind],
            unit=spec.unit,
            value_kind=_VALUE_KIND_TO_PB[spec.value_kind],
            source=spec.source,
            acquisition=_ACQUISITION_TO_PB[spec.acquisition],
            clock_domain=spec.clock_domain,
            max_age_ms=spec.max_age_ms,
        )
        if spec.quantization is not None:
            sig_pb.quantization.origin = spec.quantization.origin
            sig_pb.quantization.scale = spec.quantization.scale
        if spec.constraints is not None:
            if spec.constraints.min is not None:
                sig_pb.constraints.min = spec.constraints.min
            if spec.constraints.max is not None:
                sig_pb.constraints.max = spec.constraints.max
            if spec.constraints.step is not None:
                sig_pb.constraints.step = spec.constraints.step
    return pb


def dictionary_from_pb(pb: telemetry_pb2.Dictionary) -> Dictionary:
    signals: list[SignalSpec] = []
    for sig_pb in pb.signals:
        quant: Quantization | None = None
        if sig_pb.HasField("quantization"):
            quant = Quantization(origin=sig_pb.quantization.origin, scale=sig_pb.quantization.scale)
        constraints: Constraints | None = None
        if sig_pb.HasField("constraints"):
            c_pb = sig_pb.constraints
            constraints = Constraints(
                min=c_pb.min if c_pb.HasField("min") else None,
                max=c_pb.max if c_pb.HasField("max") else None,
                step=c_pb.step if c_pb.HasField("step") else None,
            )
        signals.append(
            SignalSpec(
                id=sig_pb.id,
                name=sig_pb.name,
                name_kind=_PB_TO_NAME_KIND[sig_pb.name_kind],
                unit=sig_pb.unit,
                value_kind=_PB_TO_VALUE_KIND[sig_pb.value_kind],
                source=sig_pb.source,
                acquisition=_PB_TO_ACQUISITION[sig_pb.acquisition],
                clock_domain=sig_pb.clock_domain,
                quantization=quant,
                constraints=constraints,
                max_age_ms=sig_pb.max_age_ms,
            )
        )
    return Dictionary(
        vehicle_id=pb.vehicle_id,
        signals=tuple(signals),
        profile_id=pb.profile_id,
        profile_version=pb.profile_version,
        vss_release=pb.vss_release or "6.1",
        fingerprint=bytes(pb.fingerprint),
    )


def _pack_bitset(bits: Sequence[bool]) -> bytes:
    buf = bytearray((len(bits) + 7) // 8)
    for idx, flag in enumerate(bits):
        if flag:
            buf[idx >> 3] |= 1 << (idx & 7)
    return bytes(buf)


def _unpack_bitset(data: bytes, count: int) -> list[bool]:
    return [bool((data[idx >> 3] >> (idx & 7)) & 1) for idx in range(count)]


def _validate_and_prepare_value(
    obs: Observation,
    spec: SignalSpec,
    *,
    downgrade_invalid: bool,
) -> tuple[Quality, bool | int | float | str | None]:
    if obs.quality in (Quality.INVALID, Quality.UNAVAILABLE):
        return obs.quality, None

    val = obs.value
    if val is None:
        if obs.quality == Quality.STALE:
            return Quality.STALE, None
        if downgrade_invalid:
            return Quality.INVALID, None
        raise TelemetryError(f"{spec.name}: VALID observation requires a value")

    try:
        if spec.value_kind == ValueKind.BOOL:
            if type(val) is not bool:
                raise TelemetryError(f"{spec.name}: expected boolean, got {type(val).__name__}")
            return obs.quality, val
        if spec.value_kind == ValueKind.STRING:
            if not isinstance(val, str):
                raise TelemetryError(f"{spec.name}: expected string, got {type(val).__name__}")
            return obs.quality, val
        if type(val) is bool or not isinstance(val, (int, float)):
            raise TelemetryError(f"{spec.name}: expected numeric value, got {type(val).__name__}")
        if not math.isfinite(float(val)):
            raise TelemetryError(f"{spec.name}: value must be finite")
        if spec.value_kind in (ValueKind.INT, ValueKind.UINT):
            if isinstance(val, float) and not val.is_integer():
                raise TelemetryError(f"{spec.name}: expected integer value, got {val}")
            ival = int(val)
            if spec.value_kind == ValueKind.UINT and ival < 0:
                raise TelemetryError(f"{spec.name}: unsigned integer cannot be negative")
            if spec.constraints is not None:
                check_constraints(ival, spec.constraints.as_dict())
            return obs.quality, ival
        # FLOAT
        if spec.constraints is not None:
            check_constraints(val, spec.constraints.as_dict())
        return obs.quality, float(val)
    except ValueError as exc:
        if downgrade_invalid:
            return Quality.INVALID, None
        raise TelemetryError(f"{spec.name}: {exc}") from exc


def _quantize_step(value: int | float, spec: SignalSpec) -> int:
    if spec.quantization is None:
        return int(value)
    origin = Fraction(Decimal(str(spec.quantization.origin)))
    scale = Fraction(Decimal(str(spec.quantization.scale)))
    ratio = (Fraction(Decimal(str(value))) - origin) / scale
    if spec.constraints is not None and spec.constraints.step is not None:
        if ratio.denominator != 1:
            raise TelemetryError(f"{spec.name}: value {value} is off quantization grid")
        return int(ratio)
    return round(float(ratio))


def _dequantize_step(step: int, spec: SignalSpec) -> int | float:
    if spec.quantization is None:
        return int(step)
    dec = Decimal(str(spec.quantization.origin)) + Decimal(step) * Decimal(
        str(spec.quantization.scale)
    )
    if spec.value_kind in (ValueKind.INT, ValueKind.UINT) and dec == dec.to_integral_value():
        return int(dec)
    return float(dec)


def _canonical_eq_key(
    quality: Quality,
    value: bool | int | float | str | None,
    spec: SignalSpec,
) -> Any:
    if value is None:
        return (quality, None)
    if spec.value_kind in (ValueKind.INT, ValueKind.UINT) or (
        spec.value_kind == ValueKind.FLOAT and spec.quantization is not None
    ):
        assert isinstance(value, (int, float)) and not isinstance(value, bool)
        return (quality, _quantize_step(value, spec))
    return (quality, value)


def _encode_quantized_deltas(steps: Sequence[int]) -> telemetry_pb2.QuantizedDeltas:
    raw_pb = telemetry_pb2.QuantizedDeltas(first_step=steps[0])
    if len(steps) > 1:
        raw_pb.step_deltas.extend(steps[i] - steps[i - 1] for i in range(1, len(steps)))

    run_vals: list[int] = [steps[0]]
    run_lens: list[int] = [1]
    for step in steps[1:]:
        if step == run_vals[-1]:
            run_lens[-1] += 1
        else:
            run_vals.append(step)
            run_lens.append(1)

    if len(run_vals) == len(steps):
        return raw_pb

    rle_pb = telemetry_pb2.QuantizedDeltas(first_step=run_vals[0])
    if len(run_vals) > 1:
        rle_pb.step_deltas.extend(run_vals[i] - run_vals[i - 1] for i in range(1, len(run_vals)))
    rle_pb.run_lengths.extend(run_lens)
    return rle_pb if rle_pb.ByteSize() < raw_pb.ByteSize() else raw_pb


def _decode_quantized_deltas(pb: telemetry_pb2.QuantizedDeltas, expected: int) -> list[int]:
    if expected == 0:
        return []
    values = [int(pb.first_step)]
    for delta in pb.step_deltas:
        values.append(values[-1] + int(delta))
    if not pb.run_lengths:
        if len(values) != expected:
            raise TelemetryError("quantized delta count mismatch")
        return values
    if len(pb.run_lengths) != len(values):
        raise TelemetryError("quantized run_lengths count mismatch")
    expanded: list[int] = []
    for val, count in zip(values, pb.run_lengths, strict=True):
        expanded.extend([val] * int(count))
    if len(expanded) != expected:
        raise TelemetryError("quantized RLE length mismatch")
    return expanded


def _encode_raw_doubles(values: Sequence[float]) -> telemetry_pb2.RawDoubles:
    raw_pb = telemetry_pb2.RawDoubles(values=values)
    run_vals: list[float] = [values[0]]
    run_lens: list[int] = [1]
    for val in values[1:]:
        if val == run_vals[-1]:
            run_lens[-1] += 1
        else:
            run_vals.append(val)
            run_lens.append(1)
    if len(run_vals) == len(values):
        return raw_pb
    rle_pb = telemetry_pb2.RawDoubles(values=run_vals, run_lengths=run_lens)
    return rle_pb if rle_pb.ByteSize() < raw_pb.ByteSize() else raw_pb


def _decode_raw_doubles(pb: telemetry_pb2.RawDoubles, expected: int) -> list[float]:
    if not pb.run_lengths:
        if len(pb.values) != expected:
            raise TelemetryError("raw double count mismatch")
        return list(pb.values)
    if len(pb.run_lengths) != len(pb.values):
        raise TelemetryError("raw double run_lengths mismatch")
    expanded: list[float] = []
    for val, count in zip(pb.values, pb.run_lengths, strict=True):
        expanded.extend([float(val)] * int(count))
    if len(expanded) != expected:
        raise TelemetryError("raw double RLE length mismatch")
    return expanded


def _encode_bool_runs(values: Sequence[bool]) -> telemetry_pb2.BoolRuns:
    initial = bool(values[0])
    runs: list[int] = [1]
    current = initial
    for val in values[1:]:
        bval = bool(val)
        if bval == current:
            runs[-1] += 1
        else:
            current = bval
            runs.append(1)
    return telemetry_pb2.BoolRuns(initial_value=initial, run_lengths=runs)


def _decode_bool_runs(pb: telemetry_pb2.BoolRuns, expected: int) -> list[bool]:
    expanded: list[bool] = []
    current = bool(pb.initial_value)
    for count in pb.run_lengths:
        expanded.extend([current] * int(count))
        current = not current
    if len(expanded) != expected:
        raise TelemetryError("bool run length mismatch")
    return expanded


def _encode_string_runs(values: Sequence[str]) -> telemetry_pb2.StringRuns:
    run_vals: list[str] = [values[0]]
    run_lens: list[int] = [1]
    for val in values[1:]:
        if val == run_vals[-1]:
            run_lens[-1] += 1
        else:
            run_vals.append(val)
            run_lens.append(1)
    if len(run_vals) == len(values):
        return telemetry_pb2.StringRuns(values=values)
    return telemetry_pb2.StringRuns(values=run_vals, run_lengths=run_lens)


def _decode_string_runs(pb: telemetry_pb2.StringRuns, expected: int) -> list[str]:
    if not pb.run_lengths:
        if len(pb.values) != expected:
            raise TelemetryError("string count mismatch")
        return list(pb.values)
    if len(pb.run_lengths) != len(pb.values):
        raise TelemetryError("string run_lengths mismatch")
    expanded: list[str] = []
    for val, count in zip(pb.values, pb.run_lengths, strict=True):
        expanded.extend([str(val)] * int(count))
    if len(expanded) != expected:
        raise TelemetryError("string RLE length mismatch")
    return expanded


def encode_batch(
    dictionary: Dictionary,
    observations: Sequence[Observation],
    *,
    downgrade_invalid: bool = False,
    emit_on_change: bool = False,
) -> telemetry_pb2.Batch:
    """Encode observations into a columnar compressed protobuf Batch."""
    if not observations:
        return telemetry_pb2.Batch(
            dictionary_fingerprint=dictionary.fingerprint,
            base_received_ms=0,
        )

    grouped: dict[int, list[tuple[Observation, Quality, bool | int | float | str | None]]] = {}
    for obs in observations:
        spec = dictionary.resolve_signal(obs.name, obs.source)
        quality, value = _validate_and_prepare_value(obs, spec, downgrade_invalid=downgrade_invalid)
        grouped.setdefault(spec.id, []).append((obs, quality, value))

    if emit_on_change:
        filtered_grouped: dict[
            int, list[tuple[Observation, Quality, bool | int | float | str | None]]
        ] = {}
        for signal_id, entries in grouped.items():
            spec = dictionary.by_id(signal_id)
            kept: list[tuple[Observation, Quality, bool | int | float | str | None]] = []
            last_key: Any = object()
            last_emitted_ms = 0
            for item in entries:
                obs, quality, value = item
                key = _canonical_eq_key(quality, value, spec)
                heartbeat_due = (
                    spec.max_age_ms > 0
                    and (obs.received_at_ms - last_emitted_ms) >= spec.max_age_ms
                )
                if not kept or key != last_key or heartbeat_due:
                    kept.append(item)
                    last_key = key
                    last_emitted_ms = obs.received_at_ms
            filtered_grouped[signal_id] = kept
        grouped = filtered_grouped

    base_received_ms = min(
        obs.received_at_ms for entries in grouped.values() for obs, _, _ in entries
    )
    batch = telemetry_pb2.Batch(
        dictionary_fingerprint=dictionary.fingerprint,
        base_received_ms=base_received_ms,
    )

    for signal_id in sorted(grouped):
        spec = dictionary.by_id(signal_id)
        entries = grouped[signal_id]
        count = len(entries)
        ts = [obs.received_at_ms for obs, _, _ in entries]
        seqs = [obs.sequence for obs, _, _ in entries]
        qualities = [q for _, q, _ in entries]

        series = batch.series.add(
            signal_id=signal_id,
            start_sequence=seqs[0],
            sample_count=count,
            first_received_delta_ms=ts[0] - base_received_ms,
        )

        # Delta-of-delta receipt timestamps.
        if count >= 2:
            prev_interval = ts[1] - ts[0]
            series.first_interval_ms = prev_interval
            for idx in range(2, count):
                interval = ts[idx] - ts[idx - 1]
                series.received_dod_ms.append(interval - prev_interval)
                prev_interval = interval

        # Optional measurement timestamps.
        present_obs = [obs.observed_at_ms is not None for obs, _, _ in entries]
        if any(present_obs):
            series.has_observed_at = True
            if not all(present_obs):
                series.observed_present_bits = _pack_bitset(present_obs)
            for obs, _, _ in entries:
                if obs.observed_at_ms is not None:
                    series.observed_offset_ms.append(obs.observed_at_ms - obs.received_at_ms)

        # Sequence deltas only when non-contiguous.
        if count >= 2:
            deltas = [seqs[i] - seqs[i - 1] for i in range(1, count)]
            if any(d != 1 for d in deltas):
                if any(d < 0 for d in deltas):
                    raise TelemetryError(f"{spec.name}: sequence numbers must be non-decreasing")
                series.sequence_deltas.extend(deltas)

        # Quality encoding.
        if all(q == qualities[0] for q in qualities):
            series.uniform_quality = _QUALITY_TO_PB[qualities[0]]
        else:
            q_vals = [_QUALITY_TO_PB[qualities[0]]]
            q_runs = [1]
            for q in qualities[1:]:
                pb_q = _QUALITY_TO_PB[q]
                if pb_q == q_vals[-1]:
                    q_runs[-1] += 1
                else:
                    q_vals.append(pb_q)
                    q_runs.append(1)
            series.quality_runs.values.extend(q_vals)
            series.quality_runs.run_lengths.extend(q_runs)

        # Presence bitset only when deviating from default (VALID/STALE carry values).
        actual_present = [val is not None for _, _, val in entries]
        default_present = [q in (Quality.VALID, Quality.STALE) for q in qualities]
        if actual_present != default_present:
            series.value_present_bits = _pack_bitset(actual_present)

        values = [val for _, _, val in entries if val is not None]
        if not values:
            continue

        if spec.value_kind == ValueKind.BOOL:
            series.bool_runs.CopyFrom(_encode_bool_runs([bool(v) for v in values]))
        elif spec.value_kind == ValueKind.STRING:
            series.string_runs.CopyFrom(_encode_string_runs([str(v) for v in values]))
        elif spec.value_kind in (ValueKind.INT, ValueKind.UINT):
            steps = [_quantize_step(int(v), spec) for v in values]
            if all(_MIN_SINT64 <= s <= _MAX_SINT64 for s in steps):
                series.quantized.CopyFrom(_encode_quantized_deltas(steps))
            else:
                series.raw_doubles.CopyFrom(_encode_raw_doubles([float(v) for v in values]))
        elif spec.quantization is not None:
            steps = [_quantize_step(float(v), spec) for v in values]
            series.quantized.CopyFrom(_encode_quantized_deltas(steps))
        else:
            series.raw_doubles.CopyFrom(_encode_raw_doubles([float(v) for v in values]))

    return batch


def decode_batch(dictionary: Dictionary, batch: telemetry_pb2.Batch) -> list[Observation]:
    """Decode a protobuf Batch into Observation objects, verifying dictionary fingerprint."""
    if bytes(batch.dictionary_fingerprint) != dictionary.fingerprint:
        raise TelemetryError("batch dictionary fingerprint mismatch")

    observations: list[Observation] = []
    for series in batch.series:
        spec = dictionary.by_id(series.signal_id)
        count = int(series.sample_count)
        if count == 0:
            continue

        # Reconstruct receipt timestamps.
        ts = [int(batch.base_received_ms) + int(series.first_received_delta_ms)]
        if count >= 2:
            interval = int(series.first_interval_ms)
            ts.append(ts[0] + interval)
            if len(series.received_dod_ms) != count - 2:
                raise TelemetryError("received_dod_ms count mismatch")
            for dod in series.received_dod_ms:
                interval += int(dod)
                ts.append(ts[-1] + interval)

        # Reconstruct optional measurement timestamps.
        observed_times: list[int | None] = [None] * count
        if series.has_observed_at:
            if series.observed_present_bits:
                present = _unpack_bitset(bytes(series.observed_present_bits), count)
            else:
                present = [True] * count
            offset_iter = iter(series.observed_offset_ms)
            for idx, is_present in enumerate(present):
                if is_present:
                    try:
                        observed_times[idx] = ts[idx] + int(next(offset_iter))
                    except StopIteration as exc:
                        raise TelemetryError(
                            "observed_offset_ms shorter than present mask"
                        ) from exc

        # Reconstruct sequences.
        seqs = [int(series.start_sequence)]
        if series.sequence_deltas:
            if len(series.sequence_deltas) != count - 1:
                raise TelemetryError("sequence_deltas count mismatch")
            for delta in series.sequence_deltas:
                seqs.append(seqs[-1] + int(delta))
        else:
            seqs.extend(seqs[0] + idx for idx in range(1, count))

        # Reconstruct qualities.
        q_kind = series.WhichOneof("quality_encoding")
        if q_kind == "uniform_quality":
            qualities = [_PB_TO_QUALITY[series.uniform_quality]] * count
        elif q_kind == "quality_runs":
            qualities = []
            for pb_q, run in zip(
                series.quality_runs.values, series.quality_runs.run_lengths, strict=True
            ):
                qualities.extend([_PB_TO_QUALITY[pb_q]] * int(run))
            if len(qualities) != count:
                raise TelemetryError("quality_runs total length mismatch")
        else:
            raise TelemetryError("missing quality_encoding on Series")

        # Value presence mask.
        if series.value_present_bits:
            value_present = _unpack_bitset(bytes(series.value_present_bits), count)
        else:
            value_present = [q in (Quality.VALID, Quality.STALE) for q in qualities]

        value_count = sum(1 for flag in value_present if flag)
        decoded_vals: list[bool | int | float | str] = []
        v_kind = series.WhichOneof("value_encoding")
        if value_count > 0:
            if v_kind == "quantized":
                steps = _decode_quantized_deltas(series.quantized, value_count)
                decoded_vals = [_dequantize_step(step, spec) for step in steps]
            elif v_kind == "raw_doubles":
                decoded_vals = list(_decode_raw_doubles(series.raw_doubles, value_count))
            elif v_kind == "bool_runs":
                decoded_vals = list(_decode_bool_runs(series.bool_runs, value_count))
            elif v_kind == "string_runs":
                decoded_vals = list(_decode_string_runs(series.string_runs, value_count))
            else:
                raise TelemetryError("missing value_encoding for value-bearing samples")

        val_iter = iter(decoded_vals)
        for idx in range(count):
            val = next(val_iter) if value_present[idx] else None
            observations.append(
                Observation(
                    name=spec.name,
                    received_at_ms=ts[idx],
                    value=val,
                    quality=qualities[idx],
                    name_kind=spec.name_kind,
                    unit=spec.unit,
                    source=spec.source,
                    acquisition=spec.acquisition,
                    observed_at_ms=observed_times[idx],
                    clock_domain=spec.clock_domain,
                    sequence=seqs[idx],
                )
            )

    return observations


def encode_frame_record(frame: telemetry_pb2.Frame, *, compress: bool = True) -> bytes:
    raw = frame.SerializeToString()
    if compress:
        payload = zlib.compress(raw, level=6)
        flags = FLAG_ZLIB
    else:
        payload = raw
        flags = FLAG_RAW
    return struct.pack(">BI", flags, len(payload)) + payload


def decode_frame_records(stream: BinaryIO) -> list[telemetry_pb2.Frame]:
    magic = stream.read(4)
    if magic != VTS_MAGIC:
        raise TelemetryError(f"invalid VTS magic: {magic!r}")
    frames: list[telemetry_pb2.Frame] = []
    while True:
        header = stream.read(5)
        if not header:
            break
        if len(header) != 5:
            raise TelemetryError("truncated VTS frame header")
        flags, length = struct.unpack(">BI", header)
        payload = stream.read(length)
        if len(payload) != length:
            raise TelemetryError("truncated VTS frame payload")
        if flags == FLAG_RAW:
            raw = payload
        elif flags == FLAG_ZLIB:
            raw = zlib.decompress(payload)
        else:
            raise TelemetryError(f"unsupported VTS frame flags: {flags:#x}")
        frame = telemetry_pb2.Frame()
        frame.ParseFromString(raw)
        frames.append(frame)
    return frames


def write_vts_bytes(
    dictionary: Dictionary,
    batches: Sequence[telemetry_pb2.Batch],
    *,
    compress: bool = True,
) -> bytes:
    out = bytearray(VTS_MAGIC)
    dict_frame = telemetry_pb2.Frame(dictionary=dictionary_to_pb(dictionary))
    out.extend(encode_frame_record(dict_frame, compress=compress))
    for batch in batches:
        batch_frame = telemetry_pb2.Frame(batch=batch)
        out.extend(encode_frame_record(batch_frame, compress=compress))
    return bytes(out)


def read_vts_bytes(data: bytes) -> tuple[Dictionary, list[Observation]]:
    frames = decode_frame_records(io.BytesIO(data))
    if not frames or frames[0].WhichOneof("body") != "dictionary":
        raise TelemetryError("VTS stream must begin with a Dictionary frame")
    dictionary = dictionary_from_pb(frames[0].dictionary)
    observations: list[Observation] = []
    for frame in frames[1:]:
        body = frame.WhichOneof("body")
        if body == "batch":
            observations.extend(decode_batch(dictionary, frame.batch))
        elif body == "dictionary":
            dictionary = dictionary_from_pb(frame.dictionary)
    return dictionary, observations


def write_zip_bytes(
    dictionary: Dictionary,
    batches: Sequence[telemetry_pb2.Batch],
) -> bytes:
    # Store raw VTS frames inside ZIP_DEFLATED so deflate sees the full session without double compression.
    vts_raw = write_vts_bytes(dictionary, batches, compress=False)
    sample_count = sum(series.sample_count for batch in batches for series in batch.series)
    start_ms: int | None = None
    end_ms: int | None = None
    for batch in batches:
        for obs in decode_batch(dictionary, batch):
            start_ms = obs.received_at_ms if start_ms is None else min(start_ms, obs.received_at_ms)
            end_ms = obs.received_at_ms if end_ms is None else max(end_ms, obs.received_at_ms)

    manifest = {
        "format": "vehicle-telemetry-zip/1",
        "vehicle_id": dictionary.vehicle_id,
        "dictionary_fingerprint": dictionary.fingerprint.hex(),
        "profile_id": dictionary.profile_id,
        "profile_version": dictionary.profile_version,
        "vss_release": dictionary.vss_release,
        "batch_count": len(batches),
        "sample_count": sample_count,
        "start_received_ms": start_ms,
        "end_received_ms": end_ms,
        "signals": [
            {"id": s.id, "name": s.name, "unit": s.unit, "source": s.source}
            for s in dictionary.signals
        ],
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.writestr("session.vts", vts_raw)
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return buf.getvalue()


def read_zip_bytes(data: bytes) -> tuple[Dictionary, list[Observation]]:
    with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
        if "session.vts" not in zf.namelist():
            raise TelemetryError("ZIP archive missing session.vts")
        dictionary, observations = read_vts_bytes(zf.read("session.vts"))
        if "manifest.json" in zf.namelist():
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            expected_fp = manifest.get("dictionary_fingerprint")
            if expected_fp and expected_fp != dictionary.fingerprint.hex():
                raise TelemetryError("ZIP manifest fingerprint mismatch")
        return dictionary, observations


def write_telemetry(
    path: str | Path,
    dictionary: Dictionary,
    observations: Sequence[Observation],
    *,
    compression: str = "zlib",
    batch_size: int = 1000,
    downgrade_invalid: bool = False,
    emit_on_change: bool = False,
) -> int:
    """Encode observations and write a .vts (raw/zlib) or .zip telemetry file."""
    batches: list[telemetry_pb2.Batch] = []
    if observations:
        step = max(1, batch_size)
        for offset in range(0, len(observations), step):
            chunk = observations[offset : offset + step]
            batches.append(
                encode_batch(
                    dictionary,
                    chunk,
                    downgrade_invalid=downgrade_invalid,
                    emit_on_change=emit_on_change,
                )
            )

    if compression == "raw":
        data = write_vts_bytes(dictionary, batches, compress=False)
    elif compression == "zlib":
        data = write_vts_bytes(dictionary, batches, compress=True)
    elif compression == "zip":
        data = write_zip_bytes(dictionary, batches)
    else:
        raise TelemetryError(f"unsupported compression mode: {compression!r}")

    target = Path(path)
    target.write_bytes(data)
    return len(data)


def read_telemetry(path: str | Path) -> tuple[Dictionary, list[Observation]]:
    """Read a .vts or .zip telemetry file."""
    data = Path(path).read_bytes()
    if data[:4] == ZIP_MAGIC:
        return read_zip_bytes(data)
    if data[:4] == VTS_MAGIC:
        return read_vts_bytes(data)
    raise TelemetryError("unrecognized telemetry file format (expected VTS1 or ZIP)")


def inspect_telemetry(path: str | Path) -> dict[str, Any]:
    """Return a summary dictionary for a .vts or .zip telemetry file."""
    raw = Path(path).read_bytes()
    container = "zip" if raw[:4] == ZIP_MAGIC else "vts"
    dictionary, observations = read_zip_bytes(raw) if container == "zip" else read_vts_bytes(raw)
    counts: dict[tuple[str, str], int] = {}
    quality_counts: dict[str, int] = {}
    for obs in observations:
        key = (obs.name, obs.source)
        counts[key] = counts.get(key, 0) + 1
        quality_counts[obs.quality.value] = quality_counts.get(obs.quality.value, 0) + 1
    return {
        "container": container,
        "bytes": len(raw),
        "vehicle_id": dictionary.vehicle_id,
        "profile_id": dictionary.profile_id,
        "profile_version": dictionary.profile_version,
        "vss_release": dictionary.vss_release,
        "dictionary_fingerprint": dictionary.fingerprint.hex(),
        "signal_count": len(dictionary.signals),
        "observation_count": len(observations),
        "quality_counts": quality_counts,
        "signals": [
            {
                "id": s.id,
                "name": s.name,
                "unit": s.unit,
                "value_kind": s.value_kind.value,
                "source": s.source,
                "acquisition": s.acquisition.value,
                "samples": counts.get((s.name, s.source), 0),
            }
            for s in dictionary.signals
        ],
    }


def read_observations_jsonl(path: str | Path) -> list[Observation]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [Observation.from_dict(json.loads(line)) for line in lines if line.strip()]


def write_observations_jsonl(path: str | Path, observations: Iterable[Observation]) -> None:
    text = "".join(json.dumps(obs.to_dict(), sort_keys=True) + "\n" for obs in observations)
    Path(path).write_text(text, encoding="utf-8")
