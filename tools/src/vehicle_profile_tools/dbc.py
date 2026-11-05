"""Minimal BO_/SG_/VAL_ parser; unsupported multiplexing is rejected explicitly."""

import re
from dataclasses import dataclass, field

from .errors import fail


@dataclass
class Signal:
    name: str
    start: int
    bits: int
    little: bool
    signed: bool
    factor: float
    offset: float
    minimum: float
    maximum: float
    unit: str
    labels: dict[str, str] = field(default_factory=dict)

    def raw(self, payload):
        if self.little:
            if self.start + self.bits > len(payload) * 8:
                raise ValueError("short DBC frame")
            result = (int.from_bytes(payload, "little") >> self.start) & ((1 << self.bits) - 1)
        else:
            result, pos = 0, self.start
            for _ in range(self.bits):
                if pos >= len(payload) * 8:
                    raise ValueError("short DBC frame")
                result = (result << 1) | ((payload[pos // 8] >> (pos % 8)) & 1)
                pos = pos + 15 if pos % 8 == 0 else pos - 1
        if self.signed and result & (1 << (self.bits - 1)):
            result -= 1 << self.bits
        return result

    def decode(self, payload, decode_as=None, enum=None):
        raw = self.raw(payload)
        if decode_as == "boolean":
            if raw not in (0, 1):
                raise ValueError("boolean requires raw 0 or 1")
            return bool(raw)
        if enum is not None:
            if str(raw) not in enum:
                raise ValueError("unmapped raw enum")
            return enum[str(raw)]
        return raw * self.factor + self.offset


@dataclass
class Message:
    id: int
    name: str
    length: int
    signals: dict[str, Signal] = field(default_factory=dict)


class Dbc:
    def __init__(self, text):
        self.messages = []
        current = None
        for line in text.splitlines():
            line = line.strip()
            m = re.match(r"BO_ (\d+) (\w+): (\d+) ", line)
            if m:
                current = Message(int(m[1]), m[2], int(m[3]))
                self.messages.append(current)
            elif line.startswith("SG_ "):
                m = re.match(
                    r'SG_ (\w+)\s*:\s*(\d+)\|(\d+)@([01])([+-])\s*\(([^,]+),([^\)]+)\)\s*\[([^|]+)\|([^\]]+)\]\s*"([^"]*)"',
                    line,
                )
                if not m or current is None:
                    fail("DOC_INVALID", "dbc", f"unsupported signal declaration: {line}")
                if m[1] in current.signals:
                    fail("DOC_INVALID", m[1], "duplicate DBC signal")
                current.signals[m[1]] = Signal(
                    m[1],
                    int(m[2]),
                    int(m[3]),
                    m[4] == "1",
                    m[5] == "-",
                    float(m[6]),
                    float(m[7]),
                    float(m[8]),
                    float(m[9]),
                    m[10],
                )
        for line in text.splitlines():
            m = re.match(r"\s*VAL_ (\d+) (\w+) (.*);", line)
            if m:
                for message in self.messages:
                    if message.id == int(m[1]) and m[2] in message.signals:
                        message.signals[m[2]].labels = dict(re.findall(r'(-?\d+) "([^"]*)"', m[3]))

    def message(self, name):
        found = [m for m in self.messages if m.name == name]
        if len(found) != 1:
            fail(
                "DBC_AMBIGUOUS_MESSAGE" if found else "DBC_UNKNOWN_MESSAGE",
                name,
                "need one matching message",
            )
        return found[0]

    def signal(self, message, name):
        msg = self.message(message)
        if name not in msg.signals:
            fail("DBC_UNKNOWN_SIGNAL", f"{message}.{name}", "signal not defined")
        return msg.signals[name]
