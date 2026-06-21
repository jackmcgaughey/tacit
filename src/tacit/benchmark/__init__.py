"""The TACIT benchmark *definition*: economy, environments, generators, agents, metrics.

This package is versioned (see the ``VERSION`` file) and changes rarely. It is kept
strictly separate from :mod:`tacit.harness` (the engine) and ``runs/`` (the outputs).
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["benchmark_version"]


def benchmark_version() -> str:
    """Return the benchmark definition version (e.g. ``"tacit-0.1.0"``).

    Read from the ``VERSION`` file colocated with this package; this string is
    written into every run directory's ``env_version.txt``.
    """
    return (Path(__file__).parent / "VERSION").read_text(encoding="utf-8").strip()
