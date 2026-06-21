"""Pydantic v2 config models for declarative experiment cells (CLAUDE.md §7).

Experiments are declarative YAML, one file per cell (see ``experiments/configs/``);
the exact config is snapshotted into each run directory. These models are part of the
model-agnostic harness, so the environment section maps onto the E1 env config but
the harness itself does not depend on any model provider.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from tacit.benchmark.environments.e1 import CommsRegime, DefectionProbe, E1EnvConfig
from tacit.benchmark.generators.e1_generator import Split

Condition = Literal["C1", "C2", "C3", "C4", "C5"]


class GeneratorConfig(BaseModel):
    """Which instance to generate for the cell."""

    model_config = ConfigDict(frozen=True)

    split: Split
    instance_seed: int


class PopulationMemberConfig(BaseModel):
    """One seat in the population: a role label and an agent spec."""

    model_config = ConfigDict(frozen=True)

    role: str
    agent: str  # e.g. "scripted:cartel"


class EnvironmentConfig(BaseModel):
    """The environment section of a cell; maps onto :class:`E1EnvConfig`.

    Carries ``n_sellers`` (which drives instance generation, not the env config) plus
    the E1 episode parameters.
    """

    model_config = ConfigDict(frozen=True)

    id: Literal["e1"] = "e1"
    n_sellers: int = 3
    rounds: int = 40
    burn_in: int = 10
    comms_regime: CommsRegime = CommsRegime.NONE
    private_channel: tuple[int, ...] = (0, 1)
    defection_probe: DefectionProbe = Field(default_factory=DefectionProbe)
    clip_low_factor: float = 0.8
    clip_high_factor: float = 1.3

    def to_env_config(self) -> E1EnvConfig:
        """Project the environment section onto the E1 environment config."""
        return E1EnvConfig(
            rounds=self.rounds,
            burn_in=self.burn_in,
            comms_regime=self.comms_regime,
            private_channel=self.private_channel,
            defection_probe=self.defection_probe,
            clip_low_factor=self.clip_low_factor,
            clip_high_factor=self.clip_high_factor,
        )


class ExperimentConfig(BaseModel):
    """A full experiment cell, parsed from one YAML file.

    Attributes:
        experiment: Human-readable cell name (used in scores and the run dir).
        condition: C1-C5 label; recorded in Phase 1 (prompt templates are not wired
            to scripted agents until Phase 2).
        environment: Environment section.
        population: One member per seat (length must equal ``environment.n_sellers``).
        seeds: Episode seeds; one episode (and run dir) is produced per seed.
        generator: Which instance to generate.
    """

    model_config = ConfigDict(frozen=True)

    experiment: str
    condition: Condition = "C2"
    environment: EnvironmentConfig = Field(default_factory=EnvironmentConfig)
    population: tuple[PopulationMemberConfig, ...]
    seeds: tuple[int, ...]
    generator: GeneratorConfig

    @model_validator(mode="after")
    def _check(self) -> Self:
        """Validate population size against the seat count and non-empty seeds."""
        if len(self.population) != self.environment.n_sellers:
            raise ValueError(
                f"population has {len(self.population)} members but n_sellers="
                f"{self.environment.n_sellers}"
            )
        if not self.seeds:
            raise ValueError("seeds must be non-empty")
        return self


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    """Load and validate an experiment cell from a YAML file."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return ExperimentConfig.model_validate(data)
