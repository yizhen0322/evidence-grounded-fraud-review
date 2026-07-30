"""Strict dashboard configuration with loopback-only network boundaries."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from src.narratives.llm_client import assert_local_ollama_host


def _is_loopback_name(value: str) -> bool:
    if value.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


def assert_loopback_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Ollama host must be an explicit loopback URL")
    if not _is_loopback_name(parsed.hostname):
        raise ValueError("Ollama host must be loopback-only")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Ollama host must not include credentials, query, or fragment")
    return assert_local_ollama_host(value)


def _validate_exact_path(value: str) -> str:
    if any(token in value for token in ("*", "?", "[", "]", "{")):
        raise ValueError("artifact paths must be exact and cannot contain a glob")
    if any(part.lower() == "latest" for part in Path(value).parts):
        raise ValueError("artifact paths cannot use a latest selector")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactConfig(StrictModel):
    dataset_path: str = "data/raw/creditcard.csv"
    detector_run: str
    g4_run: str
    g5_run: str
    results_manifest: str
    semantic_run: str | None = None

    _exact_dataset = field_validator("dataset_path")(_validate_exact_path)
    _exact_detector = field_validator("detector_run")(_validate_exact_path)
    _exact_g4 = field_validator("g4_run")(_validate_exact_path)
    _exact_g5 = field_validator("g5_run")(_validate_exact_path)
    _exact_results = field_validator("results_manifest")(_validate_exact_path)
    _exact_semantic = field_validator("semantic_run")(_validate_exact_path)


class DemoCaseConfig(StrictModel):
    faithful_case_id: int = Field(ge=0)
    error_or_uncertainty_case_id: int = Field(ge=0)
    attack_case_id: int = Field(ge=0)


class OllamaConfig(StrictModel):
    host: str
    model: str = Field(min_length=1)
    timeout_seconds: int = Field(gt=0, le=300)

    @field_validator("host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        return assert_loopback_url(value)


class ServerConfig(StrictModel):
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)

    @field_validator("host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        if not _is_loopback_name(value):
            raise ValueError("FastAPI server host must be loopback-only")
        return value


class WorkflowConfig(StrictModel):
    enabled: bool = True
    database_path: str = "var/dashboard/workflow.sqlite3"

    _exact_database = field_validator("database_path")(_validate_exact_path)


class DashboardConfig(StrictModel):
    schema_version: Literal[1]
    artifacts: ArtifactConfig
    demo_cases: DemoCaseConfig
    recorded_narrative_arm: Literal["strict"] = "strict"
    ollama: OllamaConfig
    server: ServerConfig
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)


@dataclass(frozen=True)
class DashboardSettings:
    """Validated config plus private filesystem resolution state."""

    config: DashboardConfig
    config_path: Path
    repo_root: Path

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        repo_root: str | Path | None = None,
    ) -> "DashboardSettings":
        config_path = Path(path).expanduser().resolve()
        try:
            raw = yaml.safe_load(config_path.read_text())
            config = DashboardConfig.model_validate(raw)
        except (OSError, ValidationError, yaml.YAMLError) as error:
            raise ValueError(f"invalid dashboard configuration: {error}") from error
        root = Path(repo_root or Path.cwd()).expanduser().resolve()
        settings = cls(config=config, config_path=config_path, repo_root=root)
        for candidate in (
            settings.dataset_path,
            settings.detector_run,
            settings.g4_run,
            settings.g5_run,
            settings.results_manifest,
            settings.semantic_run,
        ):
            if candidate is None:
                continue
            try:
                candidate.relative_to(root)
            except ValueError as error:
                raise ValueError(
                    f"configured artifact path escapes repository root: {candidate.name}"
                ) from error
        workflow_database = settings.workflow_database
        try:
            workflow_database.relative_to(root)
        except ValueError as error:
            raise ValueError(
                "configured workflow database escapes repository root"
            ) from error
        for protected in (root / "experiments", root / "reports"):
            try:
                workflow_database.relative_to(protected)
            except ValueError:
                continue
            raise ValueError(
                "workflow database must be outside experiment and report directories"
            )
        return settings

    def _artifact(self, raw: str) -> Path:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = self.repo_root / candidate
        return candidate.resolve()

    @property
    def detector_run(self) -> Path:
        return self._artifact(self.config.artifacts.detector_run)

    @property
    def dataset_path(self) -> Path:
        return self._artifact(self.config.artifacts.dataset_path)

    @property
    def g4_run(self) -> Path:
        return self._artifact(self.config.artifacts.g4_run)

    @property
    def g5_run(self) -> Path:
        return self._artifact(self.config.artifacts.g5_run)

    @property
    def results_manifest(self) -> Path:
        return self._artifact(self.config.artifacts.results_manifest)

    @property
    def semantic_run(self) -> Path | None:
        raw = self.config.artifacts.semantic_run
        return None if raw is None else self._artifact(raw)

    @property
    def frontend_dist(self) -> Path:
        return self.repo_root / "app/frontend/dist"

    @property
    def workflow_database(self) -> Path:
        return self._artifact(self.config.workflow.database_path)
