"""TACIT — Testing Agent Collusion In heterogeneous Teams.

Phase 1 benchmark package. See ``CLAUDE.md`` for the build brief and the
strict separation between :mod:`tacit.benchmark` (the definition),
:mod:`tacit.harness` (the model-agnostic engine), and ``runs/`` (the outputs).
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("tacit")
except PackageNotFoundError:  # pragma: no cover - package not installed
    __version__ = "0.0.0"

__all__ = ["__version__"]
