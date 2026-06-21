"""Environment protocol and the shared step-result type (CLAUDE.md §7).

The protocol is intentionally model-agnostic and instance-agnostic (``reset`` takes
``Any`` instance) so the same harness can drive different environments.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from tacit.benchmark.agents.base import Action, Observation


class StepResult(BaseModel):
    """The outcome of advancing the environment by one round.

    Attributes:
        observations: Per-seat observations for the next round (seat order).
        rewards: Per-seat reward (realised profit) for the round just played.
        done: Whether the episode has ended.
        info: Free-form per-round detail (E1 stores the round's ``RoundRecord`` here).
    """

    model_config = ConfigDict(frozen=True)

    observations: tuple[Observation, ...]
    rewards: tuple[float, ...]
    done: bool
    info: dict[str, Any] = Field(default_factory=dict)


class Environment(Protocol):
    """Minimal environment interface driven by the orchestrator (CLAUDE.md §7)."""

    def reset(self, instance: Any, seed: int) -> list[Observation]:
        """Start a fresh episode for ``instance`` under ``seed``; return round-0 obs."""
        ...

    def step(self, actions: list[Action]) -> StepResult:
        """Apply one round of actions (seat order) and return the step result."""
        ...
