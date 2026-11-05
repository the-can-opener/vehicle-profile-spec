from typing import Annotated, Any, Literal

from pydantic import Field, model_validator
from semantic_version import NpmSpec, Version

from .model import DEFAULT_CHANNEL, Model


class YearRange(Model):
    range: list[int] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def ordered(self):
        if self.range[0] > self.range[1] or self.range[1] - self.range[0] > 500:
            raise ValueError("invalid model year range")
        return self


class Applicability(Model):
    manufacturers: list[str] | None = None
    models: list[str] | None = None
    years: list[int | YearRange] | None = None
    trims: list[str] | None = None
    engines: list[str] | None = None
    markets: list[str] | None = None


class AssetRef(Model):
    path: str
    sha256: Annotated[str, Field(pattern=r"^[a-fA-F0-9]{64}$")] | None = None


class DocumentRef(AssetRef):
    applies_to: Applicability = Field(default_factory=Applicability)
    override: bool = False


class DbcRef(AssetRef):
    channel: str = DEFAULT_CHANNEL


class Dependency(Model):
    id: str
    version: str

    @model_validator(mode="after")
    def valid_range(self):
        NpmSpec(self.version)
        return self


class Manifest(Model):
    manifest: Literal[1]
    format: Literal[2]
    id: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$")]
    version: Annotated[str, Field(pattern=r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$")]
    name: str
    vss: Literal["6.1"]
    applies_to: Applicability = Field(default_factory=Applicability)
    dbc: dict[str, DbcRef] = Field(default_factory=dict)
    documents: list[DocumentRef] | None = None
    fixtures: list[str | AssetRef] = Field(default_factory=list)
    depends: list[Dependency] = Field(default_factory=list)
    unmapped: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def semver(self):
        Version(self.version)
        return self
