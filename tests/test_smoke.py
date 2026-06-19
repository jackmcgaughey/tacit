"""Milestone 1 smoke test: the package imports and the benchmark VERSION is present.

Real tests (economy, generator, environment, metrics, validation gate) land in their
respective milestones per CLAUDE.md §9.
"""

from pathlib import Path

import tacit


def test_package_imports():
    """The top-level package imports and exposes a version string."""
    assert isinstance(tacit.__version__, str)
    assert tacit.__version__


def test_benchmark_version_pinned():
    """The benchmark definition is pinned to tacit-0.1.0 (CLAUDE.md §2)."""
    version_file = Path(tacit.__file__).parent / "benchmark" / "VERSION"
    assert version_file.read_text(encoding="utf-8").strip() == "tacit-0.1.0"


def test_cli_entrypoint_importable():
    """The console-script entry point resolves to a callable (CLAUDE.md §7)."""
    from tacit.harness.cli import main

    assert callable(main)
