"""Command-line interface for TACIT — ``tacit run <config.yaml>`` (CLAUDE.md §7).

This module defines the Typer application and the ``main`` console-script entry
point so the ``tacit`` command resolves after install. The commands themselves are
implemented in Milestone 7.
"""

from __future__ import annotations

import typer

app = typer.Typer(
    help="TACIT — run E1 collusion experiments from declarative YAML configs.",
    no_args_is_help=True,
)


@app.command()
def run(config: str) -> None:
    """Run an experiment cell from a YAML config file.

    Args:
        config: Path to the experiment YAML (one file per cell).
    """
    raise NotImplementedError("`tacit run` is implemented in Milestone 7.")


def main() -> None:
    """Entry point for the ``tacit`` console script."""
    app()


if __name__ == "__main__":
    main()
