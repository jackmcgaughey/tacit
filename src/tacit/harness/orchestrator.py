"""Episode orchestrator: runs episodes and logs them verbatim (CLAUDE.md §7).

Drives the environment/agent loop for each seed in a cell, computes the metrics, and
writes a run directory per episode. The engine is model-agnostic: it talks to agents
only through the ``Agent`` protocol and never imports a model provider.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from tacit.benchmark.agents.base import Observation
from tacit.benchmark.agents.reference.base import ReferenceAgent
from tacit.benchmark.environments.e1 import E1Environment, Episode
from tacit.benchmark.generators.e1_generator import E1Instance, generate_e1_instance
from tacit.benchmark.metrics.e1_metrics import E1Metrics, compute_metrics
from tacit.benchmark.populations import make_agent
from tacit.harness.config import ExperimentConfig
from tacit.harness.logging import write_run


@dataclass(frozen=True)
class EpisodeOutcome:
    """The result of running a single episode (before it is written to disk)."""

    seed: int
    instance: E1Instance
    episode: Episode
    metrics: E1Metrics


@dataclass(frozen=True)
class WrittenRun:
    """An episode outcome paired with the run directory it was written to."""

    run_dir: Path
    outcome: EpisodeOutcome


def run_episode(config: ExperimentConfig, seed: int) -> EpisodeOutcome:
    """Run one episode of the cell under ``seed`` and compute its metrics."""
    instance = generate_e1_instance(
        config.generator.instance_seed, n_sellers=config.environment.n_sellers
    )
    agents = _build_population(config, instance)
    env = E1Environment(config.environment.to_env_config())

    observations: Sequence[Observation] = env.reset(instance, seed)
    for _ in range(config.environment.rounds):
        actions = [agent.act(observations[seat]) for seat, agent in enumerate(agents)]
        observations = env.step(actions).observations

    episode = env.episode()
    return EpisodeOutcome(
        seed=seed,
        instance=instance,
        episode=episode,
        metrics=compute_metrics(episode),
    )


def run_experiment(config: ExperimentConfig, runs_root: str | Path) -> list[WrittenRun]:
    """Run every seed in the cell, writing one run directory per episode."""
    written: list[WrittenRun] = []
    for seed in config.seeds:
        outcome = run_episode(config, seed)
        run_dir = write_run(
            runs_root,
            config=config,
            seed=seed,
            instance=outcome.instance,
            episode=outcome.episode,
            metrics=outcome.metrics,
        )
        written.append(WrittenRun(run_dir=run_dir, outcome=outcome))
    return written


def _build_population(config: ExperimentConfig, instance: E1Instance) -> list[ReferenceAgent]:
    """Construct the seated agents from the population specs."""
    return [
        make_agent(member.agent, agent_id=f"seat{seat}:{member.role}", seat=seat, instance=instance)
        for seat, member in enumerate(config.population)
    ]
