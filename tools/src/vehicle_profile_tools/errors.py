from enum import StrEnum
from typing import NoReturn


class ErrorCode(StrEnum):
    PKG_NO_MANIFEST = "PKG_NO_MANIFEST"
    PKG_MULTIPLE_MANIFESTS = "PKG_MULTIPLE_MANIFESTS"
    PKG_UNSAFE_PATH = "PKG_UNSAFE_PATH"
    PKG_UNLISTED_FILE = "PKG_UNLISTED_FILE"
    PKG_MISSING_FILE = "PKG_MISSING_FILE"
    PKG_HASH_MISMATCH = "PKG_HASH_MISMATCH"
    PKG_TOO_LARGE = "PKG_TOO_LARGE"
    DOC_INVALID = "DOC_INVALID"
    DOC_UNKNOWN_FIELD = "DOC_UNKNOWN_FIELD"
    DOC_LEGACY_FORMAT = "DOC_LEGACY_FORMAT"
    DOC_EXCLUSIVE_FORMS = "DOC_EXCLUSIVE_FORMS"
    REF_UNKNOWN_ENDPOINT = "REF_UNKNOWN_ENDPOINT"
    REF_UNKNOWN_SEQUENCE = "REF_UNKNOWN_SEQUENCE"
    REF_UNKNOWN_SOURCE = "REF_UNKNOWN_SOURCE"
    REF_SOURCE_KIND = "REF_SOURCE_KIND"
    REF_CYCLE = "REF_CYCLE"
    DBC_UNKNOWN_MESSAGE = "DBC_UNKNOWN_MESSAGE"
    DBC_UNKNOWN_SIGNAL = "DBC_UNKNOWN_SIGNAL"
    DBC_AMBIGUOUS_MESSAGE = "DBC_AMBIGUOUS_MESSAGE"
    DEP_UNSATISFIED = "DEP_UNSATISFIED"
    VSS_UNSUPPORTED_RELEASE = "VSS_UNSUPPORTED_RELEASE"
    VSS_UNKNOWN_PATH = "VSS_UNKNOWN_PATH"
    VSS_ROLE_MISMATCH = "VSS_ROLE_MISMATCH"
    VSS_CONSTRAINT_WIDENED = "VSS_CONSTRAINT_WIDENED"
    VSS_UNIT_MISMATCH = "VSS_UNIT_MISMATCH"
    VSS_ENUM_VALUE = "VSS_ENUM_VALUE"
    ALIAS_COLLISION = "ALIAS_COLLISION"
    MERGE_CONFLICT = "MERGE_CONFLICT"
    APPLICABILITY_WIDENED = "APPLICABILITY_WIDENED"
    EXT_NOT_REQUIRED = "EXT_NOT_REQUIRED"
    EXT_UNSUPPORTED = "EXT_UNSUPPORTED"
    FIXTURE_INVALID = "FIXTURE_INVALID"


ERROR_DETAILS = {
    "PKG_NO_MANIFEST": (
        "Container",
        "No root manifest",
        "Add vehicle.yaml or vehicle.json at the package root.",
    ),
    "PKG_MULTIPLE_MANIFESTS": (
        "Container",
        "Both manifest names exist",
        "Keep exactly one root manifest.",
    ),
    "PKG_UNSAFE_PATH": (
        "Container",
        "Unsafe or ambiguous asset path",
        "Use unique relative POSIX paths without symlinks or traversal.",
    ),
    "PKG_UNLISTED_FILE": (
        "Container",
        "Archive has an unlisted asset",
        "List it in the manifest or remove it from the archive.",
    ),
    "PKG_MISSING_FILE": (
        "Container",
        "Listed asset is missing",
        "Restore the asset or correct its manifest path.",
    ),
    "PKG_HASH_MISMATCH": (
        "Container",
        "Asset integrity check failed",
        "Supply the required digest and verify it against the intended bytes.",
    ),
    "PKG_TOO_LARGE": (
        "Container",
        "Package resource limit exceeded",
        "Reduce file count/size or ZIP compression ratio.",
    ),
    "DOC_INVALID": (
        "Syntax",
        "Malformed or unsupported structure",
        "Correct the named field using the format 2 schema.",
    ),
    "DOC_UNKNOWN_FIELD": (
        "Syntax",
        "Field is outside the grammar",
        "Correct the spelling or explicitly except only a non-behavioral annotation.",
    ),
    "DOC_LEGACY_FORMAT": (
        "Syntax",
        "Format 1 input cannot load directly",
        "Run vprofile migrate and declare the source framing for response bindings.",
    ),
    "DOC_EXCLUSIVE_FORMS": (
        "Syntax",
        "Mutually exclusive forms overlap",
        "Choose one write/read form; separate static value from read.",
    ),
    "REF_UNKNOWN_ENDPOINT": (
        "References",
        "Endpoint is not defined",
        "Define the endpoint in a loaded document.",
    ),
    "REF_UNKNOWN_SEQUENCE": (
        "References",
        "Called sequence is missing",
        "Define the sequence or correct the call after composition.",
    ),
    "REF_UNKNOWN_SOURCE": (
        "References",
        "Source or output is missing",
        "Define the source and the referenced output.",
    ),
    "REF_SOURCE_KIND": (
        "References",
        "Acquisition kind disagrees with source",
        "Use a signal source for signal and query source for query.",
    ),
    "REF_CYCLE": ("References", "Sequence calls form a cycle", "Remove the recursive call chain."),
    "DBC_UNKNOWN_MESSAGE": (
        "References",
        "DBC asset or message is missing",
        "Check the manifest DBC ID and message name.",
    ),
    "DBC_UNKNOWN_SIGNAL": (
        "References",
        "Signal is missing from its DBC message",
        "Correct the exact protocol-level signal name.",
    ),
    "DBC_AMBIGUOUS_MESSAGE": (
        "References",
        "More than one DBC message has that name",
        "Give referenced messages unique names.",
    ),
    "DEP_UNSATISFIED": (
        "Dependencies",
        "Earlier packages do not satisfy a dependency",
        "Load a matching ID and semver range before this package.",
    ),
    "VSS_UNSUPPORTED_RELEASE": (
        "Semantics",
        "Catalog release is not supported",
        "Pin vss to the bundled 6.1 release.",
    ),
    "VSS_UNKNOWN_PATH": (
        "Semantics",
        "Path is absent from the catalog",
        "Find the canonical path with vprofile vss search/show.",
    ),
    "VSS_ROLE_MISMATCH": (
        "Semantics",
        "Binding is incompatible with the VSS role",
        "Write only actuators, use value only on attributes, and keep canonical properties out of named actions/queries.",
    ),
    "VSS_CONSTRAINT_WIDENED": (
        "Semantics",
        "Write constraints expand the catalog domain",
        "Narrow numeric scalar constraints to the catalog/type bounds.",
    ),
    "VSS_UNIT_MISMATCH": (
        "Semantics",
        "Decoded unit differs from VSS",
        "Use the canonical unit and an explicit correct conversion.",
    ),
    "VSS_ENUM_VALUE": (
        "Semantics",
        "Value, case or datatype violates VSS",
        "Check datatype, allowed values, canonical case keys and ranges.",
    ),
    "ALIAS_COLLISION": (
        "Semantics",
        "Alias shadows another public capability",
        "Use a unique alias across properties, queries and actions.",
    ),
    "MERGE_CONFLICT": (
        "Composition",
        "Packages collide without an override",
        "Use unique package IDs and explicit override on a later replacing document.",
    ),
    "APPLICABILITY_WIDENED": (
        "Composition",
        "Document widens package applicability",
        "Restrict document applicability to the package domain.",
    ),
    "EXT_NOT_REQUIRED": (
        "Extensions",
        "Extension payload has no requirement",
        "Declare the publisher-qualified feature and exact version in requires.",
    ),
    "EXT_UNSUPPORTED": (
        "Extensions",
        "Required extension is unsupported",
        "Use a runtime supporting that exact contract; parsing does not imply activation support.",
    ),
    "FIXTURE_INVALID": (
        "Evidence",
        "Fixture names a missing or incompatible binding",
        "Correct the path/name and acquisition kind to an existing capability.",
    ),
}


class ProfileError(ValueError):
    def __init__(self, code: str, location: str, detail: str):
        self.code, self.location, self.detail = code, location, detail
        super().__init__(f"{code}: {location}: {detail}")


def fail(code: str, location: str, detail: str) -> NoReturn:
    raise ProfileError(code, location, detail)


def error_reference():
    lines = [
        "# Validator error codes",
        "",
        "Generated from errors.py. Each entry gives the layer, meaning and usual fix.",
        "",
    ]
    for code in ErrorCode:
        layer, meaning, hint = ERROR_DETAILS[code]
        lines.append(f"- `{code}` — {layer}: {meaning}. {hint}")
    return "\n".join(lines) + "\n"
