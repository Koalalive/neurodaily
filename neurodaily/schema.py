"""Configuration schema validation (pydantic v2).

Used by `neurodaily config validate`, the settings GUI, and tests. Kept
permissive: unknown keys are allowed, and every new field has a default so old
config files keep working.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

KNOWN_KINDS = {"paper", "drug", "device", "trial", "news", "policy", "conference", "funding"}
GENERIC_TYPES = {"rss", "json_api", "json"}


class DisciplineModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str = Field(min_length=1)
    arxiv_cats: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)
    bio_cats: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    enabled: bool = True

    @model_validator(mode="after")
    def _non_empty_when_enabled(self):
        if self.enabled and not (self.keywords or self.mesh_terms or self.arxiv_cats
                                 or self.bio_cats):
            raise ValueError("an enabled discipline needs at least one of "
                             "keywords/mesh_terms/arxiv_cats/bio_cats")
        return self


class JournalModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str = Field(min_length=1)
    url: str = ""
    rss: str = ""
    category: str = "neuroscience"
    impact_factor: float | None = None
    jcr: str = ""
    cas: str = ""
    year: int | None = None


class SourceModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    enabled: bool = True
    max_results: int = Field(20, ge=1, le=5000)
    lookback_days: int = Field(2, ge=1, le=365)
    # generic (config-defined) sources
    type: str | None = None
    url: str | None = None
    items_path: str | None = None
    kind: str | None = None
    map: dict[str, str] | None = None

    @model_validator(mode="after")
    def _generic_needs_url(self):
        if self.type and self.type not in GENERIC_TYPES:
            raise ValueError(f"unknown source type {self.type!r}; "
                             f"expected one of {sorted(GENERIC_TYPES)}")
        if self.type in GENERIC_TYPES and not self.url:
            raise ValueError("url is required for type rss/json_api")
        if self.kind and self.kind not in KNOWN_KINDS:
            raise ValueError(f"unknown kind {self.kind!r}; expected {sorted(KNOWN_KINDS)}")
        return self


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    version: int = 2
    profile: str = "neuro"
    disciplines: list[DisciplineModel] = Field(min_length=1)
    global_keywords: list[str] = Field(default_factory=list)
    sources: dict[str, SourceModel] = Field(default_factory=dict)
    output: dict = Field(default_factory=dict)
    scheduled: dict = Field(default_factory=dict)
    windows: dict = Field(default_factory=dict)
    policy_feeds: list[str] = Field(default_factory=list)
    journals: list[JournalModel] = Field(default_factory=list)


def validate(data: dict) -> list[str]:
    """Return a list of human-readable errors; empty means valid."""
    if not isinstance(data, dict):
        return ["config must be a JSON object"]
    try:
        ConfigModel.model_validate(data)
        return []
    except ValidationError as exc:
        out = []
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", [])) or "<root>"
            out.append(f"{loc}: {err.get('msg', 'invalid')}")
        return out


def validate_file(path: str) -> list[str]:
    import json
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return [f"config not found: {path}"]
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"]
    return validate(data)
