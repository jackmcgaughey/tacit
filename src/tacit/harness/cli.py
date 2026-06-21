"""Command-line interface for TACIT — ``tacit run <config.yaml>`` (CLAUDE.md §7)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from tacit.harness.config import load_experiment_config
from tacit.harness.orchestrator import run_experiment

app = typer.Typer(
    help="TACIT — run E1 collusion experiments from declarative YAML configs.",
    no_args_is_help=True,
)


@app.callback()
def _root() -> None:
    """TACIT command-line interface (keeps ``run`` as an explicit subcommand)."""


@app.command()
def run(
    config: Annotated[Path, typer.Argument(help="Path to the experiment YAML cell.")],
    runs_dir: Annotated[
        Path, typer.Option(help="Directory under which run dirs are written.")
    ] = Path("runs"),
) -> None:
    """Run an experiment cell: one episode (and run dir) per seed, then print scores."""
    experiment = load_experiment_config(config)
    written = run_experiment(experiment, runs_dir)
    for run_record in written:
        outcome = run_record.outcome
        collusion = outcome.metrics.collusion_index
        gain = outcome.metrics.profit_gain
        typer.echo(
            f"{run_record.run_dir.name}  seed={outcome.seed}  "
            f"CI={collusion.clipped:.3f} (raw {collusion.raw:.3f})  gain={gain.clipped:.3f}"
        )
    typer.echo(f"wrote {len(written)} run(s) under {runs_dir}")


def main() -> None:
    """Entry point for the ``tacit`` console script."""
    app()


if __name__ == "__main__":
    main()
