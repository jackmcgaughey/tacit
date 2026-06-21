"""Run-directory writer and JSONL transcript schema (CLAUDE.md §7).

One run dir per episode: ``runs/<UTC-timestamp>__<config-hash>__seed<seed>/``
containing:

* ``config.snapshot.yaml`` — the exact cell config, snapshotted verbatim;
* ``env_version.txt`` — the benchmark definition version;
* ``transcript.jsonl`` — one JSON record per round (the verbatim transcript);
* ``scores.json`` — the computed metrics plus instance and population metadata.

Nothing in ``runs/`` is ever edited by hand, and the writer never overwrites an
existing run dir.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import yaml

from tacit.benchmark import benchmark_version
from tacit.benchmark.environments.e1 import Episode
from tacit.benchmark.generators.e1_generator import E1Instance
from tacit.benchmark.metrics.e1_metrics import E1Metrics
from tacit.harness.config import ExperimentConfig


def config_hash(config: ExperimentConfig) -> str:
    """A short, stable hash of the cell config (independent of timestamp/seed)."""
    payload = json.dumps(config.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def run_dir_name(config: ExperimentConfig, seed: int, *, now: datetime | None = None) -> str:
    """Build the run-directory name ``<UTC-timestamp>__<config-hash>__seed<seed>``."""
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{stamp}__{config_hash(config)}__seed{seed}"


def write_run(
    runs_root: str | Path,
    *,
    config: ExperimentConfig,
    seed: int,
    instance: E1Instance,
    episode: Episode,
    metrics: E1Metrics,
) -> Path:
    """Write one episode's run directory and return its path.

    Raises:
        FileExistsError: If the target run directory already exists (runs are never
            overwritten).
    """
    run_dir = Path(runs_root) / run_dir_name(config, seed)
    run_dir.mkdir(parents=True, exist_ok=False)

    (run_dir / "config.snapshot.yaml").write_text(
        yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )
    (run_dir / "env_version.txt").write_text(benchmark_version() + "\n", encoding="utf-8")
    _write_transcript(run_dir / "transcript.jsonl", episode)
    _write_scores(
        run_dir / "scores.json", config=config, seed=seed, instance=instance, metrics=metrics
    )
    return run_dir


def _write_transcript(path: Path, episode: Episode) -> None:
    """Write one JSON record per round to ``transcript.jsonl``."""
    lines = [record.model_dump_json() for record in episode.records]
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")


def _write_scores(
    path: Path,
    *,
    config: ExperimentConfig,
    seed: int,
    instance: E1Instance,
    metrics: E1Metrics,
) -> None:
    """Write ``scores.json`` with metrics and run metadata."""
    scores = {
        "experiment": config.experiment,
        "condition": config.condition,
        "seed": seed,
        "instance": instance.model_dump(),
        "population": [member.model_dump() for member in config.population],
        "metrics": metrics.model_dump(),
    }
    path.write_text(json.dumps(scores, indent=2) + "\n", encoding="utf-8")
