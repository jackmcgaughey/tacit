"""Tests for the harness: config parsing, the orchestrator, logging, and the CLI.

Covers run-dir contents, determinism (the §8 acceptance criterion), and an
end-to-end ``tacit run`` over a real gate config.
"""

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from tacit.benchmark import benchmark_version
from tacit.harness.cli import app
from tacit.harness.config import ExperimentConfig, load_experiment_config
from tacit.harness.orchestrator import run_episode, run_experiment

CONFIGS_DIR = Path(__file__).resolve().parents[1] / "experiments" / "configs"

CARTEL_CELL = {
    "experiment": "test_cartel",
    "condition": "C2",
    "environment": {
        "id": "e1",
        "n_sellers": 3,
        "rounds": 20,
        "burn_in": 5,
        "comms_regime": "none",
        "defection_probe": {"enabled": False},
    },
    "population": [
        {"role": "under_test", "agent": "scripted:cartel"},
        {"role": "filler", "agent": "scripted:cartel"},
        {"role": "filler", "agent": "scripted:cartel"},
    ],
    "seeds": [0, 1],
    "generator": {"split": "dev", "instance_seed": 2},
}


def _cell(**overrides: object) -> ExperimentConfig:
    return ExperimentConfig.model_validate({**CARTEL_CELL, **overrides})


# --------------------------------------------------------------------------- #
# Config                                                                       #
# --------------------------------------------------------------------------- #
def test_config_round_trips_from_yaml(tmp_path: Path):
    path = tmp_path / "cell.yaml"
    path.write_text(yaml.safe_dump(CARTEL_CELL))
    config = load_experiment_config(path)
    assert config.experiment == "test_cartel"
    assert len(config.population) == 3
    assert config.environment.to_env_config().rounds == 20


def test_population_must_match_seat_count():
    with pytest.raises(ValueError, match="population has 2 members"):
        _cell(population=CARTEL_CELL["population"][:2])


def test_shipped_gate_configs_parse():
    for name in ("gate_cartel", "gate_honest", "gate_tit_for_tat"):
        config = load_experiment_config(CONFIGS_DIR / f"{name}.yaml")
        assert config.experiment == name
        assert len(config.population) == config.environment.n_sellers


# --------------------------------------------------------------------------- #
# Orchestrator + logging                                                       #
# --------------------------------------------------------------------------- #
def test_run_experiment_writes_complete_run_dirs(tmp_path: Path):
    written = run_experiment(_cell(), tmp_path)
    assert len(written) == 2
    for run_record in written:
        run_dir = run_record.run_dir
        assert (run_dir / "config.snapshot.yaml").exists()
        assert (run_dir / "env_version.txt").read_text().strip() == benchmark_version()
        transcript = (run_dir / "transcript.jsonl").read_text().splitlines()
        assert len(transcript) == 20  # one record per round
        assert json.loads(transcript[0])["round"] == 0
        scores = json.loads((run_dir / "scores.json").read_text())
        assert scores["experiment"] == "test_cartel"
        assert scores["metrics"]["collusion_index"]["clipped"] >= 0.8
        assert scores["instance"]["split"] == "dev"


def test_run_dirs_are_unique_per_seed(tmp_path: Path):
    written = run_experiment(_cell(), tmp_path)
    names = {run_record.run_dir.name for run_record in written}
    assert len(names) == len(written)


def test_run_is_deterministic(tmp_path: Path):
    config = _cell(seeds=[0])
    first = run_episode(config, 0)
    second = run_episode(config, 0)
    assert [r.model_dump() for r in first.episode.records] == [
        r.model_dump() for r in second.episode.records
    ]
    assert first.metrics.model_dump() == second.metrics.model_dump()


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def test_cli_runs_a_gate_config(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["run", str(CONFIGS_DIR / "gate_cartel.yaml"), "--runs-dir", str(tmp_path / "runs")],
    )
    assert result.exit_code == 0, result.output
    assert "CI=" in result.output
    assert "wrote 3 run(s)" in result.output
    assert list((tmp_path / "runs").iterdir())  # run dirs were created
