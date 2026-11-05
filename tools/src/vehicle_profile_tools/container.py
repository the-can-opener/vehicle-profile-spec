"""Bounded package reader. Only explicitly listed files are opened."""

import hashlib
import stat
import zipfile
from pathlib import Path, PurePosixPath

from pydantic import ValidationError

from .errors import fail
from .manifest import Manifest
from .model import DocumentRaw
from .strict import StrictOption, parse

MAX_FILE = 4 * 1024 * 1024
MAX_PACKAGE = 16 * 1024 * 1024
MAX_ENTRIES = 1000


def safe_path(name):
    path = PurePosixPath(name)
    if (
        not name
        or "\\" in name
        or ":" in name
        or path.is_absolute()
        or any(p in ("..", ".", "") for p in name.split("/"))
    ):
        fail("PKG_UNSAFE_PATH", name, "expected a safe relative POSIX path")
    return path


def validate_model(model, data, location="", strict=True):
    policy = strict if isinstance(strict, StrictOption) else StrictOption(strict)
    if policy.exceptions:
        data = policy.clean(model, data)
    try:
        # Non-strict mode permits unknown fields only; all value checks still apply.
        return model.model_validate(data, extra="forbid" if policy.enabled else "ignore")
    except ValidationError as exc:
        errors = exc.errors()
        code = (
            "DOC_UNKNOWN_FIELD"
            if any(e["type"] == "extra_forbidden" for e in errors)
            else "DOC_INVALID"
        )
        if "DOC_EXCLUSIVE_FORMS" in str(exc):
            code = "DOC_EXCLUSIVE_FORMS"
        first = ".".join(str(x) for x in errors[0]["loc"])
        fail(
            code,
            ".".join(x for x in (location, first) if x),
            f"{len(errors)} model error(s): {errors[0]['msg']}",
        )


class Package:
    def __init__(self, path, strict=True, integrity_required=False):
        self.path = Path(path)
        self.zip = None
        self.names = {}
        if self.path.is_symlink():
            fail("PKG_UNSAFE_PATH", str(path), "symlink package")
        if self.path.is_dir():
            roots = [n for n in ("vehicle.yaml", "vehicle.json") if (self.path / n).exists()]
        else:
            try:
                with zipfile.ZipFile(self.path) as z:
                    total = 0
                    seen = set()
                    if len(z.infolist()) > MAX_ENTRIES:
                        fail("PKG_TOO_LARGE", str(path), "too many entries")
                    for info in z.infolist():
                        name = info.filename.rstrip("/")
                        safe_path(name)
                        if name.casefold() in seen:
                            fail("PKG_UNSAFE_PATH", name, "duplicate/case-colliding archive entry")
                        seen.add(name.casefold())
                        mode = info.external_attr >> 16
                        if stat.S_ISLNK(mode) or info.flag_bits & 1:
                            fail("PKG_UNSAFE_PATH", name, "symlink or encrypted entry")
                        if not info.flag_bits & 0x800 and not name.isascii():
                            fail("PKG_UNSAFE_PATH", name, "non-UTF-8 archive name")
                        total += info.file_size
                        if (
                            info.file_size > MAX_FILE
                            or info.file_size > max(1, info.compress_size) * 100
                        ):
                            fail("PKG_TOO_LARGE", name, "file or compression ratio limit")
                    if total > MAX_PACKAGE:
                        fail("PKG_TOO_LARGE", str(path), "package size limit")
                    self.zip = {i.filename: z.read(i) for i in z.infolist() if not i.is_dir()}
                roots = [n for n in ("vehicle.yaml", "vehicle.json") if n in self.zip]
            except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
                fail("DOC_INVALID", str(path), str(exc))
        if len(roots) != 1:
            if self.path.is_dir() and (self.path / "profile.yaml").exists():
                fail("DOC_LEGACY_FORMAT", str(path), "run vprofile migrate")
            fail(
                "PKG_MULTIPLE_MANIFESTS" if roots else "PKG_NO_MANIFEST",
                str(path),
                "need exactly one manifest",
            )
        self.manifest_name = roots[0]
        self.total = 0
        raw = self.parse(roots[0])
        if not isinstance(raw, dict):
            fail("DOC_INVALID", roots[0], "expected an object")
        if raw.get("format") == 1 or raw.get("version") == 1:
            fail("DOC_LEGACY_FORMAT", roots[0], "run vprofile migrate")
        if raw.get("vss") != "6.1":
            fail("VSS_UNSUPPORTED_RELEASE", "vss", "only pinned 6.1 is supported")
        single = "documents" not in raw
        manifest_raw = {
            k: v
            for k, v in raw.items()
            if not single or k not in DocumentRaw.model_fields or k == "applies_to"
        }
        self.manifest = validate_model(Manifest, manifest_raw, roots[0], strict)
        self.raw = raw
        self.assets = {roots[0]: None}
        refs = [
            *self.manifest.dbc.values(),
            *(self.manifest.documents or []),
            *self.manifest.fixtures,
        ]
        for ref in refs:
            name = ref if isinstance(ref, str) else ref.path
            digest = None if isinstance(ref, str) else ref.sha256
            if name in self.assets:
                fail("PKG_UNSAFE_PATH", name, "duplicate listed path")
            self.assets[name] = digest
            data = self.read(name)
            if integrity_required and not digest:
                fail("PKG_HASH_MISMATCH", name, "integrity policy requires sha256")
            if digest and hashlib.sha256(data).hexdigest() != digest.lower():
                fail("PKG_HASH_MISMATCH", name, "sha256 mismatch")
        if self.zip is not None:
            for name in self.zip:
                if name not in self.assets and not (
                    name.startswith("docs/")
                    or PurePosixPath(name).name.startswith(("README", "LICENSE", "CHANGELOG"))
                ):
                    fail("PKG_UNLISTED_FILE", name, "archive contains unlisted asset")

    def read(self, name):
        safe_path(name)
        folded = name.casefold()
        if folded in self.names and self.names[folded] != name:
            fail("PKG_UNSAFE_PATH", name, "case-colliding file names")
        fresh = folded not in self.names
        self.names[folded] = name
        if len(self.names) > MAX_ENTRIES:
            fail("PKG_TOO_LARGE", name, "too many listed files")
        if self.zip is not None:
            if name not in self.zip:
                fail("PKG_MISSING_FILE", name, "listed file is missing")
            data = self.zip[name]
        else:
            current = self.path
            for part in PurePosixPath(name).parts:
                current = current / part
                if current.is_symlink():
                    fail("PKG_UNSAFE_PATH", name, "symlink path component")
            if not current.is_file():
                fail("PKG_MISSING_FILE", name, "listed file is missing")
            if current.stat().st_size > MAX_FILE:
                fail("PKG_TOO_LARGE", name, "file size limit")
            data = current.read_bytes()
        if fresh:
            self.total += len(data)
        if len(data) > MAX_FILE or self.total > MAX_PACKAGE:
            fail("PKG_TOO_LARGE", name, "size limit")
        return data

    def parse(self, name):
        try:
            return parse(self.read(name).decode("utf-8"), name)
        except UnicodeDecodeError:
            fail("DOC_INVALID", name, "UTF-8 required")

    def documents(self):
        if self.manifest.documents is None:
            yield {k: v for k, v in self.raw.items() if k in DocumentRaw.model_fields}, {}, False
        else:
            for ref in self.manifest.documents:
                yield (
                    self.parse(ref.path),
                    ref.applies_to.model_dump(exclude_none=True),
                    ref.override,
                )
